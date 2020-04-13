import pdfkit
import os
from mehr_takhfif.settings import BASE_DIR
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views import View
import operator
from server.models import InvoiceStorage, Basket, DiscountCode, InvoiceSuppliers
from django_celery_beat.models import PeriodicTask
from server.serialize import *
import pytz
from datetime import datetime
from server.utils import get_basket, add_one_off_job, sync_storage, add_minutes
import pysnooper
import json
import zeep

from django.core.exceptions import ValidationError
import random
import string

from mehr_takhfif.settings import INVOICE_ROOT, SHORTLINK, STATIC_ROOT

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
# client = zeep.Client(wsdl="https://bpm.shaparak.ir/pgwchannel/services/pgw?wsdl")

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
        # return JsonResponse({"url": "http://api.mt.com/payment/callback"})
        # ipg_id = request.GET.get('ipg_id', 1)
        return JsonResponse({"behpardakht": {"url": f"{bp['ipg_url']}?RefId={self.behpardakht_api(basket_id)}"}})

        user = request.user
        if not Basket.objects.filter(pk=basket_id, user=user).exists():
            raise ValidationError('invalid basket_id')
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

        # res = {"url": f"{bp['ipg_url']}?RefId={self.behpardakht_api(invoice.pk)}"}
        # todo debug
        res = {"url": f"{bp['ipg_url']}?RefId=12345"}
        return JsonResponse(res)

    @pysnooper.snoop()
    def behpardakht_api(self, invoice_id):
        # invoice = Invoice.objects.get(pk=invoice_id)
        # basket = get_basket(invoice.user, basket=invoice.basket, return_obj=True)
        # additional_data = []
        # for basket_product in basket.basket_products:
        #     supplier = basket_product.supplier
        #     for data in additional_data:
        #         if supplier.deposit_id == data[0]:
        #             data[1] += basket_product.start_price
        #             break
        #     else:
        #         additional_data.append([supplier.deposit_id, basket_product.start_price, 0])
        #
        # additional_data = ';'.join(','.join(str(x) for x in b) for b in additional_data)
        # additional_data += f';1,{basket.summary["mt_profit"]}, 0'

        # todo debug
        additional_data = '1,100,0;2,100,0'
        invoice = obj = type('BasketProduct', (), {})()
        invoice.amount = 200
        invoice.id = invoice_id

        local_date = timezone.now().strftime("%Y%m%d")
        local_time = pytz.timezone("Iran").localize(datetime.now()).strftime("%H%M%S")
        r = client.service.bpCumulativeDynamicPayRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                                         userPassword=bp['password'], localTime=local_time,
                                                         localDate=local_date, orderId=invoice.id,
                                                         amount=invoice.amount,
                                                         payerId=0, callBackUrl=bp['callback'])
        if r[0:2] == "0,":
            ref_id = r[2:]
            invoice.reference_id = ref_id
            invoice.save()
            return ref_id
        else:
            raise ValueError("can not get ipg page")

    @pysnooper.snoop()
    def create_invoice(self, request, basket=None):
        user = request.user
        address = None
        basket = basket or get_basket(user, request.lang)
        if basket['address_required']:
            address = user.default_address

        invoice = Invoice.objects.create(created_by=user, updated_by=user, user=user,
                                         amount=basket['summary']['discount_price'],
                                         type=1, address=address, tax=5, basket_id=basket['basket']['id'],
                                         final_price=basket['summary']['total_price'], expire=add_minutes(1))
        return invoice

    @pysnooper.snoop()
    def reserve_storage(self, basket, invoice):
        if basket.sync == 'false':
            sync_storage(basket, operator.sub)
            task_name = f'{invoice.id}: cancel reservation'
            # args = []
            kwargs = {"invoice_id": invoice.id, "task_name": task_name}
            invoice.sync_task = add_one_off_job(name=task_name, kwargs=kwargs, interval=1,
                                                task='server.tasks.cancel_reservation')
            # basket.active = False
            basket.sync = 'reserved'
            basket.save()
            invoice.save()


class CallBack(View):

    # todo remove after debug
    def get(self, request):
        # return HttpResponseRedirect("http://mt.com:3000/shopping/fail")
        digital = Invoice.objects.get(pk=102).storages.filter(product__type=1).exists()
        return HttpResponseRedirect("http://mt.com:3000/shopping/invoice?id=102&d=" + str(digital).lower())

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
        # todo https://memoryleaks.ir/unlimited-charge-of-mytehran-account/
        if not self.verify(invoice_id, ref_id):
            raise ValidationError('payment failed')
        invoice = Invoice.objects.get(pk=invoice_id, reference_id=data_dict['RefId'])
        invoice.status = 2
        invoice.payed_at = timezone.now()
        invoice.card_holder = data_dict['CardHolderPan']
        invoice.final_amount = data_dict['FinalAmount']
        invoice.basket.sync = 'done'
        invoice.basket.save()
        # self.submit_invoice_storages(invoice_id)
        task_name = f'{invoice.id}: send invoice'
        kwargs = {"invoice_id": invoice.pk, "lang": request.lang}
        invoice.email_task = add_one_off_job(name=task_name, kwargs=kwargs, interval=0,
                                             task='server.tasks.send_invoice')
        invoice.save()
        return HttpResponseRedirect(f"https://mehrtakhfif.com/invoice/{invoice_id}")

    @pysnooper.snoop()
    def verify(self, invoice_id, sale_ref_id):
        r = client.service.bpVerifyRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                           userPassword=bp['password'], orderId=invoice_id,
                                           saleOrderId=invoice_id, saleReferenceId=sale_ref_id)
        if r == '0':
            return True
        return False

    @pysnooper.snoop()
    def submit_invoice_storages(self, invoice_id):
        invoice = Invoice.objects.filter(pk=invoice_id).select_related(*Invoice.select).first()
        basket = get_basket(invoice.user, basket=invoice.basket, return_obj=True)
        invoice_products = []
        for product in basket.basket_products:
            supplier = product.supplier
            amount = product.start_price
            if not InvoiceSuppliers.objects.filter(invoice=invoice, supplier=supplier).update(amount=amount):
                InvoiceSuppliers.objects.create(invoice=invoice, supplier=supplier, amount=amount)
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
