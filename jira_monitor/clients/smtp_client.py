import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from ..logger_config import setup_logger

logger = setup_logger()


class SMTPClient:
    def __init__(self, smtp_server: str, smtp_port: int, email_user: str, email_password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_user = email_user
        self.email_password = email_password

    def test_connection(self) -> bool:
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
            logger.info("SMTP соединение успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка SMTP соединения: {e}")
            return False

    def send_email(self, recipients: List[str], subject: str, html_content: str) -> bool:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_user
            msg['To'] = ', '.join(recipients)

            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)

            logger.info(f"Email отправлен: {', '.join(recipients)}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False

    def send_simple_email(self, recipients: List[str], subject: str, text_content: str) -> bool:
        try:
            msg = MIMEText(text_content, 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = self.email_user
            msg['To'] = ', '.join(recipients)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)

            logger.info(f"Простое email отправлено: {', '.join(recipients)}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки простого email: {e}")
            return False