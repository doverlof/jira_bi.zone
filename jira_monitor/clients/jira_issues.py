import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from ..logger_config import setup_logger

logger = setup_logger()


class JiraIssues:
    def __init__(self, jira_url: str, auth, project_key: str, report_day: int, report_hour: int, report_minute: int):
        self.jira_url = jira_url
        self.auth = auth
        self.project_key = project_key
        self.report_day = report_day
        self.report_hour = report_hour
        self.report_minute = report_minute

    def get_field_id(self, field_name: str) -> Optional[str]:
        try:
            url = f"{self.jira_url}/rest/api/2/field"
            response = requests.get(url, auth=self.auth, timeout=30)
            response.raise_for_status()
            fields = response.json()

            for field in fields:
                if field.get('name', '').lower() == field_name.lower():
                    logger.info(f"Найдено поле {field_name}: ID={field['id']}")
                    return field['id']

            logger.warning(f"Поле {field_name} не найдено")
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска поля {field_name}: {e}")
            return None

    def get_completed_issues(self, release_title_field_id: str = None, change_field_id: str = None) -> Tuple[
        Dict[str, Any], str]:
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

            logger.info(f"Период поиска: с {start_date} до {end_date}")

            if not release_title_field_id:
                release_title_field_id = self.get_field_id('Release title')

            if not change_field_id:
                change_field_id = self.get_field_id('Change')

            jql = f'project = "{self.project_key}" AND status CHANGED TO "Done" DURING ("{start_date}", "{end_date}")'

            fields = 'key,summary,assignee,updated,status'
            if release_title_field_id:
                fields += f',{release_title_field_id}'
            if change_field_id:
                fields += f',{change_field_id}'

            url = f"{self.jira_url}/rest/api/2/search"
            params = {
                'jql': jql,
                'fields': fields,
                'maxResults': 100
            }

            logger.info(f"JQL запрос: {jql}")
            response = requests.get(url, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()
            data = response.json()

            logger.info(f"Найдено задач за период: {data['total']}")

            result = {
                'issues': data['issues'],
                'total': data['total'],
                'release_title_field_id': release_title_field_id,
                'change_field_id': change_field_id
            }

            return result, "Готово"

        except Exception as e:
            logger.error(f"Ошибка при запросе задач: {e}")
            return {'issues': [], 'total': 0}, None