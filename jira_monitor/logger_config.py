import os
import logging
from celery.utils.log import get_task_logger


def setup_logger():
    logger = get_task_logger(__name__)

    if not os.path.exists('logs'):
        os.makedirs('logs')

    file_handler = logging.FileHandler('logs/jira_monitor.log')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
