# worker: celery -A [project-name] worker --loglevel=info
# celery -A mehr_takhfif worker -l info

# schedule(beat): celery -A mehr_takhfif beat
# celery -A mehr_takhfif beat -s /home/celery/var/run/celerybeat-schedule

# django scheduler
# celery -A mehr_takhfif beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# one command for development
# celery -A mehr_takhfif worker --beat --scheduler django --loglevel=info


cache_backend = 'django-cache'
broker_url = 'redis://192.168.1.95:6379/10'
accept_content = ['json']
result_backend = 'redis://192.168.1.95:6379/11'
task_serializer = 'json'
timezone = 'UTC'
time_zone = 'UTC'

beat_schedule = {
    # 'add-every-5-seconds': {
    #     'task': 'server.tasks.fuck',
    #     'schedule': 5,
    #     'args': (16, 16)
    # },
}