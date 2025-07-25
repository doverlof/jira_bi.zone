from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Tuple
from ..logger_config import setup_logger
from ..config import CHANGE_MAPPING, CHANGE_ORDER

logger = setup_logger()


def group_tasks_by_change(issues: List[Dict], change_field_id: str) -> Dict[str, List[Dict]]:
    tasks_by_change = {}
    for issue in issues:
        change_value = issue['fields'].get(change_field_id, '')

        if isinstance(change_value, dict):
            change_text = change_value.get('value', '')
        else:
            change_text = str(change_value) if change_value else ''

        logger.info(f"Группировка по Change: '{change_text}' для задачи {issue['key']}")

        russian_change = CHANGE_MAPPING.get(change_text, change_text)

        if russian_change not in tasks_by_change:
            tasks_by_change[russian_change] = []
        tasks_by_change[russian_change].append(issue)

    return tasks_by_change


class EmailClient:
    def __init__(self, smtp_client, jira_client, product_name: str, project_name: str, jira_external_url: str,
                 project_key: str):
        self.smtp_client = smtp_client
        self.jira_client = jira_client
        self.product_name = product_name
        self.project_name = project_name
        self.jira_external_url = jira_external_url
        self.project_key = project_key

    def get_latest_release_version(self):
        try:
            project = self.jira_client.project(self.project_key)
            versions = self.jira_client.project_versions(project)

            released_versions = [v for v in versions if v.released]

            if released_versions:
                latest_version = max(released_versions, key=lambda x: x.releaseDate or '')
                return latest_version.name
            elif versions:
                latest_version = max(versions, key=lambda x: x.id)
                return latest_version.name

        except Exception as e:
            logger.error(f"Ошибка получения версий: {e}")

        return None

    def generate_subject(self, filtered_issues: List[Dict], version: str = None, is_startup: bool = False) -> str:
        task_count = len(filtered_issues)
        startup_prefix = "[Автозапуск] " if is_startup else ""

        if version:
            subject = f"{startup_prefix}Релиз {self.product_name} {version}. Внутренняя рассылка"
        else:
            if task_count == 1:
                subject = f"{startup_prefix}Задача {filtered_issues[0]['key']} выполнена"
            else:
                subject = f"{startup_prefix}Выполнено задач: {task_count}"

        logger.info(f"Сформирована тема письма: {subject}")
        return subject

    def generate_html_content(self, issues_data: Dict[str, Any], is_startup: bool = False) -> Tuple[str, str]:
        issues_list = issues_data.get('issues', [])
        release_title_field_id = issues_data.get('release_title_field_id')
        change_field_id = issues_data.get('change_field_id')

        if not issues_list:
            logger.info("Нет задач для формирования письма")
            return "", ""

        version = self.get_latest_release_version()
        subject = self.generate_subject(issues_list, version, is_startup)

        tasks_by_change = group_tasks_by_change(issues_list, change_field_id)

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

                    release_title = issue['fields'].get(release_title_field_id, '') if release_title_field_id else ''

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

                    release_title = issue['fields'].get(release_title_field_id, '') if release_title_field_id else ''

                    if release_title:
                        changes_html += f'{group_counter}.{task_counter}. <a href="{self.jira_external_url}/browse/{task_key}">{release_title}</a><br>'
                    else:
                        changes_html += f'{group_counter}.{task_counter}. <a href="{self.jira_external_url}/browse/{task_key}">Задача без Release title</a><br>'

                changes_html += "<br>"

        greeting_text = f"Вышла новая версия {self.product_name} {version}" if version else f"Выполнены задачи проекта {self.project_key}. Всего задач: {len(issues_list)}"

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

        logger.info("HTML содержимое письма сформировано")
        return subject, html_content

    def send_email(self, recipients: List[str], subject: str, html_content: str) -> bool:
        try:
            with self.smtp_client.get_connection() as server:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.smtp_client.email_user
                msg['To'] = ', '.join(recipients)

                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(html_part)

                server.send_message(msg)

            logger.info(f"Email отправлен получателям: {', '.join(recipients)}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки email: {e}")
            return False

    def send_simple_email(self, recipients: List[str], subject: str, text_content: str) -> bool:
        try:
            with self.smtp_client.get_connection() as server:
                msg = MIMEText(text_content, 'plain', 'utf-8')
                msg['Subject'] = subject
                msg['From'] = self.smtp_client.email_user
                msg['To'] = ', '.join(recipients)

                server.send_message(msg)

            logger.info(f"Простое email отправлено получателям: {', '.join(recipients)}")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки простого email: {e}")
            return False

    def generate_simple_notification(self, issue_key: str, summary: str) -> Tuple[str, str]:
        subject = f"Задача {issue_key} выполнена"

        text_content = f"""
Здравствуйте!

Выполнена задача: {issue_key} - {summary}

Ссылка: {self.jira_external_url}/browse/{issue_key}

С уважением,
Группа разработки {self.project_name} платформы, BI.ZONE
        """

        logger.info(f"Сформировано простое уведомление для задачи {issue_key}")
        return subject, text_content