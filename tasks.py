from celery_app import app
from celery.utils.log import get_task_logger
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
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
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        self.jira_url = os.getenv('JIRA_URL', 'http://localhost:8080')
        self.jira_user = os.getenv('JIRA_USER', 'admin')
        self.jira_password = os.getenv('JIRA_PASSWORD', 'password')
        self.project_key = os.getenv('JIRA_PROJECT_KEY', 'PROJECT')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER', 'your-email@gmail.com')
        self.email_password = os.getenv('EMAIL_PASSWORD', 'your-app-password')
        recipients_str = os.getenv('EMAIL_RECIPIENTS', 'recipient@example.com')
        self.recipients = [email.strip() for email in recipients_str.split(',')]
        self.recipients = [email.strip() for email in recipients_str.split(',')]

        if not os.path.exists('data'):
            os.makedirs('data')

        self.state_file = "data/jira_notifications_state.json"
        self.processed_file = "data/jira_processed_state.json"

        self.sent_notifications = set()
        self.processed_issues = set()
        self.load_state()

    def load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.sent_notifications = set(state.get('sent_notifications', []))
                    logger.info(f"Загружено {len(self.sent_notifications)} отправленных уведомлений")
        except Exception as e:
            logger.error(f"Ошибка загрузки состояния: {e}")
            self.sent_notifications = set()

        try:
            if os.path.exists(self.processed_file):
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.processed_issues = set(state.get('processed_issues', []))
                    logger.info(f"Загружено {len(self.processed_issues)} обработанных задач")
        except Exception as e:
            logger.error(f"Ошибка загрузки обработанных задач: {e}")
            self.processed_issues = set()

    def save_state(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'sent_notifications': list(self.sent_notifications),
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

            with open(self.processed_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'processed_issues': list(self.processed_issues),
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

            logger.info("Состояние сохранено")
        except Exception as e:
            logger.error(f"Ошибка сохранения состояния: {e}")

    def get_completed_issues(self):
        jql = f'project = "{self.project_key}" AND status = 10001'
        url = f"{self.jira_url}/rest/api/2/search"

        params = {
            'jql': jql,
            'fields': 'key,summary,assignee,updated,status',
            'maxResults': 100
        }

        try:
            response = requests.get(
                url,
                params=params,
                auth=HTTPBasicAuth(self.jira_user, self.jira_password),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Найдено задач в статусе 'Готово': {data['total']}")
            return data, "Готово"
        except Exception as e:
            logger.error(f"Ошибка при запросе задач: {e}")
            return None, None

    def send_batch_notification(self, issues_list, is_startup=False):
        if not issues_list:
            return True

        task_count = len(issues_list)
        startup_prefix = "[Автозапуск] " if is_startup else ""

        if task_count == 1:
            subject = f"{startup_prefix}Задача {issues_list[0]['key']} выполнена"
        else:
            subject = f"{startup_prefix}Выполнено задач: {task_count}"

        startup_note = ""
        if is_startup:
            startup_note = """
            <div style="background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 10px; margin: 10px 0;">
                <p><em>🤖 Автономная система обнаружила незафиксированные выполненные задачи</em></p>
            </div>
            """

        tasks_html = ""
        for i, issue in enumerate(issues_list, 1):
            task_key = issue['key']
            task_summary = issue['fields']['summary']
            assignee = issue['fields']['assignee']
            assignee_name = assignee['displayName'] if assignee else 'Не назначен'

            tasks_html += f"""
            <tr style="{'background-color: #f5f5f5;' if i % 2 == 0 else ''}">
                <td style="padding: 10px; border: 1px solid #ddd;">
                    <a href="{self.jira_url}/browse/{task_key}" style="color: #1976d2; text-decoration: none;">
                        <strong>{task_key}</strong>
                    </a>
                </td>
                <td style="padding: 10px; border: 1px solid #ddd;">{task_summary}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{assignee_name}</td>
            </tr>
            """

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px;">
                <h1>✅ {"Задача выполнена!" if task_count == 1 else f"Выполнено задач: {task_count}"}</h1>
            </div>

            {startup_note}

            <div style="padding: 20px;">
                <p><strong>Время:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
                <p><strong>Проект:</strong> {self.project_key}</p>
                <p><strong>Система:</strong> 🤖 Автономный мониторинг 24/7</p>

                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <thead>
                        <tr style="background-color: #4CAF50; color: white;">
                            <th style="padding: 12px; border: 1px solid #ddd;">Задача</th>
                            <th style="padding: 12px; border: 1px solid #ddd;">Описание</th>
                            <th style="padding: 12px; border: 1px solid #ddd;">Исполнитель</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tasks_html}
                    </tbody>
                </table>

                <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                    <p><strong>Выполнено:</strong> {task_count} {'задача' if task_count == 1 else 'задач'}</p>
                </div>
            </div>
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

            for issue in issues_list:
                self.sent_notifications.add(issue['key'])
            self.save_state()

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
        logger.info("Автономная проверка JIRA...")

        data, status_name = monitor.get_completed_issues()
        if not data:
            return "JIRA недоступна"

        current_issues = {issue['key'] for issue in data['issues']}
        new_completed = current_issues - monitor.processed_issues

        if new_completed:
            logger.info(f"Найдено {len(new_completed)} новых задач: {list(new_completed)}")
            new_issues = [issue for issue in data['issues'] if issue['key'] in new_completed]

            if new_issues:
                success = monitor.send_batch_notification(new_issues, is_startup=False)
                if success:
                    monitor.processed_issues.update(new_completed)
                    monitor.save_state()
                    return f"Обработано {len(new_issues)} задач автономно"
                else:
                    return "Ошибка отправки email"
            return None
        else:
            logger.info("Новых задач нет")
            return "Новых задач нет"

    except Exception as exc:
        logger.error(f"Ошибка в задаче: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@app.task(bind=True, max_retries=2)
def startup_check_jira_tasks(self):
    try:
        monitor = JiraCompletedMonitor()
        logger.info("Стартовая проверка...")

        data, status_name = monitor.get_completed_issues()
        if not data:
            return "JIRA недоступна при запуске"

        completed_issues = {issue['key'] for issue in data['issues']}
        unsent_notifications = completed_issues - monitor.sent_notifications

        if unsent_notifications:
            logger.info(f"Найдено {len(unsent_notifications)} неотправленных уведомлений")
            unsent_issues = [issue for issue in data['issues'] if issue['key'] in unsent_notifications]

            if unsent_issues:
                success = monitor.send_batch_notification(unsent_issues, is_startup=True)
                if success:
                    monitor.processed_issues.update(completed_issues)
                    monitor.save_state()
                    return f"Отправлено {len(unsent_issues)} стартовых уведомлений"
                return "Ошибка стартовой отправки"
            return None
        else:
            logger.info("Все уведомления актуальны")
            monitor.processed_issues = completed_issues
            monitor.save_state()
            return "Все уведомления актуальны"

    except Exception as exc:
        logger.error(f"Ошибка стартовой задачи: {exc}")
        raise self.retry(exc=exc, countdown=30)


@app.task
def reset_notifications():
    try:
        monitor = JiraCompletedMonitor()
        monitor.sent_notifications.clear()
        monitor.processed_issues.clear()
        monitor.save_state()
        logger.info("Уведомления сброшены")
        return "Уведомления сброшены"
    except Exception as e:
        logger.error(f"Ошибка сброса: {e}")
        return f"Ошибка: {e}"


@app.task
def get_status():
    try:
        monitor = JiraCompletedMonitor()
        return {
            'sent_notifications': len(monitor.sent_notifications),
            'processed_issues': len(monitor.processed_issues),
            'jira_url': monitor.jira_url,
            'project_key': monitor.project_key,
            'recipients': monitor.recipients,
            'timestamp': datetime.now().isoformat(),
            'status': 'Автономная работа активна'
        }
    except Exception as e:
        return {"error": str(e)}