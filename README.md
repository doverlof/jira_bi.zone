## Запуск через Docker

1. Создайте файл `.env`:

```bash
REDIS_HOST=172.18.0.2
REDIS_PORT=6379

JIRA_URL=http://host.docker.internal:8080
JIRA_EXTERNAL_URL=http://localhost:8080
PRODUCT_NAME=BI.ZONE Continuous Penetration Testing
PROJECT_NAME=EASM
JIRA_USER=admin
JIRA_PASSWORD=admin
JIRA_PROJECT_KEY=TEST

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=
EMAIL_PASSWORD=
EMAIL_RECIPIENTS=

REPORT_DAY_OF_MONTH=1
REPORT_HOUR=9
REPORT_MINUTE=0
```

2. Запустите:

```bash
docker-compose up -d
```

3. Проверьте статус:

```bash
docker-compose logs -f jira-monitor
```

## Локальный запуск

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Запустите Redis:

```bash
redis-server
```

3. Измените в `.env`:

```bash
REDIS_HOST=localhost
```

4. Запустите систему:

```bash
python management.py both
```

## Команды управления

```bash
python management.py both
python management.py status
python management.py reset
```

## Проверка работы

```bash
tail -f logs/jira_monitor.log
docker-compose logs -f jira-monitor
```

## временно

```bash
docker-compose down 
docker-compose build --no-cache
docker-compose up -d
docker-compose logs -f jira-monitor
```