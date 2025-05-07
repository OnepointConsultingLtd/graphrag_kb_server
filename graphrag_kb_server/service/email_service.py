import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from graphrag_kb_server.logger import logger


class EmailConfig:
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL")


email_cfg = EmailConfig()


def send_admin_token_email(recipient_email: str, name: str, token: str) -> bool:
    """
    Send an email containing the admin token to the specified recipient.

    Args:
        recipient_email: The email address of the recipient
        name: The name of the administrator
        token: The JWT token to send

    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    try:
        if not all(
            [
                email_cfg.smtp_server,
                email_cfg.smtp_username,
                email_cfg.smtp_password,
                email_cfg.sender_email,
            ]
        ):
            logger.error(
                "Missing email configuration. Please set SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, and SENDER_EMAIL environment variables."
            )
            return False

        msg = MIMEMultipart()
        msg["From"] = email_cfg.sender_email
        msg["To"] = recipient_email
        msg["Subject"] = "Your GraphRAG Knowledge Base Admin Token"

        body = f"""
        Hello {name},

        Your GraphRAG Knowledge Base administrator token has been generated.

        Token: {token}

        Please keep this token secure as it provides administrative access to the system.

        Best regards,
        GraphRAG Team
        """

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(email_cfg.smtp_server, email_cfg.smtp_port) as server:
            server.starttls()
            server.login(email_cfg.smtp_username, email_cfg.smtp_password)
            server.send_message(msg)

        logger.info(f"Admin token email sent successfully to {recipient_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send admin token email: {str(e)}")
        return False
