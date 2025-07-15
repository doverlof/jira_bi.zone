from celery_app import app
from celery.utils.log import get_task_logger
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from requests.auth import HTTPBasicAuth
from datetime import datetime
import logging

logger = get_task_logger(__name__)

if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = logging.FileHandler('logs/jira_monitor.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class JiraCompletedMonitor:
    def __init__(self):
        self.jira_url = os.getenv('JIRA_URL')
        self.jira_user = os.getenv('JIRA_USER')
        self.jira_password = os.getenv('JIRA_PASSWORD')
        self.project_key = os.getenv('JIRA_PROJECT_KEY')
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT'))
        self.jira_external_url = os.getenv('JIRA_EXTERNAL_URL')
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        recipients_str = os.getenv('EMAIL_RECIPIENTS')
        self.recipients = [email.strip() for email in recipients_str.split(',')]

    def get_issue_type_category(self, issue_type):
        type_mapping = {
            'Ошибка': 'Исправление ошибок',
            'История': 'Обновление существующей функциональности',
            'Задача': 'Прочие изменения',
            # На всякий случай английские варианты
            'Bug': 'Исправление ошибок',
            'Story': 'Обновление существующей функциональности'
        }
        return type_mapping.get(issue_type, 'Прочие изменения')

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
        # Получаем настройки периода из .env
        report_day = int(os.getenv('REPORT_DAY_OF_MONTH'))
        report_hour = int(os.getenv('REPORT_HOUR'))
        report_minute = int(os.getenv('REPORT_MINUTE'))

        from datetime import datetime

        now = datetime.now()
        current_month_start = now.replace(day=report_day, hour=report_hour, minute=report_minute, second=0,
                                          microsecond=0)

        if current_month_start.month == 1:
            previous_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        else:
            previous_month_start = current_month_start.replace(month=current_month_start.month - 1)

        start_date = previous_month_start.strftime('%Y-%m-%d %H:%M')
        end_date = current_month_start.strftime('%Y-%m-%d %H:%M')

        logger.info(f"Настройки периода: {report_day}-е число в {report_hour:02d}:{report_minute:02d}")
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

        category_order = [
            'Обновление существующей функциональности',
            'Исправление ошибок',
            'Прочие изменения'
        ]

        changes_html = ""

        for category in category_order:
            if category in tasks_by_category:
                tasks = tasks_by_category[category]
                changes_html += f"<li><strong>{category}</strong><ul>"

                for issue in tasks:
                    task_key = issue['key']
                    task_summary = issue['fields']['summary']
                    changes_html += f'<li><a href="{self.jira_external_url}/browse/{task_key}">{task_summary}</a></li>'

                changes_html += "</ul></li>"

        if version:
            greeting_text = f"Вышла новая версия BI.ZONE Continuous Penetration Testing {version}"
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


@app.task(bind=True, max_retries=3)
def check_jira_tasks(self):
    try:
        monitor = JiraCompletedMonitor()
        logger.info("Отправка ежемесячного отчета...")

        data, status_name = monitor.get_completed_issues()
        if not data:
            return "JIRA недоступна"

        if data['issues']:
            logger.info(f"Найдено {len(data['issues'])} задач за период")

            success = monitor.send_batch_notification(data['issues'], is_startup=False)
            if success:
                return f"Отправлен ежемесячный отчет по {len(data['issues'])} задачам"
            else:
                return "Ошибка отправки email"
        else:
            logger.info("За указанный период задач не найдено")
            return "За указанный период задач не найдено"

    except Exception as exc:
        logger.error(f"Ошибка в задаче: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@app.task(bind=True, max_retries=2)
def startup_check_jira_tasks(self):
    try:
        monitor = JiraCompletedMonitor()
        logger.info("Стартовая проверка отчета...")

        data, status_name = monitor.get_completed_issues()
        if not data:
            return "JIRA недоступна при запуске"

        if data['issues']:
            logger.info(f"При запуске найдено {len(data['issues'])} задач за период")

            success = monitor.send_batch_notification(data['issues'], is_startup=True)
            if success:
                return f"Отправлен стартовый отчет по {len(data['issues'])} задачам"
            return "Ошибка стартовой отправки"
        else:
            logger.info("При запуске за указанный период задач не найдено")
            return "При запуске за указанный период задач не найдено"

    except Exception as exc:
        logger.error(f"Ошибка стартовой задачи: {exc}")
        raise self.retry(exc=exc, countdown=30)


@app.task
def reset_notifications():
    try:
        logger.info("Сброс не требуется - система отправляет периодические отчеты")
        return "Система отправляет периодические отчеты, сброс не требуется"
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return f"Ошибка: {e}"


@app.task
def get_status():
    try:
        monitor = JiraCompletedMonitor()
        return {
            'jira_url': monitor.jira_url,
            'project_key': monitor.project_key,
            'recipients': monitor.recipients,
            'timestamp': datetime.now().isoformat(),
            'status': 'Система отправляет периодические отчеты за указанный период'
        }
    except Exception as e:
        return {"error": str(e)}