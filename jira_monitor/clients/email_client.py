from typing import List, Dict, Any, Tuple
from ..logger_config import setup_logger
from ..config import settings, CHANGE_ORDER, CHANGE_MAPPING

logger = setup_logger()


def _filter_issues_by_change(issues_list: List[Dict], change_field_id: str) -> List[Dict]:
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
                    logger.info(f"Задача {issue['key']} включена в письмо с Change: '{change_text}'")
                else:
                    logger.info(f"Задача {issue['key']} исключена - пустое значение Change")
            else:
                logger.info(f"Задача {issue['key']} исключена - пустое поле Change")
        else:
            logger.info(f"Задача {issue['key']} исключена - поле Change отсутствует")

    return filtered_issues


class EmailContentGenerator:
    def __init__(self):
        self.product_name = settings.product_name
        self.project_name = settings.project_name
        self.jira_external_url = settings.jira_external_url
        self.project_key = settings.jira_project_key

    def generate_email_content(
            self,
            issues_data: Dict[str, Any],
            version: str = None,
            is_startup: bool = False
    ) -> Tuple[str, str]:

        if isinstance(issues_data, dict):
            issues_list = issues_data.get('issues', [])
            release_title_field_id = issues_data.get('release_title_field_id')
            change_field_id = issues_data.get('change_field_id')
        else:
            issues_list = issues_data
            release_title_field_id = None
            change_field_id = None

        if not issues_list:
            logger.info("Нет задач для формирования письма")
            return "", ""

        filtered_issues = _filter_issues_by_change(issues_list, change_field_id)

        if not filtered_issues:
            logger.info("Нет задач с заполненным полем Change для формирования письма")
            return "", ""

        subject = self._generate_subject(filtered_issues, version, is_startup)

        html_content = self._generate_html_content(
            filtered_issues,
            release_title_field_id,
            change_field_id,
            version
        )

        return subject, html_content

    def _generate_subject(self, filtered_issues: List[Dict], version: str, is_startup: bool) -> str:
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

    def _generate_html_content(
            self,
            filtered_issues: List[Dict],
            release_title_field_id: str,
            change_field_id: str,
            version: str
    ) -> str:

        tasks_by_change = self._group_tasks_by_change(filtered_issues, change_field_id)

        changes_html = self._generate_changes_html(tasks_by_change, release_title_field_id)

        greeting_text = self._generate_greeting_text(version, len(filtered_issues))

        html_content = self._build_final_html(greeting_text, changes_html)

        logger.info("HTML содержимое письма сформировано")
        return html_content

    def _group_tasks_by_change(self, filtered_issues: List[Dict], change_field_id: str) -> Dict[str, List[Dict]]:
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

        return tasks_by_change

    def _generate_changes_html(self, tasks_by_change: Dict[str, List[Dict]], release_title_field_id: str) -> str:
        changes_html = ""
        group_counter = 0

        for change_type in CHANGE_ORDER:
            if change_type in tasks_by_change:
                group_counter += 1
                tasks = tasks_by_change[change_type]
                changes_html += f"{group_counter}. <strong>{change_type}:</strong><br>"
                changes_html += self._generate_tasks_html(tasks, group_counter, release_title_field_id)
                changes_html += "<br>"

        for change_type, tasks in tasks_by_change.items():
            if change_type not in CHANGE_ORDER:
                group_counter += 1
                changes_html += f"{group_counter}. <strong>{change_type}:</strong><br>"
                changes_html += self._generate_tasks_html(tasks, group_counter, release_title_field_id)
                changes_html += "<br>"

        return changes_html

    def _generate_tasks_html(self, tasks: List[Dict], group_counter: int, release_title_field_id: str) -> str:
        tasks_html = ""
        task_counter = 0

        for issue in tasks:
            task_counter += 1
            task_key = issue['key']

            release_title = self._get_release_title(issue, release_title_field_id, task_key)

            if release_title:
                tasks_html += f'{group_counter}.{task_counter}. <a href="{self.jira_external_url}/browse/{task_key}">{release_title}</a><br>'
            else:
                tasks_html += f'{group_counter}.{task_counter}. <a href="{self.jira_external_url}/browse/{task_key}">Задача без Release title</a><br>'

        return tasks_html

    def _get_release_title(self, issue: Dict, release_title_field_id: str, task_key: str) -> str:
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
                logger.warning(f"Поле Release title {release_title_field_id} не найдено в данных задачи {task_key}")
            else:
                logger.info(f"ID поля Release title не определен для задачи {task_key}")

        return release_title

    def _generate_greeting_text(self, version: str, task_count: int) -> str:
        if version:
            return f"Вышла новая версия {self.product_name} {version}"
        else:
            return f"Выполнены задачи проекта {self.project_key}. Всего задач: {task_count}"

    def _build_final_html(self, greeting_text: str, changes_html: str) -> str:
        return f"""
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