import requests
from requests.auth import HTTPBasicAuth
from ..logger_config import setup_logger

logger = setup_logger()


class JiraAuth:
    def __init__(self, jira_url: str, jira_user: str, jira_password: str):
        self.jira_url = jira_url
        self.jira_user = jira_user
        self.jira_password = jira_password
        self.auth = HTTPBasicAuth(jira_user, jira_password)

    def test_connection(self) -> bool:
        try:
            url = f"{self.jira_url}/rest/api/2/myself"
            response = requests.get(url, auth=self.auth, timeout=30)
            response.raise_for_status()

            user_info = response.json()
            logger.info(f"Jira подключение успешно. Пользователь: {user_info.get('displayName', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к Jira: {e}")
            return False

    def get_auth(self):
        return self.auth