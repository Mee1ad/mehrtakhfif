from __future__ import absolute_import, unicode_literals

import logging
import random
import time
from contextlib import contextmanager
from hashlib import md5
from operator import add
from time import sleep
from urllib.error import URLError

import pdfkit
import requests
from celery import shared_task
from celery.signals import task_postrun
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult
from push_notifications.models import GCMDevice

from mehr_takhfif.settings import ARVAN_API_KEY
from mehr_takhfif.settings import INVOICE_ROOT, BASE_DIR
from server.models import Invoice, InvoiceStorage, User, PaymentHistory
from server.utils import sync_storage, send_sms, send_email, random_data, add_days, add_minutes
import re
from django_celery_beat.models import IntervalSchedule

logger = logging.getLogger(__name__)
LOCK_EXPIRE = 60 * 10  # Lock expires in 10 minutes


@contextmanager
def task_lock(lock_id, oid):
    timeout_at = time.monotonic() + LOCK_EXPIRE - 3
    # cache.add fails if the key already exists
    status = cache.add(lock_id, oid, LOCK_EXPIRE)
    try:
        yield status
    finally:
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking
        if time.monotonic() < timeout_at and status:
            # don't release the lock if we exceeded the timeout
            # to lessen the chance of releasing an expired lock
            # owned by someone else
            # also don't release the lock if we didn't acquire it
            cache.delete(lock_id)


@shared_task(bind=True, max_retries=3)
def cancel_reservation(self, invoice_id, **kwargs):
    hashcode = md5(f"cancel_reservation{invoice_id}".encode()).hexdigest()
    lock_id = '{0}-lock-{1}'.format(self.name, hashcode)
    with task_lock(lock_id, self.app.oid) as acquired:
        if acquired:
            try:
                invoice = PaymentHistory.objects.filter(invoice_id=invoice_id).order_by('-id').first().invoice
                url = f"https://bpm.shaparak.ir/pgwchannel/startpay.mellat?RefId={invoice.reference_id}"
                r = requests.get(url)
                task = invoice.sync_task
                if re.search(r'<form.*>', r.text):
                    print("ok, i`ll try it later")
                    task.description = f"{task.description} - delay for 3 minutes"
                    schedule, created = IntervalSchedule.objects.get_or_create(every=3,
                                                                               period=IntervalSchedule.MINUTES)
                    task.interval = schedule
                    task.one_off = False
                    task.save()
                    return 'waiting for ipg'

                #  ((1, 'pending'), (2, 'payed'), (3, 'canceled'), (4, 'rejected'), (5, 'sent'), (6, 'ready'))
                task.one_off = True
                task.save()
                successful_status = [2, 5]  # payed, posted
                if invoice.status not in successful_status:
                    invoice.status = 3  # canceled
                    try:
                        invoice.post_invoice.status = 3
                        invoice.post_invoice.save()
                    except Exception:
                        pass
                    invoice.cancel_at = timezone.now()
                    invoice.save()
                    # sync_storage(invoice.basket_id, add)
                    sync_storage(invoice, add)
                    # try:
                        # invoice.basket.sync = 2  # canceled
                    # except AttributeError:
                    #     pass
                    return 'invoice canceled, storage synced successfully'
                return 'successful payment, task terminated'
            except Exception as e:
                logger.exception(e)
                self.retry(countdown=3 ** self.request.retries)
    return "This task is duplicate"


@shared_task(bind=True, max_retries=3)
def sale_report(self, invoice_id, **kwargs):
    hashcode = md5(f"sale_report{invoice_id}".encode()).hexdigest()
    lock_id = '{0}-lock-{1}'.format(self.name, hashcode)
    email_list = ['accounting@mehrtakhfif.com', 'post@mehrtakhfif.com', 'support@mehrtakhfif.com']
    with task_lock(lock_id, self.app.oid) as acquired:
        if acquired:
            try:
                invoice_storages = InvoiceStorage.objects.filter(invoice_id=invoice_id). \
                    select_related('storage__product__box__owner').\
                    prefetch_related('storage__product__box__owner__gcmdevice_set')
                owners = {}
                for invoice_storage in invoice_storages:
                    owner = invoice_storage.storage.product.box.owner
                    product_data = f"{invoice_storage.count} عدد {invoice_storage.storage.title['fa']}"
                    if owner in owners:
                        owners[owner].append(product_data)
                        continue
                    owners[owner] = [product_data]
                all_products = []
                for owner, products in owners.items():
                    all_products += products
                    send_email('گزارش فروش', to=owner.email, message='\n'.join(products))
                    owner.gcmdevice_set.all().send_message("برای مشاهده جزئیات فروش وارد پنل شوید",
                                                           extra={'title': "گزارش فروش"})
                [send_email('گزارش فروش', to=mail, message='\n'.join(all_products)) for mail in email_list]
                return f"{invoice_id}-successfully reported"
            except Exception as e:
                logger.exception(e)
                self.retry(countdown=3 ** self.request.retries)
    return "This task is duplicate"


@shared_task(bind=True, max_retries=3)
def sale_report_summary(self, **kwargs):
    hashcode = md5('test'.encode()).hexdigest()
    lock_id = '{0}-lock-{1}'.format(self.name, hashcode)
    with task_lock(lock_id, self.app.oid) as acquired:
        if acquired:
            try:
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
                return {
                    'notified admins': [admin['owner'].first_name + " " + admin['owner'].last_name for admin in
                                        notify_list]}
            except Exception as e:
                logger.exception(e)
                self.retry(countdown=3 ** self.request.retries)
    return "This task is duplicate"


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


@shared_task(bind=True, max_retries=3)
def send_invoice(self, invoice_id, lang="fa", **kwargs):
    hashcode = md5('test'.encode()).hexdigest()
    lock_id = '{0}-lock-{1}'.format(self.name, hashcode)
    with task_lock(lock_id, self.app.oid) as acquired:
        if acquired:
            try:
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
                    data = {'title': storage.invoice_title[lang], 'user': f'{user.first_name} {user.last_name}',
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
                send_sms(user.username, "user-order", {invoice_id})

                email_content = f"سفارش شما با شماره {invoice_id} با موفقیت ثبت شد. برای مشاهده صورتحساب و جزئیات خرید به پنل کاربری خود مراجعه کنید \nhttps://mhrt.ir/invoice/{invoice_id}"

                send_email("صورتحساب خرید", user.email, message=email_content)
                # if sms_content:
                #     send_sms(user.username, "digital-order-details", sms_content)
                res = 'sms sent'
                if user.email and all_renders:
                    send_email("صورتحساب خرید", user.email, html_content=all_renders, attach=pdf_list)
                    res += ', email sent'
                return res
            except Exception as e:
                logger.exception(e)
                self.retry(countdown=3 ** self.request.retries)
    return "This task is duplicate"


@shared_task(bind=True, max_retries=3)
def email_task(self, to, subject, message, **kwargs):
    hashcode = md5(f"{to}{subject}{message}{timezone.now().day}".encode()).hexdigest()
    lock_id = '{0}-lock-{1}'.format(self.name, hashcode)
    with task_lock(lock_id, self.app.oid) as acquired:
        if acquired:
            try:
                send_email(subject=subject, message=message, to=to)
                return f"{to}\n{subject}\n{message}"
            except Exception as e:
                logger.exception(e)
                self.retry(countdown=3 ** self.request.retries)
    return "This task is duplicate"


def get_snapshots(self, name=None):
    images = requests.get(self.url + f'/regions/{self.region}/images?type=server', headers=self.headers).json()
    if name:
        return [image for image in images['data'] if name == image['abrak'].split('_', 1)[0]]
    return images['data']


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


@shared_task(bind=True)
def test_task(self, *args, **kwargs):

    return f"{self}{args}{kwargs}"
