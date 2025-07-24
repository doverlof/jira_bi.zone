from .clients import SMTPClient, UserClient, IssuesClient, EmailClient
from .logger_config import setup_logger
from .config import settings

logger = setup_logger()


class JiraCompletedMonitor:
    def __init__(self):
        self.jira_url = settings.jira_url
        self.jira_token = settings.jira_token.get_secret_value()
        self.project_key = settings.jira_project_key
        self.jira_external_url = settings.jira_external_url
        self.product_name = settings.product_name
        self.project_name = settings.project_name
        self.report_day = settings.report_day_of_month
        self.report_hour = settings.report_hour
        self.report_minute = settings.report_minute
        self.release_title_field_id = settings.release_title_field_id
        self.change_field_id = settings.change_field_id

        self.smtp_client = SMTPClient(
            smtp_server=settings.smtp_server,
            smtp_port=settings.smtp_port,
            email_user=settings.email_user,
            email_password=settings.email_password.get_secret_value()
        )

        self.user_client = UserClient(
            jira_url=self.jira_url,
            jira_token=self.jira_token
        )

        jira_client = self.user_client.jira

        self.issues_client = IssuesClient(
            jira_client=jira_client,
            project_key=self.project_key,
            report_day=self.report_day,
            report_hour=self.report_hour,
            report_minute=self.report_minute
        )

        self.email_client = EmailClient(
            smtp_client=self.smtp_client,
            jira_client=jira_client,
            product_name=self.product_name,
            project_name=self.project_name,
            jira_external_url=self.jira_external_url,
            project_key=self.project_key
        )

    def test_connections(self) -> bool:
        try:
            with self.smtp_client.get_connection() as server:
                pass
            smtp_ok = True
            logger.info("SMTP тест успешен")
        except Exception as e:
            logger.error(f"SMTP тест неудачен: {e}")
            smtp_ok = False

        try:
            self.user_client.jira.myself()
            user_ok = True
            logger.info("Jira тест успешен")
        except Exception as e:
            logger.error(f"Jira тест неудачен: {e}")
            user_ok = False

        return smtp_ok and user_ok

    def get_completed_issues(self):
        return self.issues_client.filter_completed_issues(
            release_title_field_id=self.release_title_field_id,
            change_field_id=self.change_field_id
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