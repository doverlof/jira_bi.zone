import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

from .clients.email_client import EmailContentGenerator
from .logger_config import setup_logger
from .config import settings
from .clients import SMTPClient
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
        self.email_generator = EmailContentGenerator()

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

    def get_release_title_field_id(self):
        url = f"{self.jira_url}/rest/api/2/field"

        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.jira_user, self.jira_password),
                timeout=30
            )
            response.raise_for_status()
            fields = response.json()

            possible_names = [
                'Release title'
            ]

            logger.info("Поиск поля Release title среди доступных полей...")

            for field in fields:
                field_name = field.get('name', '')
                field_id = field.get('id', '')

                if field_name in possible_names:
                    logger.info(f"Найдено поле Release title: ID={field_id}, Name='{field_name}'")
                    return field_id

                search_terms = ['release title']
                for term in search_terms:
                    if term.lower() in field_name.lower():
                        logger.info(f"Найдено похожее поле: ID={field_id}, Name='{field_name}'")
                        return field_id

            logger.warning("Поле Release title не найдено. Доступные кастомные поля:")
            for field in fields:
                if field.get('custom', False):
                    logger.info(
                        f"  - ID: {field.get('id')}, Name: '{field.get('name')}', Type: {field.get('schema', {}).get('type', 'unknown')}")

        except Exception as e:
            logger.error(f"Ошибка получения полей: {e}")

        return None

    def get_change_field_id(self):
        url = f"{self.jira_url}/rest/api/2/field"

        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(self.jira_user, self.jira_password),
                timeout=30
            )
            response.raise_for_status()
            fields = response.json()

            possible_names = [
                'Change'
            ]

            logger.info("Поиск поля Change среди доступных полей...")

            for field in fields:
                field_name = field.get('name', '')
                field_id = field.get('id', '')

                if field_name in possible_names:
                    logger.info(f"Найдено поле Change: ID={field_id}, Name='{field_name}'")
                    return field_id

                search_terms = ['change']
                for term in search_terms:
                    if term.lower() in field_name.lower():
                        logger.info(f"Найдено похожее поле: ID={field_id}, Name='{field_name}'")
                        return field_id

            logger.warning("Поле Change не найдено")

        except Exception as e:
            logger.error(f"Ошибка получения полей Change: {e}")

        return None

    def get_completed_issues(self):
        now = datetime.now()
        current_month_start = now.replace(day=self.report_day, hour=self.report_hour,
                                          minute=self.report_minute, second=0, microsecond=0)

        if current_month_start.month == 1:
            previous_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        else:
            previous_month_start = current_month_start.replace(month=current_month_start.month - 1)

        start_date = previous_month_start.strftime('%Y-%m-%d %H:%M')
        end_date = current_month_start.strftime('%Y-%m-%d %H:%M')

        logger.info(f"Настройки периода: {self.report_day}-е число в {self.report_hour:02d}:{self.report_minute:02d}")
        logger.info(f"Период поиска: с {start_date} до {end_date}")

        release_title_field = self.release_title_field_id
        if release_title_field:
            logger.info(f"Использую ID поля Release title из конфигурации: {release_title_field}")
        else:
            logger.info("ID поля Release title не задан в конфигурации, выполняю автоматический поиск...")
            release_title_field = self.get_release_title_field_id()

        change_field = self.change_field_id
        if change_field:
            logger.info(f"Использую ID поля Change из конфигурации: {change_field}")
        else:
            logger.info("ID поля Change не задан в конфигурации, выполняю автоматический поиск...")
            change_field = self.get_change_field_id()

        jql = f'project = "{self.project_key}" AND status CHANGED TO "Done" DURING ("{start_date}", "{end_date}")'
        url = f"{self.jira_url}/rest/api/2/search"

        fields = 'key,summary,assignee,updated,status'
        if release_title_field:
            fields += f',{release_title_field}'
            logger.info(f"Добавлено поле Release title к запросу: {release_title_field}")
        else:
            logger.warning("Поле Release title не найдено, продолжаем без него")

        if change_field:
            fields += f',{change_field}'
            logger.info(f"Добавлено поле Change к запросу: {change_field}")
        else:
            logger.warning("Поле Change не найдено, продолжаем без него")

        params = {
            'jql': jql,
            'fields': fields,
            'maxResults': 100
        }

        try:
            logger.info(f"JQL запрос: {jql}")
            response = requests.get(
                url,
                params=params,
                auth=HTTPBasicAuth(self.jira_user, self.jira_password),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Найдено задач за период: {data['total']}")

            data['release_title_field_id'] = release_title_field
            data['change_field_id'] = change_field

            return data, "Готово"
        except Exception as e:
            logger.error(f"Ошибка при запросе задач: {e}")
            return None, None

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