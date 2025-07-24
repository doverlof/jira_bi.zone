from jira import JIRA
from ..logger_config import setup_logger

logger = setup_logger()

class UserClient:
    def __init__(
            self,
            jira_url: str,
            jira_token: str,
    ):
        self.jira = JIRA(
            token_auth=jira_token,
            options={"server": jira_url, "verify": False},
            async_=True,
        )