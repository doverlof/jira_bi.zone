from celery import Celery
from celery.schedules import crontab
from jira_monitor.config import settings

redis = settings.redis_settings

app = Celery('jira_monitor',
             broker=redis.redis_url,
             backend=redis.redis_url)

app.config_from_object('celeryconfig')

report = settings.report_settings
app.conf.update(
    beat_schedule={
        'check-jira-tasks': {
            'task': 'jira_monitor.tasks.check_jira_tasks',
            # 'schedule': crontab(
            #     day_of_month=settings.report_day_of_month,
            #     hour=settings.report_hour,
            #     minute=settings.report_minute
            # ),
            'schedule': 20.0,
        }
    },
    beat_schedule_filename='celerybeat-schedule',
)

app.autodiscover_tasks(['jira_monitor'])

if __name__ == '__main__':
    app.start()