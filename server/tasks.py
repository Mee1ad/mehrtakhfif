# from celery import Celery

# redis = 'redis://192.168.1.95'
# app = Celery('tasks', backend=redis, broker=redis)

# @app.task
# def add(x, y):
#     return x + y


# job = add.delay(2, 3)
from __future__ import absolute_import, unicode_literals
from celery import shared_task


@shared_task
def hello(x, y):
    return 'hello'


@shared_task
def fuck(x, y):
    return 'fuck'


@shared_task
def shit(x, y):
    return 'shit'