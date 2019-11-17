from django.views import View
import requests
import json
from server.models import Invoice
from django.utils import timezone
from mehr_takhfif.settings import HOST
from server.views.utils import des_encrypt
from django.http import JsonResponse, HttpResponseRedirect
from server.views.client.shopping import BasketView
from server.serialize import *

psp = [{'id': 1, 'name': 'Mellat', 'hide': False, 'disable': True},
       {'id': 2, 'name': 'Melli', 'hide': False, 'disable': False},
       {'id': 3, 'name': 'Saman', 'hide': False, 'disable': False},
       {'id': 4, 'name': 'Refah', 'hide': True, 'disable': True},
       {'id': 5, 'name': 'Pasargad', 'hide': True, 'disable': False}]

# allowed_ip = 0.0.0.0
merchant_id = None
terminal_id = None
terminal_key = None


class CheckBasket(View):
    def get(self, request):
        basket = BasketView.get_basket(request.user, request.lang)
        basket['psp'] = psp
        return JsonResponse(basket)


class PaymentRequest(View):
    def post(self, request):
        invoice_id = data['order_id']
        amount = Invoice.objects.get(pk=invoice_id).amount
        datetime = timezone.now()
        return_url = HOST + '/payment_callback'
        sign_data = des_encrypt(terminal_id+';'+invoice_id+';'+amount)  # encrypt (PKCS7,ECB(TripleDes) => base64
        additional_data = None  # json
        # Type = [Amount, Percentage]
        multiplexing_data = {'Type': 'Percentage', 'MultiplexingRows': [{'IbanNumber': 1, 'Value': 50}]}
        url = 'https://sadad.shaparak.ir/VPG/api/v0/Request/PaymentRequest'
        r = requests.post(url, data={'MerchantId': merchant_id, 'TerminalId': terminal_id, 'Amount': amount,
                                     'OrderId': invoice_id, 'LocalDateTime': datetime, 'ReturnUrl': return_url,
                                     'SignData': sign_data, 'AdditionalData': additional_data,
                                     'MultiplexingData': multiplexing_data})
        res = r.json()
        return JsonResponse({'res_code': res['ResCode'], 'token': res['Token'], 'description': res['Description'],
                             'redirect_url': 'https://sadad.shaparak.ir/VPG/Purchase'})

    def check_price(self, basket):
        invoice = Invoice()


class CallBack(View):
    def post(self, request):
        data = json.loads(request.body)
        invoice_id = data['OrderId']
        description = data['Description']
        details = self.verify(data['token'])
        try:
            updated = Invoice.objects.filter(pk=invoice_id).update(status='payed')
            assert updated
        except AssertionError:
            print('error')
        return JsonResponse(details)

    def verify(self, token):
        url = 'https://sadad.shaparak.ir/VPG/api/v0/Advice/Verify'
        sign_data = des_encrypt(token)  # encrypted token with TripleDes
        r = requests.post(url, data={'Token': token, 'SignData': sign_data})
        res = r.json()
        return {'res_code': res['ResCode'], 'amount': res['Amount'], 'description': res['Description'],
                'retrival_ref_no': res['RetrivalRefNo'], 'system_trace_no': res['SystemTraceNo'],
                'invoice_id': res['OrderId']}

