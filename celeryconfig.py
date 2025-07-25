from jira_monitor.config import settings

redis = settings.redis_settings

broker_url = redis.redis_url
result_backend = redis.redis_url

task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'Europe/Moscow'
enable_utc = True
broker_connection_retry_on_startup = True