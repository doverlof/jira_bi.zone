from celery import Celery
from datetime import timedelta
import os

app = Celery('jira_monitor', 
             broker='redis://redis:6379/0',
             backend='redis://redis:6379/0')

app.config_from_object('celeryconfig')

app.conf.update(
    beat_schedule={
        'check-jira-tasks': {
            'task': 'tasks.check_jira_tasks',
            'schedule': timedelta(seconds=30),
        },
        'startup-check': {
            'task': 'tasks.startup_check_jira_tasks',
            'schedule': timedelta(minutes=1),
            'options': {'expires': 15.0}
        }
    },
    beat_schedule_filename='celerybeat-schedule',
)

app.autodiscover_tasks(['tasks'])

if __name__ == '__main__':
    app.start()
