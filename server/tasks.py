from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.signals import task_postrun
from server.models import Invoice
from operator import add
from server.utils import sync_storage, send_sms, send_email, random_data
from django.utils import timezone
from server.models import InvoiceStorage
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult
import random
from mehr_takhfif.settings import INVOICE_ROOT, STATIC_ROOT, SHORTLINK
import pdfkit
from django.template.loader import render_to_string
import pysnooper


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
    args = kwargs.get('kwargs', None)
    if args:
        task_result = TaskResult.objects.filter(task_id=task_id).first()
        task_name = args['task_name']
        description = f'{task_result.date_done}:, {task_result.result}, {task_result.traceback or ""}'
        PeriodicTask.objects.filter(name=task_name).update(description=description)
        return f'Return {task_id}'


@shared_task
def send_invoice(invoice_id, lang, **kwargs):
    digital_products = InvoiceStorage.objects.filter(invoice_id=invoice_id, storage__product__type=1)
    user = digital_products.first().invoice.user
    pdf_list = []
    all_renders = ""
    sms_content = "محصولات دیجیتال خریداری شده از مهرتخفیف:"
    for product in digital_products:
        storage = product.storage
        filename = f'{storage.product.permalink}-{product.pk}'
        product.filename = filename
        while product.key is None:
            key = ''.join(random.sample(random_data, 6))
            product.key = key
            try:
                product.save()
            except Exception:
                product.refresh_from_db()
        data = {'title': storage.invoice_title[lang], 'user': user.first_name + user.last_name,
                'price': storage.discount_price}
        if storage.product.invoice_description[lang]:
            data['product_description'] = storage.product.invoice_description[lang]
        if storage.invoice_description[lang]:
            data['storage_description'] = storage.invoice_description[lang]
        rendered = ""
        for c in range(product.count):
            discount_code = storage.discount_code.filter(invoice=None).first()
            discount_code.invoice_id = invoice_id
            discount_code.save()
            data['code'] = discount_code.code
            rendered += render_to_string('invoice.html', data)
        pdf = INVOICE_ROOT + f'/{filename}.pdf'
        css = STATIC_ROOT + 'css/pdf_style.css'
        pdfkit.from_string(rendered, pdf, css=css)
        pdf_list.append(pdf)
        all_renders += rendered
        sms_content += f'\n{storage.invoice_title[lang]}\n{SHORTLINK}/{key}'
    sms = f"سفارش شما با شماره Mt-{invoice_id} با موفقیت ثبت شد برای مشاهده صورتحساب و جزئیات خرید به پنل کاربری مراجعه کنید" \
          f"\nhttps://mehrtakhfif.com/invoice/{product.invoice_id}"
    # send_sms(invoice.user.username, content=sms)
    # send_sms(invoice.user.username, content=sms_content)
    res = 'sms sent'
    if user.email:
        send_email("صورتحساب خرید", user.email, html_content=all_renders, attach=pdf_list)
        res += ', email sent'
    return res
