from django.views import View
import requests
import json
from server.models import Invoice
from django.utils import timezone
from mehr_takhfif.settings import HOST
from server.views.utils import des_encrypt

# allowed_ip = 0.0.0.0
merchant_id = None
terminal_id = None
terminal_key = None

payment_url = 'https://sadad.shaparak.ir/VPG/Purchase'


class PaymentRequest(View):
    def post(self, request):
        data = json.loads(request.body)
        order_id = data['order_id']
        amount = Invoice.objects.get(pk=order_id).amount
        datetime = timezone.now()
        return_url = HOST + '/payment_callback'
        sign_data = des_encrypt(terminal_id+';'+order_id+';'+amount)  # encrypt (PKCS7,ECB(TripleDes) => base64
        additional_data = None  # json
        # Type = [Amount, Percentage]
        multiplexing_data = {'Type': 'Percentage', 'MultiplexingRows': [{'IbanNumber': 1, 'Value': 50}]}
        url = 'https://sadad.shaparak.ir/VPG/api/v0/Request/PaymentRequest'
        r = requests.post(url, data={'MerchantId': merchant_id, 'TerminalId': terminal_id, 'Amount': amount,
                                     'OrderId': order_id, 'LocalDateTime': datetime, 'ReturnUrl': return_url,
                                     'SignData': sign_data, 'AdditionalData': additional_data,
                                     'MultiplexingData': multiplexing_data})
        res = r.json()
        res_code = res['ResCode']
        token = res['Token']
        description = res['Description']
        redirect_url = 'https://sadad.shaparak.ir/VPG/Purchase'


class CallBack(View):
    def post(self, request):

        data = json.loads(request.body)
        invoice_id = data['OrderId']
        token = data['Token']
        description = data['Description']


    def verify(self):
        def post(self, request):
            url = 'https://sadad.shaparak.ir/VPG/api/v0/Advice/Verify'
            token = None
            sign_data = None  # encrypted token with TripleDes
            r = requests.post(url, data={'Token': token, 'SignData': sign_data})
            res = r.json()
            res_code = res['ResCode']
            amount = res['Amount']
            description = res['Description']
            retrival_ref_no = res['RetrivalRefNo']
            system_trace_no = res['SystemTraceNo']
            invoice_id = res['OrderId']

