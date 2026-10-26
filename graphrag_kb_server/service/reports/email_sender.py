import smtplib
from email.message import EmailMessage

from asyncer import asyncify

from graphrag_kb_server.config import ReportConfig


def build_email_message(
    sender: str,
    recipients: list[str],
    subject: str,
    text_body: str,
    html_body: str,
    attachment_name: str,
    attachment_bytes: bytes,
) -> EmailMessage:
    """Build a multipart email with a plain text and HTML body and one PDF attachment."""
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    message.add_attachment(attachment_bytes, maintype="application", subtype="pdf", filename=attachment_name)
    return message


def open_smtp_connection(config: type[ReportConfig]) -> smtplib.SMTP:
    """Open an encrypted SMTP connection: SMTPS if config.smtp_use_ssl, otherwise plain SMTP upgraded with STARTTLS."""
    if config.smtp_use_ssl:
        smtp = smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=30)
        smtp.set_debuglevel(2 if config.smtp_debug else 0)
        return smtp
    smtp = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30)
    smtp.set_debuglevel(2 if config.smtp_debug else 0)
    smtp.starttls()
    return smtp


def send_email_with_attachment(
    config: type[ReportConfig],
    subject: str,
    text_body: str,
    html_body: str,
    attachment_name: str,
    attachment_bytes: bytes,
) -> None:
    """Send the report to config.recipients over SMTPS (implicit TLS, e.g. port 465) or SMTP with STARTTLS."""
    message = build_email_message(
        config.smtp_from,
        config.recipients,
        subject,
        text_body,
        html_body,
        attachment_name,
        attachment_bytes,
    )
    with open_smtp_connection(config) as smtp:
        if config.smtp_user and config.smtp_password:
            smtp.login(config.smtp_user, config.smtp_password)
        smtp.send_message(message)


async_send_email_with_attachment = asyncify(send_email_with_attachment)
