import os
import aiosmtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from typing import Union, Dict, List
from email.mime.text import MIMEText
from aiosmtplib import SMTPAuthenticationError, SMTPConnectTimeoutError

import settings
from core.dto.service import EmailStruct
from core.utils.loggining import logger


COMMASPACE = ', '


# async def _send_email(users: EmailStruct) -> None:
#     """Create SMTP server"""
#     host = settings.MAIL_SERVER_HOST
#     port = settings.MAIL_SERVER_PORT
#     sender = settings.MAIL_SERVER_USER
#     password = settings.MAIL_SERVER_PASSWORD
#
#     # smtp = aiosmtplib.SMTP(host, port, use_tls=False)
#     #
#     # await smtp.connect()
#     # await smtp.starttls()
#     # try:
#     #     await smtp.login(sender, password)
#     # except SMTPAuthenticationError as exx:
#     #     logger.exception(exx)
#
#     async def send_a_message() -> None:
#         """Sending email"""
#         # for i in range(len(users.email)):
#         #     recipient = users.email[i]
#         #     text = users.text[i]
#         #     subject = users.subject
#
#             # build message
#             # message = MIMEText(text, _charset="utf-8", _subtype="plain")
#             # message['From'] = sender
#             # message['To'] = recipient
#             # message['Subject'] = subject
#             # await smtp.send_message(message)
#     await send_a_message()


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


async def _send_with_authorize(send_from: str, send_to: List, subject: str, text: str, text_type="plain",
                               files: Union[Dict[str, str], List] = None,
                               server: str = "127.0.0.1", port: int = 465,
                               username: str = None, password: str = None, tls=False):
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


def create_multipart_message(send_from: str, send_to: List, subject: str, text: str, text_type: str = "plain",
                             files: Union[Dict[str, str], List] = None):
    msg = MIMEMultipart()
    msg['From'] = send_from
    if isinstance(send_to, list):
        msg['To'] = COMMASPACE.join(send_to)
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
