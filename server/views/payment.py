import json

import requests
import django_rq
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from datetime import timedelta
import operator
from server.models import Invoice, InvoiceProduct, Basket
from server.serialize import *
from server.views.utils import des_encrypt, get_basket, cancel_reservation, sync_storage

psp = {'data': [{'id': 1, 'key': 'mellat', 'name': 'ملت', 'hide': False, 'disable': True},
       {'id': 2, 'key': 'melli', 'name': 'ملی', 'hide': False, 'disable': False},
       {'id': 3, 'key': 'saman', 'name': 'سامان', 'hide': False, 'disable': False},
       {'id': 4, 'key': 'refah', 'name': 'رفاه', 'hide': True, 'disable': True},
       {'id': 5, 'key': 'pasargad', 'name': 'پاسارگاد', 'hide': True, 'disable': False}],
       'default': 2}

# allowed_ip = 0.0.0.0
merchant_id = None
terminal_id = None
terminal_key = None


class PSP(View):
    def get(self, request):
        return JsonResponse({'psp': psp})


class PaymentRequest(View):
    def post(self, request):
        basket = Basket.objects.filter(user=request.user, active=True).first()
        self.reserve_storage(basket)
        # basket = get_basket(request.user, request.lang)
        invoice = self.create_invoice(request)
        amount = invoice.amount
        datetime = timezone.now()
        return_url = HOST + '/payment_callback'
        sign_data = des_encrypt(f'{terminal_id};{invoice.pk};{amount}')  # encrypt (PKCS7,ECB(TripleDes) => base64
        additional_data = None  # json
        # Type = [Amount, Percentage]
        multiplexing_data = {'Type': 'Percentage', 'MultiplexingRows': [{'IbanNumber': 1, 'Value': 50}]}
        url = 'https://sadad.shaparak.ir/VPG/api/v0/Request/PaymentRequest'
        return JsonResponse({'token': 'test token', 'description': 'test description',
                             'redirect_url': 'https://sadad.shaparak.ir/VPG/Purchase'})

        # r = requests.post(url, data={'MerchantId': merchant_id, 'TerminalId': terminal_id, 'Amount': amount,
        #                              'OrderId': invoice_id, 'LocalDateTime': datetime, 'ReturnUrl': return_url,
        #                              'SignData': sign_data, 'AdditionalData': additional_data,
        #                              'MultiplexingData': multiplexing_data})
        # res = r.json()
        # return JsonResponse({'res_code': res['ResCode'], 'token': res['Token'], 'description': res['Description'],
        #                      'redirect_url': 'https://sadad.shaparak.ir/VPG/Purchase'})

    def create_invoice(self, request, basket=None):
        user = request.user
        address = None
        basket = basket or get_basket(user, request.lang)
        if basket['address_required']:
            address = user.default_address
        Invoice.objects.filter(basket_id=basket['basket']['id'], status='pending').delete()
        invoice = Invoice(created_by=user, updated_by=user, user=user, amount=basket['summary']['discount_price'],
                          type="unknown", address=address, tax=20, basket_id=basket['basket']['id'])
        invoice.save()
        return invoice

    def reserve_storage(self, basket):
        if not basket.sync:
            sync_storage(basket, operator.sub)
            scheduler = django_rq.get_scheduler('basket_sync')
            job = scheduler.enqueue_at(timedelta(minutes=30), cancel_reservation, basket=basket)
            basket.job = job
            basket.sync = 'reserved'
            basket.save()
            # python manage.py rqscheduler


class CallBack(View):
    def post(self, request):
        data = json.loads(request.body)
        invoice_id = data['OrderId']
        description = data['Description']
        # details = self.verify(data['token'])
        self.submit_invoice_products(invoice_id)
        try:
            updated = Invoice.objects.filter(pk=invoice_id).update(status='payed', payed_at=timezone.now())
            assert updated
        except AssertionError:
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

    def submit_invoice_products(self, invoice_id):
        invoice = Invoice.objects.filter(pk=invoice_id).select_related(*Invoice.select).first()
        basket = invoice.basket
        basket_products = BasketProduct.objects.filter(basket=basket)
        invoice_products = []
        for product in basket_products:
            storage = product.storage
            invoice_products.append(
                InvoiceProduct(product=storage.product, invoice_id=invoice_id, count=product.count, tax=storage.tax,
                               final_price=storage.final_price, discount_price=storage.discount_price))
        InvoiceProduct.objects.bulk_create(invoice_products)
