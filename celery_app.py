from celery import Celery
from celery.schedules import crontab


app = Celery('jira_monitor',
             broker='redis://redis:6379/0',
             backend='redis://redis:6379/0')

app.config_from_object('celeryconfig')

app.conf.update(
    beat_schedule={
        'check-jira-tasks': {
            'task': 'tasks.check_jira_tasks',
            'schedule': crontab(day_of_month=8, hour=13, minute=32),
        }
    },
    beat_schedule_filename='celerybeat-schedule',
)

app.autodiscover_tasks(['tasks'])

if __name__ == '__main__':
    app.start()