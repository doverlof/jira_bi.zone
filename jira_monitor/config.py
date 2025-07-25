from __future__ import annotations
from pathlib import Path
from typing import List
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).parent.parent


class JiraSettings(BaseModel):
    jira_url: str
    jira_token: SecretStr
    jira_project_key: str
    jira_external_url: str
    release_title_field_id: str | None = None
    change_field_id: str | None = None


class SmtpSettings(BaseModel):
    smtp_server: str
    smtp_port: int = 587
    email_user: str
    email_password: SecretStr


class EmailSettings(BaseModel):
    email_recipients: str

    @property
    def recipients_list(self) -> List[str]:
        return [email.strip() for email in self.email_recipients.split(',')]


class ProjectSettings(BaseModel):
    product_name: str
    project_name: str


class ReportSettings(BaseModel):
    report_day_of_month: int
    report_hour: int
    report_minute: int


class RedisSettings(BaseModel):
    redis_host: str = "redis"
    redis_port: int = 6379

    @property
    def redis_url(self) -> str:
        return f'redis://{self.redis_host}:{self.redis_port}/0'


class ChangeMapping:
    MAPPING = {
        'New features': 'Новая функциональность',
        'Functionality update': 'Обновление существующей функциональности',
        'Performance enhancements': 'Улучшения производительности и технические доработки',
        'Bug fixes': 'Исправление ошибок',
        'Other changes': 'Прочие изменения'
    }

    ORDER = [
        'Новая функциональность',
        'Обновление существующей функциональности',
        'Улучшения производительности и технические доработки',
        'Исправление ошибок',
        'Прочие изменения'
    ]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    jira_settings: JiraSettings
    smtp_settings: SmtpSettings
    email_settings: EmailSettings
    project_settings: ProjectSettings
    report_settings: ReportSettings
    redis_settings: RedisSettings


settings = Settings()

CHANGE_MAPPING = ChangeMapping.MAPPING
CHANGE_ORDER = ChangeMapping.ORDER