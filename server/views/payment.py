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
from server.utils import get_basket, add_one_off_job, sync_storage, add_minutes, set_custom_signed_cookie
from server.serialize import get_tax
from mehr_takhfif.settings import SAFE_IP
import pysnooper
import json
import zeep

from django.core.exceptions import ValidationError
from mehr_takhfif.settings import INVOICE_ROOT, SHORTLINK, STATIC_ROOT, DEBUG
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from server.tasks import cancel_reservation
from server.views.post import get_shipping_cost

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


class PaymentRequest(View):

    @pysnooper.snoop()
    def get(self, request, basket_id):
        ip = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR')

        # debug
        if not request.user.is_staff:
            raise ValidationError(_('متاسفانه در حال حاضر امکان خرید وجود ندارد'))
        if request.user.is_staff:
            invoice = self.create_invoice(request)
            self.submit_invoice_storages(invoice.pk)
            invoice.status = 2
            invoice.payed_at = timezone.now()
            invoice.card_holder = '012345******6789'
            invoice.final_amount = invoice.amount
            invoice.save()
            return HttpResponseRedirect(f'https://mehrtakhfif.com/invoice/{invoice.id}')

        user = request.user
        if not Basket.objects.filter(pk=basket_id, user=user).exists():
            raise ValidationError(_('سبد خرید نامعتبر است'))
        # def check_user_information
        # check for disabling in 15 minutes
        if user.first_name is None or user.last_name is None or user.meli_code is None or user.username is None:
            raise ValidationError(_('لطفا قبل از خرید پروفایل خود را تکمیل نمایید'))
        basket = Basket.objects.filter(user=request.user, id=basket_id).first()
        invoice = self.create_invoice(request)
        self.reserve_storage(basket, invoice)
        self.submit_invoice_storages(invoice.pk)
        return JsonResponse({"url": f"{bp['ipg_url']}?RefId={self.behpardakht_api(invoice.pk)}"})

    @pysnooper.snoop()
    def behpardakht_api(self, invoice_id):
        invoice = Invoice.objects.get(pk=invoice_id)
        basket = get_basket(invoice.user, basket=invoice.basket, return_obj=True, tax=True)
        tax = basket.summary["tax"]
        additional_data = [[1, int(basket.summary["mt_profit"] + basket.summary["ha_profit"] + tax +
                                   basket.summary['shipping_cost']) * 10, 0]]
        # bug '1,49000,0;1,16000,0'
        # todo add feature price
        for basket_product in basket.basket_products:
            try:
                supplier = basket_product.supplier
            except AttributeError:
                continue
            for data in additional_data:
                if supplier.deposit_id == data[0]:
                    data[1] += basket_product.start_price * 10
                    break
            else:
                additional_data.append([supplier.deposit_id, basket_product.start_price * 10, 0])

        additional_data = ';'.join(','.join(str(x) for x in b) for b in additional_data)

        local_date = timezone.now().strftime("%Y%m%d")
        # DEBUG:
        # invoice.amount = 1000
        # additional_data = '1,5000,0;2,5000,0'
        local_time = pytz.timezone("Iran").localize(datetime.now()).strftime("%H%M%S")
        r = "0,123456789"
        if not DEBUG:
            r = client.service.bpCumulativeDynamicPayRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                                             userPassword=bp['password'], localTime=local_time,
                                                             localDate=local_date, orderId=invoice.id,
                                                             amount=(invoice.amount + basket.summary[
                                                                 'shipping_cost']) * 10,
                                                             additionalData=additional_data,
                                                             callBackUrl=bp['callback'])

        if r[0:2] == "0,":
            ref_id = r[2:]
            invoice.reference_id = ref_id
            invoice.save()
            return ref_id
        else:
            raise ValueError(_("can not get ipg page"))

    def create_invoice(self, request, basket=None):
        user = request.user
        address = None
        basket = basket or get_basket(user, request.lang, require_profit=True)
        shipping_price = 0
        if basket['address_required']:
            address = AddressSchema().dump(user.default_address)
            basket['summary']['total_price'] -= basket['summary']['shipping_cost']
            basket['summary']['discount_price'] -= basket['summary']['shipping_cost']
            if shipping_price < 0:
                raise ValidationError('لطفا آدرس خود را در پروفایل ثبت کنید')
        invoice = Invoice.objects.create(created_by=user, updated_by=user, user=user,
                                         mt_profit=basket['summary']['mt_profit'], expire=add_minutes(15),
                                         invoice_discount=basket['summary']['invoice_discount'], address=address,
                                         ha_profit=basket['summary']['ha_profit'], basket_id=basket['basket']['id'],
                                         amount=basket['summary']['discount_price'] + basket['summary']['tax'],
                                         final_price=basket['summary']['total_price'])
        Invoice.objects.create(created_by=user, updated_by=user, user=user, address=address, expire=add_minutes(15),
                               amount=basket['summary']['shipping_cost'], basket_id=basket['basket']['id'])
        return invoice

    @pysnooper.snoop()
    def reserve_storage(self, basket, invoice):
        if basket.sync != 1:  # reserved
            sync_storage(basket, operator.sub)
            task_name = f'{invoice.id}: cancel reservation'
            # args = []
            kwargs = {"invoice_id": invoice.id, "task_name": task_name}
            invoice.sync_task = add_one_off_job(name=task_name, kwargs=kwargs, interval=15,
                                                task='server.tasks.cancel_reservation')
            # basket.active = False
            basket.sync = 1  # reserved
            basket.save()
            invoice.save()

    def submit_invoice_storages(self, invoice_id):
        invoice = Invoice.objects.filter(pk=invoice_id).select_related(*Invoice.select).first()
        basket = get_basket(invoice.user, basket=invoice.basket, return_obj=True)
        invoice_products = []
        for product in basket.basket_products:
            storage = product.storage
            supplier = storage.supplier
            amount = product.start_price
            if not InvoiceSuppliers.objects.filter(invoice=invoice, supplier=supplier).update(
                    amount=F('amount') + amount):
                InvoiceSuppliers.objects.create(invoice=invoice, supplier=supplier, amount=amount)
            tax = get_tax(storage.tax_type, storage.discount_price, storage.start_price)
            invoice_products.append(
                InvoiceStorage(storage=storage, invoice_id=invoice_id, count=product.count, tax=tax * product.count,
                               final_price=storage.final_price - tax, box=product.box, features=product.features,
                               discount_price=storage.discount_price * product.count,
                               start_price=storage.start_price, discount_percent=storage.discount_percent,
                               total_price=(storage.final_price - tax) * product.count,
                               discount_price_without_tax=(storage.discount_price - tax) * product.count,
                               discount=(storage.final_price - storage.discount_price) * product.count,
                               created_by=invoice.user, updated_by=invoice.user),
            )
        InvoiceStorage.objects.bulk_create(invoice_products)


class CallBack(View):

    def get(self, request):
        return HttpResponseRedirect("https://mehrtakhfif.com")

    @pysnooper.snoop()
    def post(self, request):
        # todo redirect to site anyway
        data = request.body.decode().split('&')
        data_dict = {}
        for param in data:
            val = param.split('=')
            data_dict[val[0]] = val[1]
        invoice_id = data_dict['SaleOrderId']
        ref_id = data_dict.get('SaleReferenceId', None)
        invoice = Invoice.objects.get(pk=invoice_id, reference_id=data_dict['RefId'])
        if not ref_id or not self.verify(invoice_id, ref_id):
            self.finish_invoice_jobs(invoice, cancel=True)
            return HttpResponseRedirect("https://mehrtakhfif.com")
        # todo https://memoryleaks.ir/unlimited-charge-of-mytehran-account/
        invoice.status = 2
        invoice.payed_at = timezone.now()
        invoice.card_holder = data_dict['CardHolderPan']
        invoice.final_amount = data_dict['FinalAmount']
        task_name = f'{invoice.id}: send invoice'
        kwargs = {"invoice_id": invoice.pk, "lang": request.lang, 'name': task_name}
        invoice.email_task = add_one_off_job(name=task_name, kwargs=kwargs, interval=0,
                                             task='server.tasks.send_invoice')
        invoice.save()
        self.finish_invoice_jobs(invoice, finish=True)
        return HttpResponseRedirect(f"https://mehrtakhfif.com/invoice/{invoice_id}")

    def finish_invoice_jobs(self, invoice, cancel=None, finish=None):
        if finish:  # successfull payment, cancel task
            task_name = f'{invoice.id}: cancel reservation'
            description = f'{timezone.now()}: canceled by system'
            invoice.basket.status = 3  # done
            invoice.basket.save()
            Basket.objects.create(user=invoice.user, created_by=invoice.user, updated_by=invoice.user)
            PeriodicTask.objects.filter(name=task_name).update(enabled=False, description=description)
        if cancel:
            cancel_reservation(invoice.pk)

    @pysnooper.snoop()
    def verify(self, invoice_id, sale_ref_id):
        r = client.service.bpVerifyRequest(terminalId=bp['terminal_id'], userName=bp['username'],
                                           userPassword=bp['password'], orderId=invoice_id,
                                           saleOrderId=invoice_id, saleReferenceId=sale_ref_id)
        if r == '0':
            return True
        return False
