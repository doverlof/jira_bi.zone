import requests
from requests.auth import HTTPBasicAuth

from .clients.smtp_client import SMTPClient
from .clients.jira_auth import JiraAuth
from .clients.jira_issues import JiraIssues
from .clients.email_generator import EmailGenerator
from .logger_config import setup_logger
from .config import settings

logger = setup_logger()


class JiraCompletedMonitor:
    def __init__(self):
        self.jira_url = settings.jira_url
        self.jira_user = settings.jira_user
        self.jira_password = settings.jira_password.get_secret_value()
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

        self.jira_auth = JiraAuth(
            jira_url=self.jira_url,
            jira_user=self.jira_user,
            jira_password=self.jira_password
        )

        self.jira_issues = JiraIssues(
            jira_url=self.jira_url,
            auth=self.jira_auth.get_auth(),
            project_key=self.project_key,
            report_day=self.report_day,
            report_hour=self.report_hour,
            report_minute=self.report_minute
        )

        self.email_generator = EmailGenerator(
            product_name=self.product_name,
            project_name=self.project_name,
            jira_external_url=self.jira_external_url,
            project_key=self.project_key
        )

    def get_latest_release_version(self):
        url = f"{self.jira_url}/rest/api/2/project/{self.project_key}/versions"

        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.jira_user, self.jira_password),
                timeout=30
            )
            response.raise_for_status()
            versions = response.json()

            released_versions = [v for v in versions if v.get('released', False)]

            if released_versions:
                latest_version = max(released_versions, key=lambda x: x.get('releaseDate', ''))
                return latest_version['name']
            elif versions:
                latest_version = max(versions, key=lambda x: x.get('id', 0))
                return latest_version['name']

        except Exception as e:
            logger.error(f"Ошибка получения версий: {e}")

        return None

    def get_completed_issues(self):
        logger.info(f"Настройки периода: {self.report_day}-е число в {self.report_hour:02d}:{self.report_minute:02d}")

        release_title_field = self.release_title_field_id
        if release_title_field:
            logger.info(f"Использую ID поля Release title из конфигурации: {release_title_field}")
        else:
            logger.info("ID поля Release title не задан в конфигурации, выполняю автоматический поиск...")

        change_field = self.change_field_id
        if change_field:
            logger.info(f"Использую ID поля Change из конфигурации: {change_field}")
        else:
            logger.info("ID поля Change не задан в конфигурации, выполняю автоматический поиск...")

        return self.jira_issues.get_completed_issues(
            release_title_field_id=release_title_field,
            change_field_id=change_field
        )

    def send_batch_notification(self, issues_data, is_startup=False):
        if not issues_data:
            logger.info("Нет данных о задачах для отправки")
            return True

        version = self.get_latest_release_version()

        subject, html_content = self.email_generator.generate_email_content(
            issues_data=issues_data,
            version=version,
            is_startup=is_startup
        )

        if not subject or not html_content:
            logger.info("Нет задач с заполненным полем Change для отправки")
            return True

        success = self.smtp_client.send_email(
            recipients=settings.recipients_list,
            subject=subject,
            html_content=html_content
        )

        if success:
            if isinstance(issues_data, dict):
                issues_list = issues_data.get('issues', [])
                change_field_id = issues_data.get('change_field_id')

                filtered_keys = []
                for issue in issues_list:
                    if change_field_id and change_field_id in issue['fields']:
                        change_value = issue['fields'][change_field_id]
                        if change_value:
                            if isinstance(change_value, dict):
                                change_text = change_value.get('value', '')
                            else:
                                change_text = str(change_value)

                            if change_text:
                                filtered_keys.append(issue['key'])

                if filtered_keys:
                    logger.info(f"Email отправлен для задач: {', '.join(filtered_keys)}")
                else:
                    logger.info("Email отправлен, но задачи для логирования не найдены")
            else:
                logger.info("Email отправлен")

            return True
        else:
            logger.error("Ошибка отправки email")
            return False

    def send_simple_notification(self, issue_key: str, summary: str):
        subject, text_content = self.email_generator.generate_simple_notification(
            issue_key=issue_key,
            summary=summary
        )

        success = self.smtp_client.send_simple_email(
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