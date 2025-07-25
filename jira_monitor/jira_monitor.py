from .clients import SMTPClient, JiraClient, EmailClient
from .logger_config import setup_logger
from .config import settings

logger = setup_logger()


def create_smtp_client() -> SMTPClient:
    return SMTPClient(
        smtp_server=settings.smtp_server,
        smtp_port=settings.smtp_port,
        email_user=settings.email_user,
        email_password=settings.email_password.get_secret_value()
    )


def create_jira_client() -> JiraClient:
    return JiraClient(
        jira_url=settings.jira_url,
        jira_token=settings.jira_token.get_secret_value(),
        project_key=settings.jira_project_key,
        report_day=settings.report_day_of_month,
        report_hour=settings.report_hour,
        report_minute=settings.report_minute
    )


def create_email_client(smtp_client: SMTPClient, jira_client: JiraClient) -> EmailClient:
    return EmailClient(
        smtp_client=smtp_client,
        jira_client=jira_client.jira,
        product_name=settings.product_name,
        project_name=settings.project_name,
        jira_external_url=settings.jira_external_url,
        project_key=settings.jira_project_key
    )


class JiraCompletedMonitor:
    def __init__(self, smtp_client: SMTPClient, jira_client: JiraClient, email_client: EmailClient):
        self.smtp_client = smtp_client
        self.jira_client = jira_client
        self.email_client = email_client

        self.jira_url = settings.jira_url
        self.project_key = settings.jira_project_key

    @classmethod
    def create_default(cls):
        smtp_client = create_smtp_client()
        jira_client = create_jira_client()
        email_client = create_email_client(smtp_client, jira_client)
        return cls(smtp_client, jira_client, email_client)

    def test_connections(self) -> bool:
        try:
            with self.smtp_client.get_connection() as server:
                logger.debug(f"SMTP сервер подключен: {server.sock.getpeername()}")
            smtp_ok = True
            logger.info("SMTP тест успешен")
        except Exception as e:
            logger.error(f"SMTP тест неудачен: {e}")
            smtp_ok = False

        try:
            self.jira_client.myself()
            jira_ok = True
            logger.info("Jira тест успешен")
        except Exception as e:
            logger.error(f"Jira тест неудачен: {e}")
            jira_ok = False

        return smtp_ok and jira_ok

    def get_completed_issues(self):
        return self.jira_client.filter_completed_issues(
            release_title_field_id=settings.release_title_field_id,
            change_field_id=settings.change_field_id
        )

    def send_batch_notification(self, issues_data, is_startup=False):
        if not issues_data or not issues_data.get('issues'):
            logger.info("Нет задач для отправки")
            return True

        subject, html_content = self.email_client.generate_html_content(
            issues_data=issues_data,
            is_startup=is_startup
        )

        if not subject or not html_content:
            logger.info("Не удалось сформировать содержимое письма")
            return True

        success = self.email_client.send_email(
            recipients=settings.recipients_list,
            subject=subject,
            html_content=html_content
        )

        if success:
            logger.info("Email успешно отправлен")
            return True
        else:
            logger.error("Ошибка отправки email")
            return False

    def send_simple_notification(self, issue_key: str, summary: str):
        subject, text_content = self.email_client.generate_simple_notification(
            issue_key=issue_key,
            summary=summary
        )

        success = self.email_client.send_simple_email(
            recipients=settings.recipients_list,
            subject=subject,
            text_content=text_content
        )

        if success:
            logger.info(f"Простое уведомление отправлено для задачи {issue_key}")
            return True
        else:
            logger.error(f"Ошибка отправки простого уведомления для задачи {issue_key}")
            return False