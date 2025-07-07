import os

# Получение настроек Redis из переменных окружения
redis_host = os.getenv('REDIS_HOST', 'redis')  # По умолчанию 'redis', но можно переопределить
redis_port = os.getenv('REDIS_PORT', '6379')

broker_url = f'redis://{redis_host}:{redis_port}/0'
result_backend = f'redis://{redis_host}:{redis_port}/0'

task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'Europe/Moscow'
enable_utc = True
broker_connection_retry_on_startup = True