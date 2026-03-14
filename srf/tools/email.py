import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pydantic import BaseModel, EmailStr, Field
from sanic.log import logger

from srf.config.settings import EmailConfig


class EmailValidator(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    confirmations: int = Field(..., gt=0, le=99999)
    # expire_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=10))


async def send_email(to_email, subject="", content=""):
    """
    send email by SMTP

    to_email:
    subject:
    content:
    """

    # Sender's mailbox configuration (needs to be modified to your mailbox information)
    from_email = EmailConfig.from_email
    smtp_server = EmailConfig.smtp_server  # SMTP server address
    smtp_port = EmailConfig.smtp_port  # e.g. 587 or 465
    password = EmailConfig.password

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = Header(subject, 'utf-8')

    # Email body
    msg.attach(MIMEText(content, 'plain', 'utf-8'))

    # Connect to the SMTP server and send mail
    if smtp_port == 465:
        # SSL connect
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    else:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # TLS encryption

    try:
        server.login(from_email, password)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception:
        logger.exception("Email send failed")
        return False


async def send_verify_code(to_email, verify_code):
    content = f"""your code:{verify_code}, valid within one minute"""
    subject = "platform verification code"
    try:
        await send_email(to_email, subject, content)
    except Exception:
        logger.exception("Email send failed")
