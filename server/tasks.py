from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.signals import task_postrun
from server.models import Invoice
from operator import add, sub
from server.views.utils import sync_storage
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult


@shared_task
def cancel_reservation(invoice_id, **kwargs):
    invoice = Invoice.objects.get(pk=invoice_id)
    if invoice.status != 'payed':
        invoice.status = 'canceled'
        invoice.suspended_at = timezone.now()
        invoice.save()
        sync_storage(invoice.basket_id, add)
        return 'invoice canceled, storage synced successfully'


@task_postrun.connect
def task_postrun_handler(task_id=None, **kwargs):
    task_name = kwargs.get('kwargs')['task_name']
    task_result = TaskResult.objects.filter(task_id=task_id).first()
    description = f'{task_result.date_done}:, {task_result.result}, {task_result.traceback or ""}'
    task = PeriodicTask.objects.filter(name=task_name).update(description=description)
    return f'Return {task_id}'
