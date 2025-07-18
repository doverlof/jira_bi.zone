from typing import List, Dict, Any, Tuple
from ..logger_config import setup_logger

logger = setup_logger()


class EmailGenerator:
    def __init__(self, product_name: str, project_name: str, jira_external_url: str, project_key: str):
        self.product_name = product_name
        self.project_name = project_name
        self.jira_external_url = jira_external_url
        self.project_key = project_key

    def filter_issues_by_change(self, issues: List[Dict], change_field_id: str) -> List[Dict]:
        filtered = []
        for issue in issues:
            if change_field_id and change_field_id in issue['fields']:
                change_value = issue['fields'][change_field_id]
                if change_value:
                    if isinstance(change_value, dict):
                        change_text = change_value.get('value', '')
                    else:
                        change_text = str(change_value)

                    if change_text:
                        filtered.append(issue)
                        logger.info(f"Задача {issue['key']} включена в письмо с Change: '{change_text}'")
                    else:
                        logger.info(f"Задача {issue['key']} исключена - пустое значение Change")
                else:
                    logger.info(f"Задача {issue['key']} исключена - пустое поле Change")
            else:
                logger.info(f"Задача {issue['key']} исключена - поле Change отсутствует")
        return filtered

    def group_tasks_by_change(self, issues: List[Dict], change_field_id: str) -> Dict[str, List[Dict]]:
        change_mapping = {
            'New features': 'Новая функциональность',
            'Functionality update': 'Обновление существующей функциональности',
            'Performance enhancements': 'Улучшения производительности и технические доработки',
            'Bug fixes': 'Исправление ошибок',
            'Other changes': 'Прочие изменения'
        }

        tasks_by_change = {}
        for issue in issues:
            change_value = issue['fields'].get(change_field_id, '')

            if isinstance(change_value, dict):
                change_text = change_value.get('value', '')
            else:
                change_text = str(change_value) if change_value else ''

            logger.info(f"Найдено значение Change: '{change_text}' для задачи {issue['key']}")

            russian_change = change_mapping.get(change_text, change_text)

            if russian_change not in tasks_by_change:
                tasks_by_change[russian_change] = []
            tasks_by_change[russian_change].append(issue)

        return tasks_by_change

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

    def generate_email_content(self, issues_data: Dict[str, Any], version: str = None, is_startup: bool = False) -> \
    Tuple[str, str]:
        issues_list = issues_data.get('issues', [])
        release_title_field_id = issues_data.get('release_title_field_id')
        change_field_id = issues_data.get('change_field_id')

        if not issues_list:
            logger.info("Нет задач для формирования письма")
            return "", ""

        filtered_issues = self.filter_issues_by_change(issues_list, change_field_id)

        if not filtered_issues:
            logger.info("Нет задач с заполненным полем Change для формирования письма")
            return "", ""

        subject = self.generate_subject(filtered_issues, version, is_startup)

        tasks_by_change = self.group_tasks_by_change(filtered_issues, change_field_id)

        change_order = [
            'Новая функциональность',
            'Обновление существующей функциональности',
            'Улучшения производительности и технические доработки',
            'Исправление ошибок',
            'Прочие изменения'
        ]

        changes_html = ""
        group_counter = 0

        for change_type in change_order:
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
            if change_type not in change_order:
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

        greeting_text = f"Вышла новая версия {self.product_name} {version}" if version else f"Выполнены задачи проекта {self.project_key}. Всего задач: {len(filtered_issues)}"

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