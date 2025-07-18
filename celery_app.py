from celery import Celery
from celery.schedules import crontab
from jira_monitor.config import settings

app = Celery('jira_monitor',
             broker=settings.redis_url,
             backend=settings.redis_url)

app.config_from_object('celeryconfig')

app.conf.update(
    beat_schedule={
        'check-jira-tasks': {
            'task': 'jira_monitor.tasks.check_jira_tasks',
            # 'schedule': crontab(
            #     day_of_month=settings.report_day_of_month,
            #     hour=settings.report_hour,
            #     minute=settings.report_minute
            # ),
            'schedule': 10.0,
        }
    },
    beat_schedule_filename='celerybeat-schedule',
)

app.autodiscover_tasks(['jira_monitor'])

if __name__ == '__main__':
    app.start()