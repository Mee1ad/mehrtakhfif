import requests
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views import View
import operator
from server.models import InvoiceStorage, Basket, User
from django_celery_beat.models import PeriodicTask
from server.serialize import *
import pytz
from datetime import datetime
from server.utils import get_basket, add_one_off_job, sync_storage, add_minutes
import pysnooper
import json
import zeep

ipg = {'data': [{'id': 1, 'key': 'mellat', 'name': 'به پرداخت ملت', 'hide': False, 'disable': False},
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
client = zeep.Client(wsdl="https://bpm.shaparak.ir/pgwchannel/services/pgw?wsdl")

saddad = {'merchant_id': None, 'terminal_id': None, 'terminal_key': None,
          'payment_request': 'https://sadad.shaparak.ir/VPG/api/v0/Request/PaymentRequest',
          'redirect_url': 'https://sadad.shaparak.ir/VPG/Purchase'}  # mellat

pecco = {'pin': '4MuVGr1FaB6P7S43Ggh5', 'terminal_id': '44481453',
         'payment_request': 'https://pec.shaparak.ir/NewIPGServices/Sale/SaleService.asmx'}  # parsian

callback = HOST + "/callback"


class IPG(View):
    def get(self, request):
        return JsonResponse({'ipg': ipg})


class PaymentRequest(View):
    @pysnooper.snoop()
    def get(self, request, basket_id):
        # todo debug
        amount = request.GET.get('a')

        # ipg_id = request.GET.get('ipg_id', 1)
        user = request.user
        assert Basket.objects.filter(pk=basket_id, user=user).exists()
        try:
            invoice = Invoice.objects.get(user=user, basket_id=basket_id, status=1)
            assert invoice.expire >= timezone.now()
            return JsonResponse({"url": f"{bp['ipg_url']}?RefId={invoice.reference_id}"})
        except AssertionError:
            invoice.status = 3
            invoice.save()
        except Invoice.DoesNotExist:
            pass
        basket = Basket.objects.filter(user=request.user, id=basket_id).first()
        invoice = self.create_invoice(request)
        self.reserve_storage(basket, invoice)

        res = {"url": f"{bp['ipg_url']}?RefId={self.behpardakht_api(invoice.pk, amount)}"}
        return JsonResponse(res)

    @pysnooper.snoop()
    def behpardakht_api(self, invoice_id, amount):
        invoice = Invoice.objects.get(pk=invoice_id)
        # todo debug
        invoice.amount = amount

        local_date = timezone.now().strftime("%Y%m%d")
        local_time = pytz.timezone("Iran").localize(datetime.now()).strftime("%H%M%S")
        r = client.service.bpPayRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                        userPassword=bp['password'], localTime=local_time,
                                        localDate=local_date, orderId=invoice.id, amount=invoice.amount,
                                        payerId=0, callBackUrl=bp['callback'])
        if r[0:2] == "0,":
            ref_id = r[2:]
            invoice.reference_id = ref_id
            invoice.save()
            return ref_id
        else:
            raise ValueError("can not get ipg page")

    def ipg_api(self):
        pass
        # encrypt(PKCS7, ECB(TripleDes) = > base64
        # sign_data = des_encrypt(f'{saddad["terminal_id"]};{invoice.pk};{amount}')
        # additional_data = None  # json
        # Type = [Amount, Percentage]
        # multiplexing_data = {'Type': 'Percentage', 'MultiplexingRows': [{'IbanNumber': 1, 'Value': 50}]}
        # return JsonResponse({'token': 'test token', 'description': 'test description',
        #                      'redirect_url':})

        # r = requests.post(url, data={'MerchantId': merchant_id, 'TerminalId': terminal_id, 'Amount': amount,
        #                              'OrderId': invoice_id, 'LocalDateTime': datetime, 'ReturnUrl': return_url,
        #                              'SignData': sign_data, 'AdditionalData': additional_data,
        #                              'MultiplexingData': multiplexing_data})
        # res = r.json()
        # return JsonResponse({'res_code': res['ResCode'], 'token': res['Token'], 'description': res['Description'],
        #                      'redirect_url': 'https://sadad.shaparak.ir/VPG/Purchase'})
        #
        # url = pecco['payment_request']
        # request_data = {'LoginAccount': pecco['pin'], 'Amount': amount, 'OrderId': invoice.id,
        #                 'CallBackUrl': 'http://localhost/callback', 'AdditionalData': None}
        # r = requests.post(url=pecco['payment_request'], data=request_data)
        # print(r.status_code)
        # print(r.content)

    @pysnooper.snoop()
    def create_invoice(self, request, basket=None):
        user = request.user
        address = None
        basket = basket or get_basket(user, request.lang)
        if basket['address_required']:
            address = user.default_address

        invoice = Invoice(created_by=user, updated_by=user, user=user, amount=basket['summary']['discount_price'],
                          type=1, address=address, tax=5, basket_id=basket['basket']['id'],
                          final_price=basket['summary']['total_price'], expire=add_minutes(13))
        invoice.save()
        return invoice

    @pysnooper.snoop()
    def reserve_storage(self, basket, invoice):
        if basket.sync == 'false':
            sync_storage(basket, operator.sub)
            task_name = f'{invoice.id}: cancel reservation'
            # args = []
            kwargs = {"invoice_id": invoice.id, "task_name": task_name}
            invoice.task = add_one_off_job(name=task_name, kwargs=kwargs, interval=5,
                                           task='server.tasks.cancel_reservation')
            # basket.active = False
            basket.sync = 'reserved'
            basket.save()
            invoice.save()


class CallBack(View):
    @pysnooper.snoop()
    def post(self, request):
        data = request.body.decode().split('&')
        data_dict = {}
        for param in data:
            val = param.split('=')
            data_dict[val[0]] = val[1]
        invoice_id = data_dict['SaleOrderId']
        ref_id = data_dict.get('SaleReferenceId', None)
        if not ref_id:
            return HttpResponseRedirect("https://mehrtakhfif.com")
        self.verify(invoice_id, invoice_id, ref_id)
        # self.submit_invoice_storages(invoice_id)
        try:
            invoice = Invoice.objects.get(pk=invoice_id, reference_id=ref_id)
            invoice.status = 2
            invoice.payed_at = timezone.now()
            invoice.card_holder = data_dict['CardHolderPan']
            invoice.final_amount = data_dict['FinalAmount']
            invoice.basket.sync = 'done'
            invoice.basket.save()
            invoice.save()
        except Exception as e:
            print(e)
        return HttpResponseRedirect("https://mehrtakhfif.com")

    @pysnooper.snoop()
    def verify(self, invoice_id, sale_order_id, sale_ref_id):
        r = client.service.bpVerifyRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                           userPassword=bp['password'], orderId=invoice_id,
                                           saleOrderId=sale_order_id, saleReferenceId=sale_ref_id)
        if r == '0':
            return True

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
                               vip_discount_percent=storage.vip_discount_percent, box=product.box))
        task_name = f'{invoice.id}: cancel reservation'
        description = f'{timezone.now()}: canceled by system'
        PeriodicTask.objects.filter(name=task_name).update(enabled=False, description=description)
        InvoiceStorage.objects.bulk_create(invoice_products)
