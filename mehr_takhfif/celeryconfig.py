# worker: celery -A [project-name] worker --loglevel=info
# celery -A mehr_takhfif worker -l info

# schedule(beat): celery -A mehr_takhfif beat
# celery -A mehr_takhfif beat -s /home/celery/var/run/celerybeat-schedule

# django scheduler
# celery -A mehr_takhfif beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# one command for development
# celery -A mehr_takhfif worker --beat --scheduler django --loglevel=info


from mehr_takhfif.settings_var import broker_url

cache_backend = 'django-cache'
result_backend = 'django-db'
# result_backend = 'redis://192.168.1.95:6379/11'
broker_url = broker_url
# accept_content = ['json']
# task_serializer = 'json'
# timezone = 'UTC'
# time_zone = 'UTC'
