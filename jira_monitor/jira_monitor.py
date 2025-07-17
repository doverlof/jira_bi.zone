
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from requests.auth import HTTPBasicAuth
from datetime import datetime

from .config import Config, ISSUE_TYPE_MAPPING, CATEGORY_ORDER
from .logger_config import setup_logger

logger = setup_logger()

class JiraCompletedMonitor:
    def __init__(self):
        config = Config()
        self.jira_url = config.jira_url
        self.jira_user = config.jira_user
        self.jira_password = config.jira_password
        self.project_key = config.project_key
        self.smtp_server = config.smtp_server
        self.smtp_port = config.smtp_port
        self.jira_external_url = config.jira_external_url
        self.email_user = config.email_user
        self.email_password = config.email_password
        self.recipients = config.recipients
        self.product_name = config.product_name
        self.report_day = config.report_day
        self.report_hour = config.report_hour
        self.report_minute = config.report_minute

    def get_issue_type_category(self, issue_type):
        return ISSUE_TYPE_MAPPING.get(issue_type, 'Прочие изменения')

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

        jql = f'project = "{self.project_key}" AND status CHANGED TO "Done" DURING ("{start_date}", "{end_date}")'
        url = f"{self.jira_url}/rest/api/2/search"

        params = {
            'jql': jql,
            'fields': 'key,summary,assignee,updated,status,issuetype',
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
            return data, "Готово"
        except Exception as e:
            logger.error(f"Ошибка при запросе задач: {e}")
            return None, None

    def send_batch_notification(self, issues_list, is_startup=False):
        if not issues_list:
            return True

        task_count = len(issues_list)
        startup_prefix = "[Автозапуск] " if is_startup else ""

        version = self.get_latest_release_version()

        if version:
            subject = f"{startup_prefix}Релиз BI.ZONE Continuous Penetration Testing {version}. Внутренняя рассылка"
        else:
            if task_count == 1:
                subject = f"{startup_prefix}Задача {issues_list[0]['key']} выполнена"
            else:
                subject = f"{startup_prefix}Выполнено задач: {task_count}"

        tasks_by_category = {}
        for issue in issues_list:
            issue_type = issue['fields']['issuetype']['name']

            logger.info(f"Найден тип задачи: '{issue_type}' для задачи {issue['key']}")

            category = self.get_issue_type_category(issue_type)
            if category not in tasks_by_category:
                tasks_by_category[category] = []
            tasks_by_category[category].append(issue)

        changes_html = ""

        for category in CATEGORY_ORDER:
            if category in tasks_by_category:
                tasks = tasks_by_category[category]
                changes_html += f"<li><strong>{category}</strong><ul>"

                for issue in tasks:
                    task_key = issue['key']
                    task_summary = issue['fields']['summary']
                    changes_html += f'<li><a href="{self.jira_external_url}/browse/{task_key}">{task_summary}</a></li>'

                changes_html += "</ul></li>"

        if version:
            greeting_text = f"Вышла новая версия {self.product_name} {version}"
        else:
            greeting_text = f"Выполнены задачи проекта {self.project_key}. Всего задач: {task_count}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 20px;">

            <p>Здравствуйте!</p>

            <p>{greeting_text}</p>

            <ol>
                {changes_html}
            </ol>

            <br>
            <p style="color: #888888; font-size: 14px;">С уважением,<br>
            Группа разработки EASM платформы, BI.ZONE</p>

        </body>
        </html>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email_user
        msg['To'] = ', '.join(self.recipients)

        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)

            task_keys = [issue['key'] for issue in issues_list]
            logger.info(f"Email отправлен для задач: {', '.join(task_keys)}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False