from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from ..logger_config import setup_logger

logger = setup_logger()


class IssuesClient:
    def __init__(self, jira_client, project_key: str, report_day: int, report_hour: int, report_minute: int):
        self.jira = jira_client
        self.project_key = project_key
        self.report_day = report_day
        self.report_hour = report_hour
        self.report_minute = report_minute

    def get_field_id(self, field_name: str) -> Optional[str]:
        try:
            fields = self.jira.fields()

            for field in fields:
                if field['name'].lower() == field_name.lower():
                    logger.info(f"Найдено поле {field_name}: ID={field['id']}")
                    return field['id']

            logger.warning(f"Поле {field_name} не найдено")
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска поля {field_name}: {e}")
            return None

    def filter_completed_issues(self, release_title_field_id: str = None, change_field_id: str = None) -> tuple[dict[
        str, list[Any] | int], None] | tuple[dict[str, list[Any] | int | str | None], str]:
        try:
            now = datetime.now()
            current_period = now.replace(day=self.report_day, hour=self.report_hour,
                                         minute=self.report_minute, second=0, microsecond=0)

            if current_period.month == 1:
                previous_period = current_period.replace(year=current_period.year - 1, month=12)
            else:
                previous_period = current_period.replace(month=current_period.month - 1)

            start_date = previous_period.strftime('%Y-%m-%d %H:%M')
            end_date = current_period.strftime('%Y-%m-%d %H:%M')

            logger.info(f"Период фильтрации: с {start_date} до {end_date}")
            logger.info(
                f"Настройки периода: {self.report_day}-е число в {self.report_hour:02d}:{self.report_minute:02d}")

            if not release_title_field_id:
                logger.info("ID поля Release title не задан, выполняю автоматический поиск...")
                release_title_field_id = self.get_field_id('Release title')
            else:
                logger.info(f"Использую ID поля Release title из конфигурации: {release_title_field_id}")

            if not change_field_id:
                logger.info("ID поля Change не задан, выполняю автоматический поиск...")
                change_field_id = self.get_field_id('Change')
            else:
                logger.info(f"Использую ID поля Change из конфигурации: {change_field_id}")

            jql = f'project = "{self.project_key}" AND status CHANGED TO "Done" DURING ("{start_date}", "{end_date}")'

            fields = 'key,summary,assignee,updated,status'
            if release_title_field_id:
                fields += f',{release_title_field_id}'
            if change_field_id:
                fields += f',{change_field_id}'

            logger.info(f"JQL фильтр: {jql}")

            issues = self.jira.search_issues(
                jql,
                fields=fields,
                maxResults=100
            )

            issues_data = []
            for issue in issues:
                issue_dict = {
                    'key': issue.key,
                    'fields': {}
                }

                if hasattr(issue.fields, 'summary'):
                    issue_dict['fields']['summary'] = issue.fields.summary
                if hasattr(issue.fields, 'assignee') and issue.fields.assignee:
                    issue_dict['fields']['assignee'] = issue.fields.assignee.displayName
                if hasattr(issue.fields, 'updated'):
                    issue_dict['fields']['updated'] = str(issue.fields.updated)
                if hasattr(issue.fields, 'status'):
                    issue_dict['fields']['status'] = issue.fields.status.name

                if release_title_field_id:
                    field_value = getattr(issue.fields, release_title_field_id, None)
                    if field_value:
                        issue_dict['fields'][release_title_field_id] = field_value

                if change_field_id:
                    field_value = getattr(issue.fields, change_field_id, None)
                    if field_value:
                        if hasattr(field_value, 'value'):
                            issue_dict['fields'][change_field_id] = {'value': field_value.value}
                        else:
                            issue_dict['fields'][change_field_id] = field_value

                issues_data.append(issue_dict)

            logger.info(f"Отфильтровано задач за период: {len(issues_data)}")

            filtered_issues = []
            for issue in issues_data:
                if change_field_id and change_field_id in issue['fields']:
                    change_value = issue['fields'][change_field_id]
                    if change_value:
                        if isinstance(change_value, dict):
                            change_text = change_value.get('value', '')
                        else:
                            change_text = str(change_value)

                        if change_text:
                            filtered_issues.append(issue)
                            logger.info(f"Задача {issue['key']} прошла фильтр Change: '{change_text}'")
                        else:
                            logger.info(f"Задача {issue['key']} отфильтрована - пустое значение Change")
                    else:
                        logger.info(f"Задача {issue['key']} отфильтрована - пустое поле Change")
                else:
                    logger.info(f"Задача {issue['key']} отфильтрована - поле Change отсутствует")

            result = {
                'issues': filtered_issues,
                'total': len(filtered_issues),
                'release_title_field_id': release_title_field_id,
                'change_field_id': change_field_id
            }

            return result, "Готово"

        except Exception as e:
            logger.error(f"Ошибка фильтрации задач: {e}")
            return {'issues': [], 'total': 0}, None