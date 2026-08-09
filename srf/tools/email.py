import asyncio
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pydantic import BaseModel, EmailStr, Field
from sanic.log import logger

from srf.config.settings import EmailConfig


class EmailValidator(BaseModel):
    email: EmailStr


class EmailCodeVerifySchema(BaseModel):
    confirmations: str = Field(..., pattern=r"^\d{5}$")
    email: EmailStr
    # expire_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=10))


def send_email(to_email, subject="", content="") -> bool:
    """
    send email by SMTP

    to_email:
    subject:
    content:
    """

    # Sender's mailbox configuration (needs to be modified to your mailbox information)
    from_email = EmailConfig.from_email
    smtp_server = EmailConfig.smtp_server  # SMTP server address
    smtp_port = int(EmailConfig.smtp_port)  # e.g. 587 or 465
    password = EmailConfig.password

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = Header(subject, 'utf-8')
    msg.attach(MIMEText(content, 'plain', 'utf-8'))

    # Connect to the SMTP server and send mail
    server = None
    try:
        if smtp_port == 465:
            # SSL connect
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()  # TLS encryption

        server.login(from_email, password)
        server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception:
        logger.exception("Email send failed to=%s", to_email)
        return False
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass


# async def send_email(to_email: str, subject: str = "", content: str = "") -> bool:
#     return await asyncio.to_thread(_send_email, to_email, subject, content)


async def send_verify_code(to_email, verify_code) -> bool:
    content = f"""Your verification code: {verify_code}, valid within one minute"""
    subject = "Platform Verification Code"
    return await asyncio.to_thread(send_email, to_email, subject, content)
