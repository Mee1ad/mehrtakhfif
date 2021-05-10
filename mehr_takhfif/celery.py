from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mehr_takhfif.settings')

app = Celery('mehr_takhfif')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
# app.config_from_object('django.conf:settings', namespace='CELERY')

app.config_from_object('mehr_takhfif.celeryconfig')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "backup": {
        "task": "core.tasks.backup",
        "schedule": crontab(hour=15, minute=00)
    },
    "mediabackup": {
        "task": "core.tasks.mediabackup",
        # "schedule": crontab(hour=15, minute=15, day_of_week=1)
        "schedule": crontab(hour=15, minute=15)
    },
}
