import os
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

import aiosmtplib
from aiosmtplib import SMTPAuthenticationError, SMTPConnectTimeoutError

import settings
from core.dto.service import EmailStruct
from core.utils.loggining import logger
from infrastructure.database.models import Claim, ClaimWay, SystemUser, Visitor


async def _send_email(data: EmailStruct) -> None:
    """Build a message and send email."""
    host = settings.MAIL_SERVER_HOST
    port = settings.MAIL_SERVER_PORT
    sender = settings.MAIL_SEND_FROM_EMAIL
    password = settings.MAIL_SERVER_PASSWORD
    username = settings.MAIL_SERVER_USERNAME

    recipients = data.email
    text = data.text
    subject = data.subject
    await _send_with_authorize(send_from=sender, send_to=recipients, subject=subject, text=text,
                               server=host, port=port, username=username, password=password)


async def _send_with_authorize(send_from: str, send_to: list, subject: str, text: str, text_type="plain",
                               files: dict[str, str] | list = None,
                               server: str = "127.0.0.1", port: int = 465,
                               username: str = None, password: str = None, tls=False) -> None:
    msg = create_multipart_message(send_from, send_to, subject, text, text_type=text_type,
                                   files=files)
    try:
        await aiosmtplib.send(
            msg,
            hostname=server,
            port=port,
            username=username,
            password=password,
            use_tls=tls,
            start_tls=True,
            timeout=180  # seconds
        )
    except SMTPAuthenticationError as ex:
        logger.exception(ex)
    except SMTPConnectTimeoutError as e:
        logger.exception(e)


def create_multipart_message(send_from: str, send_to: list, subject: str, text: str, text_type: str = "plain",
                             files: dict[str, str] | list = None) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg['From'] = send_from
    if isinstance(send_to, list):
        msg['To'] = ', '.join(send_to)
    else:
        msg['To'] = send_to
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text, text_type, _charset="utf-8"))

    if type(files) == dict:
        for fn in files:
            with open(files[fn], "rb") as file:
                part = MIMEApplication(
                    file.read(),
                    Name=fn
                )
            # After the file is closed
            part['Content-Disposition'] = 'attachment; filename="%s"' % fn
            msg.attach(part)
    else:
        for f in files or []:
            with open(f, "rb") as file:
                part = MIMEApplication(
                    file.read(),
                    Name=os.path.basename(f)
                )
            # After the file is closed
            part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(f)
            msg.attach(part)

    return msg


async def create_email_struct(claim_way: ClaimWay,
                              claim: Claim,
                              claim_way_2: bool = False,
                              approved: bool = False,
                              time_before: bool = False,
                              status: str = None) -> tuple[EmailStruct, list[SystemUser], str]:
    """Build EmailStruct"""
    system_users = claim_way.__dict__.get('_system_users')

    url = settings.CLAIMS_URL.format(claim=claim.id)
    text = settings.CLAIMWAY_BODY_TEXT.format(claim=claim.id, url=url)
    subject = settings.CLAIMWAY_SUBJECT_TEXT

    time_to_send = time_to_expire = None
    if time_before:
        # Notify SystemUsers in ClaimWay before N minutes before Visitor come
        if time_to_send_notify := await calculate_time_to_send_notify(claim):
            time_to_send, time_to_expire = time_to_send_notify
            visit_start_date = datetime.strftime(time_to_expire, settings.DATETIME_FORMAT)
            text = settings.CLAIMWAY_BEFORE_N_MINUTES_BODY_TEXT.format(url=url, visit_start_date=visit_start_date)
            subject = settings.CLAIMWAY_BEFORE_N_MINUTES_SUBJECT_TEXT.format(claim=claim.id)

    if status:
        # if status in claim was changed
        text = settings.CLAIM_STATUS_BODY_TEXT.format(claim=claim.id, status=status)
        subject = settings.CLAIM_STATUS_SUBJECT_TEXT.format(claim=claim.id)

    if approved:
        # when claim was approved
        text = settings.CLAIM_APPROVED_BODY_TEXT.format(claim=claim.id, url=url)
        subject = settings.CLAIM_APPROVED_SUBJECT_TEXT.format(claim=claim.id)

    emails = [user.email for user in system_users]

    email_struct = EmailStruct(email=emails,
                               text=text,
                               subject=subject,
                               time_to_send=time_to_send,
                               time_to_expire=time_to_expire,
                               claim=claim.id,
                               claim_way_2=claim_way_2)
    return email_struct, system_users, url


async def create_email_struct_for_sec_officers(visitor: Visitor,
                                               user: SystemUser) -> tuple[EmailStruct, list[SystemUser]]:
    """Build EmailStruct for security officers."""
    # TODO do something or make sure Role.get(id=4) == 'Сотрудник службы безопасности'
    security_officers = await SystemUser.filter(scopes=4)

    subject = settings.BLACKLIST_NOTIFICATION_SUBJECT_TEXT
    text = settings.BLACKLIST_NOTIFICATION_BODY_TEXT.format(user=user, visitor=visitor)
    emails = [user.email for user in security_officers]

    email_struct = EmailStruct(email=emails,
                               text=text,
                               subject=subject)
    return email_struct, security_officers


async def calculate_time_to_send_notify(claim: Claim) -> tuple[datetime, datetime] | None:
    """
    Calculating time for sending notification to users, who didn't approve claim.
    Also, calc expire time for Celery task.
    """
    minutes: int = await settings.system_settings("claimway_before_n_minutes")

    if time_to_expire := await Visitor.filter(claim=claim.id, deleted=False).first().values("visit_start_date"):
        if time_to_expire["visit_start_date"]:
            time_to_expire = time_to_expire["visit_start_date"].astimezone()
            time_to_send = time_to_expire - timedelta(minutes=minutes)
            return time_to_send, time_to_expire
