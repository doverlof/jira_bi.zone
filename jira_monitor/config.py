from __future__ import annotations
from pathlib import Path
from typing import List
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    jira_url: str
    jira_user: str
    jira_password: SecretStr
    jira_project_key: str
    jira_external_url: str

    release_title_field_id: str | None = None
    change_field_id: str | None = None

    smtp_server: str
    smtp_port: int = 587

    email_user: str
    email_password: SecretStr
    email_recipients: str

    product_name: str
    project_name: str

    report_day_of_month: int
    report_hour: int
    report_minute: int

    redis_host: str = "redis"
    redis_port: int = 6379

    @classmethod
    def validate_recipients(cls, v):
        if not v:
            raise ValueError('Список получателей не может быть пустым')
        return v

    @property
    def recipients_list(self) -> List[str]:
        return [email.strip() for email in self.email_recipients.split(',')]

    @property
    def redis_url(self) -> str:
        return f'redis://{self.redis_host}:{self.redis_port}/0'


CHANGE_MAPPING = {
    'New features': 'Новая функциональность',
    'Functionality update': 'Обновление существующей функциональности',
    'Performance enhancements': 'Улучшения производительности и технические доработки',
    'Bug fixes': 'Исправление ошибок',
    'Other changes': 'Прочие изменения'
}

CHANGE_ORDER = [
    'Новая функциональность',
    'Обновление существующей функциональности',
    'Улучшения производительности и технические доработки',
    'Исправление ошибок',
    'Прочие изменения'
]

settings = Settings()