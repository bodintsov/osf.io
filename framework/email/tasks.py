import logging
import smtplib
from base64 import b64encode
from email.mime.text import MIMEText
from io import BytesIO

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Bcc,
    ReplyTo,
    Category,
    Attachment,
    FileContent,
    Email,
    To,
    Personalization,
    Cc,
    FileName,
    Disposition,
)


from framework import sentry
from framework.celery_tasks import app
from website import settings

logger = logging.getLogger(__name__)


@app.task
def send_email(
    from_addr: str,
    to_addr: str,
    subject: str,
    message: str,
    reply_to: bool = False,
    ttls: bool = True,
    login: bool = True,
    bcc_addr: [] = None,
    username: str = None,
    password: str = None,
    categories=None,
    attachment_name: str = None,
    attachment_content: str | bytes | BytesIO = None,
):
    """Send email to specified destination.
    Email is sent from the email specified in FROM_EMAIL settings in the
    settings module.

    Uses the Sendgrid API if ``settings.SENDGRID_API_KEY`` is set.

    :param from_addr: A string, the sender email
    :param to_addr: A string, the recipient
    :param subject: subject of email
    :param message: body of message
    :param categories: Categories to add to the email using SendGrid's
        SMTPAPI. Used for email analytics.
        See https://sendgrid.com/docs/User_Guide/Statistics/categories.html
        This parameter is only respected if using the Sendgrid API.
        ``settings.SENDGRID_API_KEY`` must be set.

    :return: True if successful
    """
    if not settings.USE_EMAIL:
        return
    if settings.SENDGRID_API_KEY:
        return _send_with_sendgrid(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            categories=categories,
            attachment_name=attachment_name,
            attachment_content=attachment_content,
            reply_to=reply_to,
            bcc_addr=bcc_addr,
        )
    else:
        return _send_with_smtp(
            from_addr=from_addr,
            to_addr=to_addr,
            subject=subject,
            message=message,
            ttls=ttls,
            login=login,
            username=username,
            password=password,
            reply_to=reply_to,
            bcc_addr=bcc_addr,
        )


def _send_with_smtp(
        from_addr,
        to_addr,
        subject,
        message,
        ttls=True,
        login=True,
        username=None,
        password=None,
        bcc_addr=None,
        reply_to=None,
):
    username = username or settings.MAIL_USERNAME
    password = password or settings.MAIL_PASSWORD

    if login and (username is None or password is None):
        logger.error('Mail username and password not set; skipping send.')
        return False

    msg = MIMEText(
        message,
        'html',
        _charset='utf-8',
    )
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    if reply_to:
        msg['Reply-To'] = reply_to

    # Combine recipients for SMTP
    recipients = [to_addr] + (bcc_addr or [])

    # Establish SMTP connection and send the email
    with smtplib.SMTP(settings.MAIL_SERVER) as server:
        server.ehlo()
        if ttls:
            server.starttls()
            server.ehlo()
        if login:
            server.login(username, password)
        server.sendmail(
            from_addr=from_addr,
            to_addrs=recipients,
            msg=msg.as_string()
        )
    return True


def _send_with_sendgrid(
    from_addr: str,
    to_addr: str,
    subject: str,
    message: str,
    categories=None,
    attachment_name: str = None,
    attachment_content=None,
    cc_addr=None,
    bcc_addr=None,
    reply_to=None,
    client=None,
):
    in_allowed_list = to_addr in settings.SENDGRID_EMAIL_WHITELIST
    if settings.SENDGRID_WHITELIST_MODE and not in_allowed_list:
        sentry.log_message(
            f'SENDGRID_WHITELIST_MODE is True. Failed to send emails to non-whitelisted recipient {to_addr}.'
        )
        return False

    client = client or SendGridAPIClient(settings.SENDGRID_API_KEY)
    mail = Mail(
        from_email=Email(from_addr),
        html_content=message,
        subject=subject,
    )

    # Personalization to handle To, CC, and BCC sendgrid client concept
    personalization = Personalization()

    personalization.add_to(To(to_addr))

    if cc_addr:
        if isinstance(cc_addr, str):
            cc_addr = [cc_addr]
        for email in cc_addr:
            personalization.add_cc(Cc(email))

    if bcc_addr:
        if isinstance(bcc_addr, str):
            bcc_addr = [bcc_addr]
        for email in bcc_addr:
            personalization.add_bcc(Bcc(email))

    if reply_to:
        mail.reply_to = ReplyTo(reply_to)

    mail.add_personalization(personalization)

    if categories:
        mail.add_category([Category(x) for x in categories])

    if attachment_name and attachment_content:
        attachment = Attachment(
            file_content=FileContent(b64encode(attachment_content).decode()),
            file_name=FileName(attachment_name),
            disposition=Disposition('attachment')
        )
        mail.add_attachment(attachment)

    response = client.send(mail)
    if response.status_code not in (200, 201, 202):
        sentry.log_message(
            f'{response.status_code} error response from sendgrid.'
            f'from_addr:  {from_addr}\n'
            f'to_addr:  {to_addr}\n'
            f'subject:  {subject}\n'
            'mimetype:  html\n'
            f'message:  {response.body[:30]}\n'
            f'categories:  {categories}\n'
            f'attachment_name:  {attachment_name}\n'
        )
    else:
        return True

def _content_to_bytes(attachment_content: BytesIO | str | bytes) -> bytes:
    if isinstance(attachment_content, bytes):
        return attachment_content
    elif isinstance(attachment_content, BytesIO):
        return attachment_content.getvalue()
    elif isinstance(attachment_content, str):
        return attachment_content.encode()
    else:
        return str(attachment_content).encode()
