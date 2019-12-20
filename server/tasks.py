from __future__ import absolute_import, unicode_literals

from celery import shared_task
from server.models import Invoice
from operator import add, sub
from server.views.utils import sync_storage
from django.utils import timezone


@shared_task
def cancel_reservation(invoice_id):
    invoice = Invoice.objects.get(pk=invoice_id)
    if invoice.status != 'payed':
        invoice.status = 'canceled'
        invoice.suspended_at = timezone.now()
        invoice.save()
        sync_storage(invoice.basket_id, add)
        return 'invoice canceled, storage synced successfully'

