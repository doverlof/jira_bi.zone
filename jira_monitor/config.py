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
        self.project_name = os.getenv('PROJECT_NAME')
        self.recipients = [email.strip() for email in recipients_str.split(',')]
        self.report_day = int(os.getenv('REPORT_DAY_OF_MONTH'))
        self.report_hour = int(os.getenv('REPORT_HOUR'))
        self.report_minute = int(os.getenv('REPORT_MINUTE'))
        self.release_title_field_id = os.getenv('RELEASE_TITLE_FIELD_ID')
        self.change_field_id = os.getenv('CHANGE_FIELD_ID')


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