import os
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

import aiosmtplib
from aiosmtplib import SMTPAuthenticationError, SMTPConnectTimeoutError
from loguru import logger

from asbp_app.api.dto.service import EmailStruct
from asbp_app.enviroment.infrastructure.database.models import Claim, ClaimWay, SystemUser, Visitor, SystemSettingsTypes
from asbp_app.utils.system import get_system_settings


async def _send_email(data: EmailStruct) -> None:
    """Build a message and send email."""
    host = await get_system_settings(SystemSettingsTypes.EMAIL_HOST)
    port = await get_system_settings(SystemSettingsTypes.EMAIL_PORT)
    sender = await get_system_settings(SystemSettingsTypes.EMAIL_SENDER)
    password = await get_system_settings(SystemSettingsTypes.EMAIL_PASS)
    username = await get_system_settings(SystemSettingsTypes.EMAIL_USER)

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


async def create_email_struct_for_sec_officers(visitor: Visitor,
                                               user: SystemUser) -> tuple[EmailStruct, list[SystemUser]]:
    """Build EmailStruct for security officers."""
    # TODO do something or make sure Role.get(id=4) == 'Сотрудник службы безопасности'
    security_officers = await SystemUser.filter(scopes=4)

    subject = await get_system_settings(SystemSettingsTypes.BLACKLIST_NOTIFICATION_SUBJECT_TEXT)
    text = (await get_system_settings(SystemSettingsTypes.BLACKLIST_NOTIFICATION_BODY_TEXT)).format(user=user,
                                                                                                    visitor=visitor)
    emails = [user.email for user in security_officers]

    email_struct = EmailStruct(email=emails,
                               text=text,
                               subject=subject)
    return email_struct, security_officers
