from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.signals import task_postrun
from server.models import Invoice
from operator import add
from server.utils import sync_storage
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult


@shared_task
def cancel_reservation(invoice_id, **kwargs):
    invoice = Invoice.objects.get(pk=invoice_id)
    if invoice.status != 2:  # payed
        invoice.status = 3  # canceled
        invoice.suspended_at = timezone.now()
        invoice.save()
        sync_storage(invoice.basket_id, add)
        return 'invoice canceled, storage synced successfully'


@task_postrun.connect
def task_postrun_handler(task_id=None, **kwargs):
    task = kwargs.get('kwargs', None)
    if task:
        task_name = task['task_name']
        task_result = TaskResult.objects.filter(task_id=task_id).first()
        description = f'{task_result.date_done}:, {task_result.result}, {task_result.traceback or ""}'
        PeriodicTask.objects.filter(name=task_name).update(description=description)
        return f'Return {task_id}'
