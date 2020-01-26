import json
import pysnooper
import requests
import django_rq
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from datetime import timedelta
import operator
from server.models import Invoice, InvoiceStorage, Basket
from django_celery_beat.models import PeriodicTask
from server.serialize import *
from server.views.utils import des_encrypt, get_basket, add_one_off_job, sync_storage

ipg = {'data': [{'id': 1, 'key': 'mellat', 'name': 'ملت', 'hide': False, 'disable': True},
                {'id': 2, 'key': 'melli', 'name': 'ملی', 'hide': False, 'disable': False},
                {'id': 3, 'key': 'saman', 'name': 'سامان', 'hide': False, 'disable': False},
                {'id': 4, 'key': 'refah', 'name': 'رفاه', 'hide': True, 'disable': True},
                {'id': 5, 'key': 'pasargad', 'name': 'پاسارگاد', 'hide': True, 'disable': False}],
       'default': 2}

# allowed_ip = 0.0.0.0
saddad = {'merchant_id': None, 'terminal_id': None, 'terminal_key': None,
          'payment_request': 'https://sadad.shaparak.ir/VPG/api/v0/Request/PaymentRequest',
          'redirect_url': 'https://sadad.shaparak.ir/VPG/Purchase'}  # mellat

pecco = {'pin': '4MuVGr1FaB6P7S43Ggh5', 'terminal_id': '44481453',
         'payment_request': 'https://pec.shaparak.ir/NewIPGServices/Sale/SaleService.asmx'}  # parsian


class IPG(View):
    def get(self, request):
        return JsonResponse({'ipg': ipg})


class PaymentRequest(View):
    def get(self, request, basket_id):
        user = request.user
        assert Basket.objects.filter(pk=basket_id, user=user).exists()
        invoice = Invoice.objects.filter(user=user, basket_id=basket_id)
        if not invoice.exists():
            basket = Basket.objects.filter(user=request.user, active=True).first()
            invoice = self.create_invoice(request)
            self.reserve_storage(basket, invoice)
        else:
            invoice = invoice.first()
            assert invoice.status == 'pending'
            invoice.status = 'canceled'
            invoice.task.enabled = False
            invoice.task.description = 'Canceled by system'
            invoice.task.save()
            new_invoice = self.create_invoice(request)
            self.reserve_storage(invoice.basket, new_invoice)

        amount = invoice.amount
        datetime = timezone.now()
        return_url = HOST + '/payment_callback'
        self.ipg_api()
        return JsonResponse({})

    def ipg_api(self):
        # encrypt (PKCS7,ECB(TripleDes) => base64
        # sign_data = des_encrypt(f'{saddad["terminal_id"]};{invoice.pk};{amount}')
        additional_data = None  # json
        # Type = [Amount, Percentage]
        # multiplexing_data = {'Type': 'Percentage', 'MultiplexingRows': [{'IbanNumber': 1, 'Value': 50}]}
        # return JsonResponse({'token': 'test token', 'description': 'test description',
        #                      'redirect_url': })

        # r = requests.post(url, data={'MerchantId': merchant_id, 'TerminalId': terminal_id, 'Amount': amount,
        #                              'OrderId': invoice_id, 'LocalDateTime': datetime, 'ReturnUrl': return_url,
        #                              'SignData': sign_data, 'AdditionalData': additional_data,
        #                              'MultiplexingData': multiplexing_data})
        # res = r.json()
        # return JsonResponse({'res_code': res['ResCode'], 'token': res['Token'], 'description': res['Description'],
        #                      'redirect_url': 'https://sadad.shaparak.ir/VPG/Purchase'})

        # url = pecco['payment_request']
        # request_data = {'LoginAccount': pecco['pin'], 'Amount': amount, 'OrderId': invoice.id,
        #                 'CallBackUrl': 'http://localhost/callback', 'AdditionalData': None}
        # r = requests.post(url=pecco['payment_request'], data=request_data)
        # print(r.status_code)
        # print(r.content)

    def create_invoice(self, request, basket=None):
        user = request.user
        address = None
        basket = basket or get_basket(user, request.lang)
        if basket['address_required']:
            address = user.default_address

        invoice = Invoice(created_by=user, updated_by=user, user=user, amount=basket['summary']['discount_price'],
                          type="unknown", address=address, tax=5, basket_id=basket['basket']['id'],
                          final_price=basket['summary']['total_price'])
        invoice.save()
        return invoice

    def reserve_storage(self, basket, invoice):
        if basket.sync == 'false':
            sync_storage(basket, operator.sub)
            task_name = f'{invoice.id}: cancel reservation'
            # args = []
            kwargs = {"invoice_id": invoice.id, "task_name": task_name}
            invoice.task = add_one_off_job(name=task_name, kwargs=kwargs, interval=5,
                                           task='server.tasks.cancel_reservation')
            basket.active = False
            basket.sync = 'reserved'
            basket.save()


class CallBack(View):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        invoice_id = data['OrderId']
        description = data['Description']
        # details = self.verify(data['token'])
        self.submit_invoice_storages(invoice_id)
        try:
            invoice = Invoice.objects.get(pk=invoice_id)
            invoice.status = 'payed'
            invoice.payed_at = timezone.now()
            invoice.basket.sync = 'done'
            invoice.basket.save()
            invoice.save()
        except Exception as e:
            print(e)
            print('error')
        return JsonResponse({})

    def verify(self, token):
        url = 'https://sadad.shaparak.ir/VPG/api/v0/Advice/Verify'
        sign_data = des_encrypt(token)  # encrypted token with TripleDes
        r = requests.post(url, data={'Token': token, 'SignData': sign_data})
        res = r.json()
        return {'res_code': res['ResCode'], 'amount': res['Amount'], 'description': res['Description'],
                'retrival_ref_no': res['RetrivalRefNo'], 'system_trace_no': res['SystemTraceNo'],
                'invoice_id': res['OrderId']}

    def submit_invoice_storages(self, invoice_id):
        invoice = Invoice.objects.filter(pk=invoice_id).select_related(*Invoice.select).first()
        basket = invoice.basket
        basket_products = BasketProduct.objects.filter(basket=basket)
        invoice_products = []
        for product in basket_products:
            storage = product.storage
            invoice_products.append(
                InvoiceStorage(storage=storage, invoice_id=invoice_id, count=product.count, tax=storage.tax,
                               final_price=storage.final_price, discount_price=storage.discount_price,
                               discount_percent=storage.discount_percent, vip_discount_price=storage.vip_discount_price,
                               vip_discount_percent=storage.vip_discount_percent))
        task_name = f'{invoice.id}: cancel reservation'
        description = f'{timezone.now()}: canceled by system'
        PeriodicTask.objects.filter(name=task_name).update(enabled=False, description=description)
        InvoiceStorage.objects.bulk_create(invoice_products)
