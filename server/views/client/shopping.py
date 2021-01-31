import operator
import traceback

from django.http import JsonResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from mehr_takhfif.settings import CLIENT_HOST
from server.serialize import BasketProductSchema, ProductFeatureSchema, AddressSchema, MediaSchema
from server.utils import *
from server.views.payment import PaymentRequest, CallBack
from server.views.post import *


class BasketView(View):
    def get(self, request):
        try:
            basket = Basket.objects.filter(user=request.user) \
                .annotate(invoice_exists=Count('invoice', filter=Q(invoice__user=request.user, invoice__status=1,
                                                                   invoice__expire__gt=timezone.now(),
                                                                   invoice__final_price__isnull=False))) \
                .prefetch_related('basket_storages__storage__features', 'basket_storages__storage__product__box',
                                  'basket_storages__storage__product__thumbnail',
                                  'basket_storages__storage__vip_prices') \
                .order_by('-id').first()
        except TypeError:
            basket = None
        invoices = []
        if getattr(basket, 'invoice_exists', None):
            try:
                invoices = Invoice.objects.filter(user=request.user, status=1, expire__gt=timezone.now(),
                                                  final_price__isnull=False)
                invoices = InvoiceSchema(only=['id', 'amount', 'expire', 'payment_url'], with_shipping_cost=True) \
                    .dump(invoices, many=True)
            except TypeError:  # AnonymousUser
                pass
        return JsonResponse({**get_basket(request, basket=basket, tax=True), 'active_invoice': list(invoices)})

    def post(self, request):
        data = load_data(request)
        user = request.user
        use_session = False
        if not user.is_authenticated or (DEBUG is True and data.get('use_session', None) is True):
            basket_count = self.add_to_session(request, data['products'])
            use_session = True
        else:
            baskets = Basket.objects.filter(user=user).order_by('-id')
            basket = baskets.first()
            if not basket:
                basket = Basket.objects.create(user=user, created_by=user, updated_by=user)
            basket_count = add_to_basket(basket, data['products'])
        res = {'basket_count': basket_count, **get_basket(request, use_session=use_session),
               'message': 'محصول با موفقیت به سبد خرید افزوده شد'}
        res = JsonResponse(res)
        res = set_custom_signed_cookie(res, 'basket_count', basket_count)
        return res

    def patch(self, request):
        data = load_data(request)
        pk = data['basket_product_id']
        count = data['count']
        user = request.user
        if not user.is_authenticated:
            product = request.session.get('basket', [])[pk]
            storage = Storage.objects.filter(pk=product['storage_id']).first()
            if storage.is_available(count) is False:
                return JsonResponse({'message': 'تعداد درخواست شده موجود نمیباشد', 'variant': 'error'})
            product['count'] = count
            request.session.save()
            res = JsonResponse(get_basket(request))
            return set_custom_signed_cookie(res, 'basket_count', get_basket_count(user, session=request.session))
        basket = Basket.objects.filter(user=user).order_by('-id').first()
        basket_product = BasketProduct.objects.filter(basket=basket, pk=pk).select_related('storage')
        storage = basket_product.first().storage
        if storage.is_available(count) is False:
            return JsonResponse({'message': 'تعداد درخواست شده موجود نمیباشد', 'variant': 'error'})
        basket_product.update(count=data['count'])
        basket.discount_code.update(basket=None)
        res = JsonResponse(get_basket(request))
        return set_custom_signed_cookie(res, 'basket_count', get_basket_count(user, basket_id=basket.id))

    def delete(self, request):
        # storage_id = request.GET.get('storage_id', None)
        basket_product_id = request.GET.get('basket_product_id', None)
        summary = request.GET.get('summary', None)
        try:
            try:
                basket = Basket.objects.filter(user=request.user).order_by('-id').first()
                BasketProduct.objects.filter(basket=basket, id=basket_product_id).delete()
                basket.discount_code.update(basket=None)
            except TypeError:
                session = request.session
                products = session.get('basket', [])
                products.pop(int(basket_product_id))
                session.save()
            res = {}
            if summary:
                res = get_basket(request)
            return JsonResponse(res)
        except (AssertionError, Basket.DoesNotExist):
            return JsonResponse(res_code['bad_request'], status=400)

    def add_to_session(self, request, products):
        for product in products:
            count = int(product['count'])
            storage = Storage.objects.get(pk=product['storage_id'])
            if is_available(storage, count) is False:
                print('count:', count, 'available_count_for_sale:', storage.available_count_for_sale,
                      'max_count_for_sale:', storage.max_count_for_sale, 'storage.disable:', storage.disable,
                      'storage.product.disable:', storage.product.disable)
                raise ValidationError(_('متاسفانه این محصول ناموجود میباشد'))
            basket = request.session.get('basket', [])
            duplicate_basket_product_index = [basket.index(basket_product) for basket_product in basket if
                                              basket_product['storage_id'] == storage.pk]
            features = storage.features.all()
            product['features'] = ProductFeatureSchema().dump(features, many=True)
            product['box_id'] = storage.product.box_id
            if duplicate_basket_product_index:
                request.session['basket'][duplicate_basket_product_index[0]] = product
                request.session.save()
                return len(request.session['basket'])
            if not basket:
                request.session['basket'] = []
            request.session['basket'].append(product)
            request.session.save()
            return len(request.session['basket'])


class GetProducts(View):
    def post(self, request):
        data = load_data(request)
        storage_ids = [item['id'] for item in data['basket']]
        products = data['basket']
        basket = type('Basket', (), {})()
        basket.basket_products = []
        if DEBUG is False:
            assert not request.user.is_authenticated
        storages = Storage.objects.filter(id__in=storage_ids).select_related('product')
        address_required = False
        for item in products:
            storage = next(storage for storage in storages if item['id'] == storage.pk)  # search
            obj = type('BasketProduct', (), {})()
            obj.count = item['count']
            obj.product = storage.product
            obj.storage = storage
            obj.features = item['features']
            if obj.product.type == 'product' and not address_required:
                address_required = True
            obj.product.default_storage = storage
            basket.basket_products.append(obj)

        basket = get_basket(request, basket=basket, basket_products=basket.basket_products)
        return JsonResponse(basket)

    def patch(self, request):
        data = load_data(request)
        basket = data['basket']
        product = data['product']
        for p in basket:
            if p['storage_id'] == product['storage_id'] and p['features'] == product['features']:
                return JsonResponse({'index': basket.index(p)})
        return JsonResponse({'index': -1})


class InvoiceView(View):
    def get(self, request):
        # email.attach_file('/images/weather_map.png')
        return JsonResponse(res_code['ok'])


class DiscountCodeView(View):
    def post(self, request):
        data = json.loads(request.body)
        code = data['code']
        try:
            discount_code = DiscountCode.objects.exclude(basket__invoice__expire__gte=timezone.now()) \
                .get(code=code, invoice_storage__isnull=True, basket__isnull=True)
            discount_code.basket = request.basket
            discount_code.save()
            if discount_code.type == 3:  # post
                return JsonResponse({'message': 'هزینه پست شما رایگان شد', 'variant': 'success'})
            return JsonResponse({'message': 'کد تخفیف اعمال شد', 'variant': 'success'})
        except DiscountCode.DoesNotExist:
            return JsonResponse({'message': 'به نظر نمیاد این کد کاری بکنه!', 'variant': 'warning'})


class BookingView(View):

    def get(self, request, invoice_id):
        if DEBUG is True:
            invoice = Invoice.objects.get(pk=invoice_id)
            invoice.status = 2
            invoice.payed_at = timezone.now()
            invoice.card_holder = '012345******6789'
            invoice.final_amount = invoice.amount
            invoice.save()
            # task_name = f'{invoice.id}: send invoice'
            # kwargs = {"invoice_id": invoice.pk, "lang": request.lang, 'name': task_name}
            Basket.objects.create(user=invoice.user, created_by=invoice.user, updated_by=invoice.user)
            CallBack.notification_admin(invoice)
            # return JsonResponse({'invoice_id': invoice.id})
            # return HttpResponseRedirect(f"http://mt.com:3002/invoice/{invoice.id}")
            return HttpResponseRedirect(f"{CLIENT_HOST}/invoice/{invoice.id}")
        url = PaymentRequest.behpardakht_api(invoice_id, booking=True)
        return HttpResponseRedirect(url)

    def post(self, request):
        data = load_data(request)
        user = request.user
        start_date = timestamp_to_datetime(data['start_date'])
        end_date = timestamp_to_datetime(data.get('end_date', data['start_date']))
        count = data.get('count', 1)
        preview = get_preview_permission(user, is_get=False, product_check=True)
        # statuss = ((1, 'pending'), (2, 'payed'), (3, 'canceled'), (4, 'rejected'), (5, 'sent'), (6, 'ready'))
        invoice = Invoice.objects.filter(user=user, status__in=[1])
        try:
            storage = Storage.objects.filter(pk=data['storage_id'], **preview).exclude(product__booking_type=1). \
                select_related('product').prefetch_related(
                'product__features').only('product__type', 'product__thumbnail', 'product__box').first()
            if storage.is_available(count) is False:
                raise ValidationError(_('تعداد درخواست شده موجود نمیباشد'))
            invoice_id = self.create_invoice(request, storage, count, start_date, end_date,
                                             data['cart_postal_text'])
            invoice = HOST + f"/booking/{invoice_id}"
            address = Address.objects.filter(pk=user.default_address_id).select_related('city', 'state').first()
            res = {"address": AddressSchema().dump(address),
                   'start_date': data['start_date'], "thumbnail": MediaSchema().dump(storage.product.thumbnail),
                   'cart_postal': data['cart_postal_text'], 'invoice': invoice}
            return JsonResponse({'data': res, 'message': 'رزرو شما پس از پرداخت فعال میشود', 'variant': 'success'})
        except AttributeError:
            traceback.print_exc()
            return JsonResponse({'message': 'امکان رزرو برای این محصول وجود ندارد', 'variant': 'error'}, status=400)

    def create_invoice(self, request, storage, count, start_date, end_date, cart_postal_text, charity_id=1):
        user = request.user
        if user.default_address.state_id != 25:
            raise ValidationError('در حال حاضر محصولات فقط در استان گیلان قابل ارسال میباشد')
        if storage.shipping_cost:
            shipping_cost = storage.shipping_cost + storage.booking_cost
        else:
            shipping_cost = get_shipping_cost_temp(user) + storage.booking_cost
        tax = get_tax(storage.tax_type, storage.discount_price, storage.start_price)
        address = AddressSchema().dump(user.default_address)
        post_invoice = Invoice.objects.create(created_by=user, updated_by=user, user=user, address=address,
                                              amount=shipping_cost)

        invoice = Invoice.objects.create(created_by=user, updated_by=user, user=user, charity_id=charity_id,
                                         final_price=storage.final_price,
                                         amount=storage.discount_price + tax, start_date=start_date,
                                         end_date=end_date, details={'cart_postal': cart_postal_text},
                                         invoice_discount=storage.final_price - storage.discount_price, address=address,
                                         max_shipping_time=storage.max_shipping_time, post_invoice=post_invoice)
        self.submit_invoice_storages(invoice.pk, storage, user.pk, count)
        InvoiceSuppliers.objects.create(invoice=invoice, supplier=storage.supplier, amount=storage.start_price)
        return invoice.pk

    def reserve_storage(self, basket, invoice):
        sync_storage(basket, operator.sub)
        # task_name = f'{invoice.id}: cancel reservation'
        # kwargs = {"invoice_id": invoice.id, "task_name": task_name}
        # invoice.sync_task = add_one_off_job(name=task_name, kwargs=kwargs, interval=30,
        #                                     task='server.tasks.cancel_reservation')
        # invoice.save()

    def submit_invoice_storages(self, invoice_id, storage, user_id, count=1):
        storage.count = count
        storage.storage = storage
        share = get_share(storage)
        product = storage.product
        InvoiceStorage.objects.create(storage=storage, invoice_id=invoice_id, count=count,
                                      tax=share['tax'] * count,
                                      final_price=(storage.final_price - share['tax']) * count, box=product.box,
                                      discount_price=storage.discount_price * count,
                                      charity=share['charity'] * count,
                                      start_price=storage.start_price * count, admin=share['admin'] * count,
                                      mt_profit=share['mt_profit'],
                                      total_price=(storage.final_price - share['tax']) * count,
                                      dev=share['dev'] * count,
                                      discount_price_without_tax=(storage.discount_price - share['tax']) * count,
                                      discount=(storage.final_price - storage.discount_price) * count,
                                      created_by_id=user_id, updated_by_id=user_id)
