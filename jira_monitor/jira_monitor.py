import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from requests.auth import HTTPBasicAuth
from datetime import datetime

from .config import Config, CHANGE_ORDER, CHANGE_MAPPING
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
        self.project_name = config.project_name
        self.report_day = config.report_day
        self.report_hour = config.report_hour
        self.report_minute = config.report_minute
        self.release_title_field_id = config.release_title_field_id
        self.change_field_id = config.change_field_id

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
        if isinstance(issues_data, dict):
            issues_list = issues_data.get('issues', [])
            release_title_field_id = issues_data.get('release_title_field_id')
            change_field_id = issues_data.get('change_field_id')
        else:
            issues_list = issues_data
            release_title_field_id = None
            change_field_id = None

        if not issues_list:
            return True

        filtered_issues = []
        for issue in issues_list:
            if change_field_id and change_field_id in issue['fields']:
                change_value = issue['fields'][change_field_id]
                if change_value:
                    if isinstance(change_value, dict):
                        change_text = change_value.get('value', '')
                    else:
                        change_text = str(change_value)

                    if change_text:
                        filtered_issues.append(issue)
                        logger.info(f"Задача {issue['key']} включена в отчет с Change: '{change_text}'")
                    else:
                        logger.info(f"Задача {issue['key']} исключена - пустое значение Change")
                else:
                    logger.info(f"Задача {issue['key']} исключена - пустое поле Change")
            else:
                logger.info(f"Задача {issue['key']} исключена - поле Change отсутствует")

        if not filtered_issues:
            logger.info("Нет задач с заполненным полем Change для отправки")
            return True

        task_count = len(filtered_issues)
        startup_prefix = "[Автозапуск] " if is_startup else ""

        version = self.get_latest_release_version()

        if version:
            subject = f"{startup_prefix}Релиз {self.product_name} {version}. Внутренняя рассылка"
        else:
            if task_count == 1:
                subject = f"{startup_prefix}Задача {filtered_issues[0]['key']} выполнена"
            else:
                subject = f"{startup_prefix}Выполнено задач: {task_count}"

        tasks_by_change = {}
        for issue in filtered_issues:
            change_value = issue['fields'].get(change_field_id, '')

            if isinstance(change_value, dict):
                change_text = change_value.get('value', '')
            else:
                change_text = str(change_value) if change_value else ''

            logger.info(f"Найдено значение Change: '{change_text}' для задачи {issue['key']}")

            russian_change = CHANGE_MAPPING.get(change_text, change_text)

            if russian_change not in tasks_by_change:
                tasks_by_change[russian_change] = []
            tasks_by_change[russian_change].append(issue)

        changes_html = ""
        group_counter = 0

        for change_type in CHANGE_ORDER:
            if change_type in tasks_by_change:
                group_counter += 1
                tasks = tasks_by_change[change_type]
                changes_html += f"{group_counter}. <strong>{change_type}:</strong><br>"

                task_counter = 0
                for issue in tasks:
                    task_counter += 1
                    task_key = issue['key']

                    release_title = ""
                    if release_title_field_id and release_title_field_id in issue['fields']:
                        release_title_value = issue['fields'][release_title_field_id]
                        if release_title_value:
                            release_title = release_title_value
                            logger.info(f"Найден Release title для задачи {task_key}: '{release_title_value}'")
                        else:
                            logger.info(f"Release title пустой для задачи {task_key}")
                    else:
                        if release_title_field_id:
                            logger.warning(
                                f"Поле Release title {release_title_field_id} не найдено в данных задачи {task_key}")
                        else:
                            logger.info(f"ID поля Release title не определен для задачи {task_key}")

                    if release_title:
                        changes_html += f'{group_counter}.{task_counter}. <a href="{self.jira_external_url}/browse/{task_key}">{release_title}</a><br>'
                    else:
                        changes_html += f'{group_counter}.{task_counter}. <a href="{self.jira_external_url}/browse/{task_key}">Задача без Release title</a><br>'

                changes_html += "<br>"

        for change_type, tasks in tasks_by_change.items():
            if change_type not in CHANGE_ORDER:
                group_counter += 1
                changes_html += f"{group_counter}. <strong>{change_type}:</strong><br>"

                task_counter = 0
                for issue in tasks:
                    task_counter += 1
                    task_key = issue['key']

                    release_title = ""
                    if release_title_field_id and release_title_field_id in issue['fields']:
                        release_title_value = issue['fields'][release_title_field_id]
                        if release_title_value:
                            release_title = release_title_value

                    if release_title:
                        changes_html += f'{group_counter}.{task_counter}. <a href="{self.jira_external_url}/browse/{task_key}">{release_title}</a><br>'
                    else:
                        changes_html += f'{group_counter}.{task_counter}. <a href="{self.jira_external_url}/browse/{task_key}">Задача без Release title</a><br>'

                changes_html += "<br>"

        if version:
            greeting_text = f"Вышла новая версия {self.product_name} {version}"
        else:
            greeting_text = f"Выполнены задачи проекта {self.project_key}. Всего задач: {task_count}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 20px;">

            <p>Здравствуйте!</p>

            <p>{greeting_text}</p>

            <p><strong>Что нового:</strong></p>

            {changes_html}

            <br>
            <p style="color: #888888; font-size: 14px;">С уважением,<br>
            Группа разработки {self.project_name} платформы, BI.ZONE</p>

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

            task_keys = [issue['key'] for issue in filtered_issues]
            logger.info(f"Email отправлен для задач: {', '.join(task_keys)}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False