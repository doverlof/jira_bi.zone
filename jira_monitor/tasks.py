from celery_app import app
from datetime import datetime

from .jira_monitor import JiraCompletedMonitor
from .logger_config import setup_logger

logger = setup_logger()

@app.task(bind=True, max_retries=3)
def check_jira_tasks(self):
    try:
        monitor = JiraCompletedMonitor()
        logger.info("Отправка ежемесячного отчета...")

        data, status_name = monitor.get_completed_issues()
        if not data:
            return "JIRA недоступна"

        if data['issues']:
            logger.info(f"Найдено {len(data['issues'])} задач за период")

            success = monitor.send_batch_notification(data['issues'], is_startup=False)
            if success:
                return f"Отправлен ежемесячный отчет по {len(data['issues'])} задачам"
            else:
                return "Ошибка отправки email"
        else:
            logger.info("За указанный период задач не найдено")
            return "За указанный период задач не найдено"

    except Exception as exc:
        logger.error(f"Ошибка в задаче: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@app.task(bind=True, max_retries=2)
def startup_check_jira_tasks(self):
    try:
        monitor = JiraCompletedMonitor()
        logger.info("Стартовая проверка отчета...")

        data, status_name = monitor.get_completed_issues()
        if not data:
            return "JIRA недоступна при запуске"

        if data['issues']:
            logger.info(f"При запуске найдено {len(data['issues'])} задач за период")

            success = monitor.send_batch_notification(data['issues'], is_startup=True)
            if success:
                return f"Отправлен стартовый отчет по {len(data['issues'])} задачам"
            return "Ошибка стартовой отправки"
        else:
            logger.info("При запуске за указанный период задач не найдено")
            return "При запуске за указанный период задач не найдено"

    except Exception as exc:
        logger.error(f"Ошибка стартовой задачи: {exc}")
        raise self.retry(exc=exc, countdown=30)


@app.task
def reset_notifications():
    try:
        logger.info("Сброс не требуется - система отправляет периодические отчеты")
        return "Система отправляет периодические отчеты, сброс не требуется"
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return f"Ошибка: {e}"


@app.task
def get_status():
    try:
        monitor = JiraCompletedMonitor()
        return {
            'jira_url': monitor.jira_url,
            'project_key': monitor.project_key,
            'recipients': monitor.recipients,
            'timestamp': datetime.now().isoformat(),
            'status': 'Система отправляет периодические отчеты за указанный период'
        }
    except Exception as e:
        return {"error": str(e)}
