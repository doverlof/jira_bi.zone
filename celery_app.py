from celery import Celery
from celery.schedules import crontab
import os

app = Celery('jira_monitor',
             broker='redis://redis:6379/0',
             backend='redis://redis:6379/0')

app.config_from_object('celeryconfig')

report_day = int(os.getenv('REPORT_DAY_OF_MONTH'))
report_hour = int(os.getenv('REPORT_HOUR'))
report_minute = int(os.getenv('REPORT_MINUTE'))

app.conf.update(
    beat_schedule={
        'check-jira-tasks': {
            'task': 'tasks.check_jira_tasks',
            'schedule': crontab(day_of_month=report_day, hour=report_hour, minute=report_minute),
        }
    },
    beat_schedule_filename='celerybeat-schedule',
)

app.autodiscover_tasks(['tasks'])

if __name__ == '__main__':
    app.start()