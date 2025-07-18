from jira_monitor.config import settings

broker_url = settings.redis_url
result_backend = settings.redis_url

task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'Europe/Moscow'
enable_utc = True
broker_connection_retry_on_startup = True