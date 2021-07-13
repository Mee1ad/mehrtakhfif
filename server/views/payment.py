import json
import operator
import urllib.parse as urlparse
from urllib.parse import parse_qs

import zeep
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django_celery_beat.models import IntervalSchedule

from mehr_takhfif.settings import DEBUG, CLIENT_HOST
from server.serialize import *
from server.tasks import cancel_reservation
from server.utils import LoginRequired, get_basket, add_one_off_job, sync_storage, add_minutes, get_share,\
    add_to_basket, set_custom_signed_cookie
import pysnooper

ipg = {'data': [{'id': 1, 'key': 'mellat', 'name': 'ملت', 'hide': False, 'disable': False},
                {'id': 2, 'key': 'melli', 'name': 'ملی', 'hide': True, 'disable': True},
                {'id': 3, 'key': 'saman', 'name': 'سامان', 'hide': True, 'disable': True},
                {'id': 4, 'key': 'refah', 'name': 'رفاه', 'hide': True, 'disable': True},
                {'id': 5, 'key': 'pasargad', 'name': 'پاسارگاد', 'hide': True, 'disable': True}],
       'default': 1}

# allowed_ip = 0.0.0.0
# behpardakht
bp = {'terminal_id': 5290645, 'username': "takh252", 'password': "71564848",
      'ipg_url': "https://bpm.shaparak.ir/pgwchannel/startpay.mellat",
      'callback': 'https://api.mehrtakhfif.com/payment/callback'}  # mellat

deposit = {'charity': 5000, 'dev': 2}

if not DEBUG:
    client = zeep.Client(wsdl="https://bpm.shaparak.ir/pgwchannel/services/pgw?wsdl")

saddad = {'merchant_id': None, 'terminal_id': None, 'terminal_key': None,
          'payment_request': 'https://sadad.shaparak.ir/VPG/api/v0/Request/PaymentRequest',
          'redirect_url': 'https://sadad.shaparak.ir/VPG/Purchase'}  # mellat

pecco = {'pin': '4MuVGr1FaB6P7S43Ggh5', 'terminal_id': '44481453',
         'payment_request': 'https://pec.shaparak.ir/NewIPGServices/Sale/SaleService.asmx'}  # parsian

callback = HOST + "/callback"


# todo clear basket after payment
class IPG(View):
    def get(self, request):
        return JsonResponse({'ipg': ipg})


class PaymentRequest(LoginRequired):
    def get(self, request, basket_id):
        # ip = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR')

        # debug
        # if not request.user.is_staff:
        #     raise ValidationError(_('متاسفانه در حال حاضر امکان خرید وجود ندارد'))
        # if request.user.is_staff:
        basket = Basket.objects.filter(user=request.user, id=basket_id).first()
        if basket.count < 1:
            return JsonResponse({"message": "سبد خرید خالی است", "variant": "error"})
        permitted_user = [1]
        # if basket.sync in [2, 3]:  # [(0, 'ready'), (1, 'reserved'), (2, 'canceled'), (3, 'done')]
        #     raise ValidationError(_('سبد خرید باید فعال باشد'))

        if DEBUG and request.user.pk in permitted_user:
            from server.tasks import send_invoice
            # if DEBUG:
            invoice = self.create_invoice(request)
            self.reserve_storage(basket, invoice)
            self.submit_invoice_storages(request, invoice.pk)
            # invoice.basket.sync = 3
            # invoice.basket.save()
            invoice.status = 2
            invoice.payed_at = timezone.now()
            invoice.card_holder = '012345******6789'
            invoice.final_amount = invoice.amount
            invoice.save()
            # invoice.basket.status = 3  # done
            invoice.basket.discount_code.update(invoice=invoice)
            url = self.get_payment_url(invoice)
            # invoice.basket.save()
            # CallBack.notification_admin(invoice)
            # return JsonResponse({'invoice_id': invoice.id})
            # return HttpResponseRedirect(f"http://mt.com:3002/invoice/{invoice.id}")
            send_invoice(invoice.id, lang="fa")
            basket.products.clear()
            return JsonResponse({'url': f"{CLIENT_HOST}/invoice/{invoice.id}"})

        user = request.user
        if not Basket.objects.filter(pk=basket_id, user=user).exists():
            raise ValidationError(_('سبد خرید نامعتبر است'))
        # check for disabling in 15 minutes
        if user.first_name is None or user.last_name is None or user.meli_code is None or user.username is None:
            raise ValidationError(_('لطفا قبل از خرید پروفایل خود را تکمیل نمایید'))
        invoice = self.create_invoice(request)
        self.submit_invoice_storages(request, invoice.pk)
        self.reserve_storage(basket, invoice)
        url = self.get_payment_url(invoice)
        basket.products.clear()
        res = JsonResponse({"url": url})
        return set_custom_signed_cookie(res, 'basket_count', 0)

    @staticmethod
    def behpardakht_api(invoice_id, invoice=None, retried_times=10, charity_id=1, booking=False):
        # charity_deposit = Charity.objects.get(pk=charity_id).deposit_id
        if invoice is None:
            invoice = Invoice.objects.filter(pk=invoice_id).prefetch_related('storages').select_related(
                'post_invoice').first()
        share = get_share(invoice=invoice)
        shipping_cost = getattr(getattr(invoice, 'post_invoice', None), 'amount', 0)
        print(share['mt_profit'], share['tax'], shipping_cost, share['admin'], share['charity'], share['dev'])
        additional_data = [[1, (share['mt_profit'] + share['tax'] + shipping_cost + share['admin']) * 10, 0],
                           [deposit['charity'], share['charity'] * 10, 0],
                           [deposit['dev'], share['dev'] * 10, 0]]
        # invoice = Invoice.objects.get(pk=invoice_id)
        # if not booking:
        # basket = get_basket(request, basket=invoice.basket, return_obj=True, tax=True)
        # tax = basket.summary["tax"]
        # charity = basket.summary["charity"]
        # additional_data = [[1, int(basket.summary["mt_profit"] + basket.summary["charity"] + tax +
        #                            basket.summary['shipping_cost'] - charity) * 10, 0],
        #                    [deposit['charity'], charity * 10, 0]]
        # bug '1,49000,0;1,16000,0'
        # todo add feature price
        suppliers_invoice = InvoiceSuppliers.objects.filter(invoice_id=invoice_id)
        for supplier_invoice in suppliers_invoice:
            try:
                supplier = supplier_invoice.supplier
            except AttributeError:
                continue
            for data in additional_data:
                if supplier.deposit_id == data[0]:
                    data[1] += supplier_invoice.amount * 10
                    break
            else:
                additional_data.append([supplier.deposit_id, supplier_invoice.amount * 10, 0])
        # for basket_product in basket.basket_products:
        #     try:
        #         supplier = basket_product.supplier
        #     except AttributeError:
        #         continue
        #     for data in additional_data:
        #         if supplier.deposit_id == data[0]:
        #             data[1] += basket_product.start_price * 10
        #             break
        #     else:
        #         additional_data.append([supplier.deposit_id, basket_product.start_price * 10, 0])
        print(additional_data)
        additional_data = [item for item in additional_data if item[1] > 0]
        additional_data = ';'.join(','.join(str(x) for x in b) for b in additional_data)

        local_date = timezone.now().strftime("%Y%m%d")
        # DEBUG:
        # invoice.amount = 1000
        # additional_data = '1,5000,0;2,5000,0'
        local_time = pytz.timezone("Iran").localize(datetime.datetime.now()).strftime("%H%M%S")
        r = "0,123456789"
        if not DEBUG:
            print("order id", f"{retried_times}{invoice.id}")
            r = client.service.bpCumulativeDynamicPayRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                                             userPassword=bp['password'], localTime=local_time,
                                                             localDate=local_date, callBackUrl=bp['callback'],
                                                             orderId=f"{retried_times}{invoice.id}",
                                                             amount=(invoice.amount + shipping_cost) * 10,
                                                             additionalData=additional_data)
        if r[0:2] == "0,":
            ref_id = r[2:]
            invoice.reference_id = ref_id
            invoice.save()
            return f"{bp['ipg_url']}?RefId={ref_id}"
        else:
            print(additional_data)
            raise ValueError(_(f"can not get ipg page: {r}"))

    @staticmethod
    def get_payment_url(invoice):
        url = PaymentRequest.behpardakht_api(invoice_id=invoice.pk, retried_times=getattr(invoice, 'retried_times', 10))
        parsed = urlparse.urlparse(url)
        ref_id = parse_qs(parsed.query)['RefId'][0]
        if timezone.now() > add_minutes(-15, invoice.expire):
            print('invoice task extended')
            task = invoice.sync_task
            task.enabled = False
            task.save()
            task.description = f"retried {invoice.retried_times[1:]} times"
            schedule, created = IntervalSchedule.objects.get_or_create(every=16, period=IntervalSchedule.MINUTES)
            task.interval = schedule
            task.enabled = True
            task.save()
            invoice.expire = add_minutes(16)
            invoice.reference_id = ref_id
            invoice.save()
        PaymentHistory.objects.create(reference_id=ref_id, amount=invoice.amount, invoice=invoice,
                                      description="پرداخت توسط درگاه پرداخت")
        return url

    def postpone_invoice(self, invoice):
        invoice.expire = add_minutes(30)
        task_name = f'{invoice.id}: cancel reservation'
        # args = []
        kwargs = {"invoice_id": invoice.id, "task_name": task_name}
        schedule, created = IntervalSchedule.objects.get_or_create(every=30, period=IntervalSchedule.MINUTES)
        task, created = PeriodicTask.objects.get_or_create(interval=schedule, name=task_name, kwargs=json.dumps(kwargs),
                                                           task='server.tasks.cancel_reservation', one_off=True)
        task.save()

    def create_invoice(self, request, basket=None, charity_id=1):
        user = request.user
        address = None
        basket = basket or get_basket(request, require_profit=True, with_changes=True)
        # todo if changes
        if basket['address_required']:
            if user.default_address.state_id not in [8, 25]:
                raise ValidationError('در حال حاضر محصولات فقط در گیلان قابل ارسال میباشد')
            address = AddressSchema().dump(user.default_address)
            basket['summary']['total_price'] -= basket['summary']['shipping_cost']
            basket['summary']['discount_price'] -= basket['summary']['shipping_cost']
            if basket['summary']['shipping_cost'] < 0:
                raise ValidationError('لطفا آدرس خود را در پروفایل ثبت کنید')
        max_shipping_time = 0
        for product in basket['basket']['products']:
            if max_shipping_time < product['product']['default_storage']['max_shipping_time']:
                max_shipping_time = product['product']['default_storage']['max_shipping_time']
        post_invoice = None
        shipping_cost = basket['summary']['shipping_cost']
        if shipping_cost:
            post_invoice = Invoice.objects.create(created_by=user, updated_by=user, user=user, address=address,
                                                  amount=shipping_cost,
                                                  basket_id=basket['basket']['id'])
        invoice = Invoice.objects.create(created_by=user, updated_by=user, user=user, charity_id=charity_id,
                                         # mt_profit=basket['summary']['mt_profit'],
                                         basket_id=basket['basket']['id'],
                                         invoice_discount=basket['summary']['invoice_discount'], address=address,
                                         # charity=basket['summary']['charity'],
                                         amount=basket['summary']['discount_price'] + basket['summary']['tax'],
                                         final_price=basket['summary']['total_price'],
                                         max_shipping_time=max_shipping_time, post_invoice=post_invoice)
        return invoice

    def reserve_storage(self, basket, invoice):
        # if basket.sync != 1:  # [(0, 'ready'), (1, 'reserved'), (2, 'canceled'), (3, 'done')]
        sync_storage(basket, operator.sub)
        # task_name = f'{invoice.id}: cancel reservation'
        # # args = []
        # kwargs = {"invoice_id": invoice.id, "task_name": task_name}
        # invoice.sync_task = add_one_off_job(name=task_name, kwargs=kwargs, interval=30,
        #                                     task='server.tasks.cancel_reservation')
        # basket.active = False
        # basket.sync = 1  # reserved
        # basket.save()
        # invoice.save()

    def submit_invoice_storages(self, request, invoice_id):
        invoice = Invoice.objects.filter(pk=invoice_id).select_related(*Invoice.select).first()
        basket = get_basket(request, basket=invoice.basket, return_obj=True)
        invoice_products = []
        for product in basket.basket_products:
            storage = product.storage
            supplier = storage.supplier
            amount = product.start_price
            if not InvoiceSuppliers.objects.filter(invoice=invoice, supplier=supplier).update(
                    amount=F('amount') + amount):
                InvoiceSuppliers.objects.create(invoice=invoice, supplier=supplier, amount=amount)
            # tax = get_tax(storage.tax_type, storage.discount_price, storage.start_price)
            # charity = round(storage.discount_price * 0.005)
            # dev = round((storage.discount_price - storage.start_price - tax) * 0.069)
            # admin = round((storage.discount_price - storage.start_price - tax - charity - dev) *
            #               storage.product.box.share)
            # mt_profit = storage.discount_price - storage.start_price - tax - charity - dev - admin
            storage.count = product.count
            storage.storage = storage
            share = get_share(storage)
            invoice_products.append(
                InvoiceStorage(storage=storage, invoice_id=invoice_id, count=product.count, tax=share['tax'],
                               final_price=(storage.final_price - share['tax']) * product.count, box=product.box,
                               discount_price=storage.discount_price * product.count, charity=share['charity'],
                               start_price=storage.start_price * product.count, admin=share['admin'],
                               features=product.features, mt_profit=share['mt_profit'],
                               total_price=(storage.final_price - share['tax']) * product.count, dev=share['dev'],
                               discount_price_without_tax=(storage.discount_price - share['tax']) * product.count,
                               discount=(storage.final_price - storage.discount_price) * product.count,
                               created_by=invoice.user, updated_by=invoice.user))
        InvoiceStorage.objects.bulk_create(invoice_products)


class RePayInvoice(LoginRequired):
    def get(self, request, invoice_id):
        # invoices = Invoice.objects.select_for_update().filter(pk=invoice_id)
        # with transaction.atomic():
        #     old_invoice = invoices.first()
        #     old_invoice.status = 3  # canceled
        #     old_invoice.post_invoice.status = 3
        #     old_invoice.post_invoice.save()
        #     old_invoice.cancel_at = timezone.now()
        #     old_invoice.save()
        # CallBack.finish_invoice_jobs(old_invoice, cancel=True)
        # new_invoice = old_invoice
        # new_post_invoice = old_invoice.post_invoice
        # new_post_invoice.__dict__.update({"pk": None, "expire": add_minutes(30), "status": 1})
        # new_invoice.__dict__.update({"pk": None, "reference_id": None, "expire": add_minutes(30), "status": 1})
        invoice = Invoice.objects.filter(pk=invoice_id, status=1).annotate(
            retried_times=Count('histories') + 10).first()
        url = PaymentRequest.get_payment_url(invoice)
        return JsonResponse({"url": url})


class EditInvoice(LoginRequired):
    def patch(self, request, invoice_id):
        products = InvoiceStorage.objects.filter(invoice_id=invoice_id, invoice__user=request.user, invoice__status=1,
                                                 invoice__expire__gt=timezone.now()).select_related('invoice__basket')\
            .only('invoice__basket', 'storage_id', 'count')
        basket = products[0].invoice.basket
        products = list(products.values('storage_id', 'count'))
        cancel_reservation(invoice_id, force=True)
        basket_count = add_to_basket(basket, products)
        res = JsonResponse({"message": "محصولات خریداری شده برای ایجاد تغییرات به سبد خرید افزوده شدند",
                            "variant": "success"})
        return set_custom_signed_cookie(res, 'basket_count', basket_count)


class CallBack(View):
    # todo dor debug
    def get(self, request):
        return HttpResponseRedirect(f"{CLIENT_HOST}/profile/all-order")

    def post(self, request):
        # todo redirect to site anyway
        data = request.body.decode().split('&')
        data_dict = {}
        for param in data:
            val = param.split('=')
            data_dict[val[0]] = val[1]
        invoice_id = data_dict['SaleOrderId'][2:]  # data_dict['SaleOrderId'][:2] = retried times
        invoice = PaymentHistory.objects.get(invoice_id=invoice_id, reference_id=data_dict['RefId']).invoice
        if invoice.status in [3, 4]:
            return HttpResponseRedirect(f"{CLIENT_HOST}/invoice/{invoice_id}?error=true")
        invoice.sale_reference_id = data_dict.get('SaleReferenceId', None)
        invoice.sale_order_id = data_dict['SaleOrderId']
        invoice.ipg_res_code = data_dict['ResCode']
        if not invoice.sale_reference_id or not self.verify(invoice.sale_order_id, invoice.sale_reference_id):
            # self.finish_invoice_jobs(invoice, cancel=True)
            # invoice.status = 1
            invoice.save()
            # EditInvoice.restore_products(invoice)
            return HttpResponseRedirect(f'{CLIENT_HOST}/basket')
        # todo https://memoryleaks.ir/unlimited-charge-of-mytehran-account/
        invoice.status = 2
        try:
            invoice.post_invoice.status = 2
            invoice.post_invoice.save()
        except Exception:
            pass
        Invoice.objects.filter(pk=invoice.post_invoice_id).update(status=2)
        invoice.payed_at = timezone.now()
        invoice.card_holder = data_dict['CardHolderPan']
        invoice.final_amount = data_dict['FinalAmount']
        task_name = f'{invoice.id}: send invoice'
        kwargs = {"invoice_id": invoice.pk, "lang": request.lang, 'name': task_name}
        invoice.email_task = add_one_off_job(name=task_name, kwargs=kwargs, interval=0,
                                             task='server.tasks.send_invoice')
        invoice.save()
        self.finish_invoice_jobs(invoice, finish=True)
        self.notification_admin(invoice)
        return HttpResponseRedirect(f"{CLIENT_HOST}/invoice/{invoice_id}")

    @staticmethod
    def finish_invoice_jobs(invoice, cancel=None, finish=None):
        task_name = f'{invoice.id}: cancel reservation'
        description = f'{timezone.now()}: unknown reason'
        if finish:  # successful payment, cancel task
            # invoice.basket.status = 3  # done
            description = f'{timezone.now()}: successful payment'
            invoice.basket.discount_code.update(invoice=invoice)
            # invoice.basket.save()
            # Basket.objects.create(user=invoice.user, created_by=invoice.user, updated_by=invoice.user)
        elif cancel:
            description = f'{timezone.now()}: reserve canceled'
            cancel_reservation(invoice.pk)
        PeriodicTask.objects.filter(name=task_name).update(enabled=False, description=description)

    @staticmethod
    def notification_admin(invoice):
        kwargs = {"invoice_id": invoice.pk}
        invoice.sync_task = add_one_off_job(name=f"sales report - {invoice.pk}", kwargs=kwargs, interval=0,
                                            task='server.tasks.sale_report')

    def verify(self, sale_order_id, sale_ref_id):
        r = client.service.bpVerifyRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                           userPassword=bp['password'], orderId=sale_order_id,
                                           saleOrderId=sale_order_id, saleReferenceId=sale_ref_id)
        if r == '0':
            return True
        print(f'{sale_order_id}-bpVerifyRequest response:', r)
        time.sleep(1)
        r = client.service.bpVerifyRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                           userPassword=bp['password'], orderId=sale_order_id,
                                           saleOrderId=sale_order_id, saleReferenceId=sale_ref_id)
        if r == '0':
            return True
        print(f'{sale_order_id}-bpVerifyRequest2 response:', r)
        time.sleep(1)
        r = client.service.bpInquiryRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                            userPassword=bp['password'], orderId=10434,
                                            saleOrderId=10434, saleReferenceId="184589975811")
        print(f'{sale_order_id}-bpInquiryRequest response:', r)
        r = client.service.bpSettleRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                           userPassword=bp['password'], orderId=sale_order_id,
                                           saleOrderId=sale_order_id, saleReferenceId=sale_ref_id)
        time.sleep(1)
        if r == '0':
            return True
        print(f'{sale_order_id}-bpSettleRequest response:', r)
        return False
