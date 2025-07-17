import os

class Config:
    def __init__(self):
        self.jira_url = os.getenv('JIRA_URL')
        self.jira_user = os.getenv('JIRA_USER')
        self.jira_password = os.getenv('JIRA_PASSWORD')
        self.project_key = os.getenv('JIRA_PROJECT_KEY')
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT'))
        self.jira_external_url = os.getenv('JIRA_EXTERNAL_URL')
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        recipients_str = os.getenv('EMAIL_RECIPIENTS')
        self.product_name = os.getenv('PRODUCT_NAME')
        self.recipients = [email.strip() for email in recipients_str.split(',')]
        self.report_day = int(os.getenv('REPORT_DAY_OF_MONTH'))
        self.report_hour = int(os.getenv('REPORT_HOUR'))
        self.report_minute = int(os.getenv('REPORT_MINUTE'))

ISSUE_TYPE_MAPPING = {
    'Ошибка': 'Исправление ошибок',
    'История': 'Обновление существующей функциональности',
    'Задача': 'Прочие изменения',
    'Bug': 'Исправление ошибок',
    'Story': 'Обновление существующей функциональности'
}

CATEGORY_ORDER = [
    'Обновление существующей функциональности',
    'Исправление ошибок',
    'Прочие изменения'
]