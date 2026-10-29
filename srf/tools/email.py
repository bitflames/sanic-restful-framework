import asyncio
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pydantic import BaseModel, EmailStr, Field
from sanic.log import logger

from srf.config import settings
from srf.templates.template import templates


class EmailValidator(BaseModel):
    email: EmailStr


class EmailCodeVerifySchema(EmailValidator):
    confirmations: str = Field(..., pattern=r"^\d{6}$", strict=False)


def send_email(to_email: str, subject: str, content: str) -> bool:
    from_email = settings.EMAIL_CONFIG.from_email
    smtp_server = settings.EMAIL_CONFIG.smtp_server
    smtp_port = int(settings.EMAIL_CONFIG.smtp_port)
    password = settings.EMAIL_CONFIG.password

    message = MIMEMultipart("alternative")
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = Header(subject, "utf-8")
    message.attach(MIMEText(content, "html", "utf-8"))

    server = None

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(from_email, password)
        server.sendmail(from_email, [to_email], message.as_string())
        return True

    except Exception:  # noqa: BLE001
        logger.exception("Email send failed")
        return False

    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:  # noqa: BLE001
                logger.warning("Failed to close SMTP connection", exc_info=True)


async def send_template_email(to_email: str, subject: str, template_name: str, context: dict) -> bool:
    template = templates.get_template(template_name)
    content = template.render(**context)

    return await asyncio.to_thread(send_email, to_email, subject, content)
