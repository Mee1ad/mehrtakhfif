from __future__ import absolute_import, unicode_literals

import random
from operator import add
from time import sleep

import pdfkit
import requests
from celery import shared_task
from celery.signals import task_postrun
from django.template.loader import render_to_string
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult
from push_notifications.models import GCMDevice

from mehr_takhfif.settings import ARVAN_API_KEY
from mehr_takhfif.settings import INVOICE_ROOT, SHORTLINK, BASE_DIR
from server.models import Invoice, InvoiceStorage, User
from server.utils import sync_storage, send_sms, send_email, random_data, add_days
from urllib.error import URLError


@shared_task
def cancel_reservation(invoice_id, **kwargs):
    invoice = Invoice.objects.get(pk=invoice_id)
    successful_status = [2, 5]  # payed, posted
    if invoice.status not in successful_status:
        invoice.status = 3  # canceled
        try:
            invoice.post_invoice.status = 3
            invoice.post_invoice.save()
        except Exception:
            pass
        invoice.suspended_at = timezone.now()
        invoice.save()
        sync_storage(invoice.basket_id, add)
        invoice.basket.sync = 2  # canceled
        return 'invoice canceled, storage synced successfully'


@shared_task
def sale_report(invoice_id, **kwargs):
    invoice_storages = InvoiceStorage.objects.filter(invoice_id=invoice_id)
    notif_users = User.objects.filter(groups__name__in=['accountants', 'post'])
    notif_devices = GCMDevice.objects.filter(user__in=notif_users)
    for invoice_storage in invoice_storages:
        owner = invoice_storage.storage.product.box.owner
        message = f"""عنوان محصول:
                      {invoice_storage.storage.title['fa']}
                      تعداد:{invoice_storage.count}
                     قیمت: {invoice_storage.storage.discount_price}"""
        notif_users |= User.objects.filter(pk=owner.pk)
        devices = GCMDevice.objects.filter(user=owner)
        for device in devices | notif_devices:
            try:
                device.send_message(message, extra={'title': "گزارش فروش"})
            except URLError:
                continue
        [send_email('گزارش فروش', user.email, message=message) for user in notif_users]
    return f"{invoice_id}-successfully reported"


@shared_task
def sale_report_summary(**kwargs):
    yesterday = add_days(-1)
    invoices = Invoice.objects.filter(payed_at__gt=yesterday)
    notify_list = []
    for invoice in invoices:
        invoice_storages = InvoiceStorage.objects.filter(invoice=invoice)
        for invoice_storage in invoice_storages:
            owner = invoice_storage.storage.product.box.owner
            duplicate_data = [item for item in notify_list if item['owner'] == owner]
            if not duplicate_data:
                notify_list.append({'owner': owner, 'count': invoice_storage.count})
                continue
            duplicate_data[0]['count'] += invoice_storage.count
    for item in notify_list:
        send_sms(item['owner'].username, "order-summary", item['count'])
    superusers = [User.objects.get(pk=1)]
    item_count = sum([item['count'] for item in notify_list])
    if notify_list:
        [send_sms(user.username, "order-summary", item_count) for user in superusers]
    return {'notified admins': [admin['owner'].first_name + " " + admin['owner'].last_name for admin in notify_list]}


@task_postrun.connect
def task_postrun_handler(task_id=None, **kwargs):
    args = kwargs.get('kwargs', None)
    if args:
        task_result = TaskResult.objects.filter(task_id=task_id).first()
        try:
            task_name = args['name']
            description = f'{task_result.date_done}:, {task_result.result}, {task_result.traceback or ""}'
            PeriodicTask.objects.filter(name=task_name).update(description=description)
            return f'Return {task_id}'
        except KeyError:
            return 'no response'


@shared_task
def send_invoice(invoice_id, lang, **kwargs):
    products = InvoiceStorage.objects.filter(invoice_id=invoice_id)
    digital_products = products.filter(storage__product__type=1)
    user = Invoice.objects.get(pk=invoice_id).user
    pdf_list = []
    all_renders = ""
    # sms_content = ""
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
            discount_code.invoice_storage = product
            discount_code.save()
            data['code'] = discount_code.code
            rendered += render_to_string('invoice.html', data)
        pdf = INVOICE_ROOT + f'/{filename}.pdf'
        css = BASE_DIR + '/templates/css/pdf_style.css'
        pdfkit.from_string(rendered, pdf, css=css)
        pdf_list.append(pdf)
        all_renders += rendered
        # sms_content += f'\n{storage.invoice_title[lang]}\n{SHORTLINK}/{product.key}'
    send_sms(user.username, "user-order", f"Mt-{invoice_id}")
    email_content = """سفارش شما با شماره %token با موفقیت ثبت شد برای مشاهده صورتحساب و جزئیات خرید به پنل کاربری خود مراجعه کنید
                    mhrt.ir/invoice/%token"""
    send_email("صورتحساب خرید", user.email, message=email_content)
    # if sms_content:
    #     send_sms(user.username, "digital-order-details", sms_content)
    res = 'sms sent'
    if user.email and all_renders:
        send_email("صورتحساب خرید", user.email, html_content=all_renders, attach=pdf_list)
        res += ', email sent'
    return res


def get_snapshots(self, name=None):
    images = requests.get(self.url + f'/regions/{self.region}/images?type=server', headers=self.headers).json()
    if name:
        return [image for image in images['data'] if name == image['abrak'].split('_', 1)[0]]
    return images['data']


# todo make a task in db
@shared_task
def server_backup():
    url = "https://napi.arvancloud.com/ecc/v1"
    region = "ir-thr-at1"
    headers = {'Authorization': ARVAN_API_KEY}

    servers = requests.get(url + f'/regions/{region}/servers', headers=headers).json()
    for server in servers['data']:
        data = {'name': server['name']}
        new_snapshot = requests.post(url + f'/regions/{region}/servers/{server["id"]}/snapshot',
                                     headers=headers, data=data)
        if new_snapshot.status_code == 202:
            images = get_snapshots(server['name'])
            while images[0]['status'] != 'active':
                sleep(5)
                images = get_snapshots(server['name'])
            last_item = -1
            while len(images) > 2:
                if requests.delete(url + f'/regions/{region}/images/{images[last_item]["id"]}',
                                   headers=headers).status_code == 200:
                    images = get_snapshots(server['name'])
                    continue
                if last_item == -1:
                    last_item = -2
                    continue
                break
    return 'backup synced'


@shared_task
def test(**kwargs):
    return "test"
