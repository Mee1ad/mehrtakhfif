from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

from server.serialize import BasketProductSchema, ProductFeatureSchema
from server.utils import *
from server.views.post import *


class BasketView(View):
    def get(self, request):
        try:
            basket = Basket.objects.filter(user=request.user).order_by('-id').first()
        except TypeError:
            basket = None
        deleted_items = self.check_basket(basket)
        return JsonResponse({**get_basket(request, basket=basket, tax=True),
                             'deleted_items': deleted_items})

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
            basket_count = self.add_to_basket(basket, data['products'])
        res = {'basket_count': basket_count, **get_basket(request, use_session=use_session),
               'message': 'محصول با موفقیت به سبد خرید افزوده شد'}
        res = JsonResponse(res)
        res = set_custom_signed_cookie(res, 'basket_count', basket_count)
        return res

    def patch(self, request):
        data = load_data(request)
        pk = data['basket_product_id']
        count = data['count']
        basket = Basket.objects.filter(user=request.user).order_by('-id').first()
        storage = BasketProduct.objects.filter(basket=basket, pk=pk).select_related('storage').first().storage
        assert storage.available_count_for_sale >= count and storage.max_count_for_sale >= count
        assert BasketProduct.objects.filter(id=pk, basket=basket).update(count=data['count'])
        basket.discount_code.update(basket=None)
        return JsonResponse(get_basket(request))

    def delete(self, request):
        basket_product_id = request.GET.get('basket_product_id', None)
        summary = request.GET.get('summary', None)
        try:
            basket = Basket.objects.filter(user=request.user).order_by('-id').first()
            BasketProduct.objects.filter(basket=basket, id=basket_product_id).delete()
            res = {}
            if summary:
                res = get_basket(request)
            basket.discount_code.update(basket=None)
            return JsonResponse(res)
        except (AssertionError, Basket.DoesNotExist):
            return JsonResponse(res_code['bad_request'], status=400)

    def add_to_session(self, request, products):
        for product in products:
            count = int(product['count'])
            storage = Storage.objects.get(pk=product['storage_id'])
            if storage.available_count_for_sale < count or storage.max_count_for_sale < count or storage.disable \
                    or storage.product.disable:
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

    def add_to_basket(self, basket, products):
        for product in products:
            count = int(product['count'])
            storage = Storage.objects.get(pk=product['storage_id'])
            if storage.available_count_for_sale < count or storage.max_count_for_sale < count or storage.disable \
                    or storage.product.disable:
                raise ValidationError(_('متاسفانه این محصول ناموجود میباشد'))
            try:
                basket_product = BasketProduct.objects.filter(basket=basket, storage=storage)
                assert basket_product.exists()
                basket_product.update(count=count)
            except AssertionError:
                box = storage.product.box
                features = storage.features.all()
                features = ProductFeatureSchema().dump(features, many=True)
                BasketProduct.objects.create(basket=basket, storage=storage, count=count, box=box,
                                             features=features)

        basket.count = basket.products.all().count()
        basket.save()
        basket.discount_code.update(basket=None)
        return basket.count

    def check_basket(self, basket):
        basket_products = BasketProduct.objects.filter(basket=basket)
        # todo test
        deleted_items = []
        for basket_product in basket_products:
            if basket_product.count > basket_product.storage.available_count_for_sale:
                deleted_items.append(BasketProductSchema().dump(basket_product))
                basket_product.delete()
        return deleted_items


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

    def post(self, request):
        data = load_data(request)
        user = request.user
        start_date = timestamp_to_datetime(data['start_date'])
        end_date = timestamp_to_datetime(data.get('end_date', data['start_date']))
        preview = get_preview_permission(user, is_get=False, product_check=True)
        try:
            storage = Storage.objects.filter(pk=data['storage_id'], **preview).exclude(product__booking_type=1).\
                select_related('product').only('product__type').first()
            Booking.objects.create(storage_id=data['storage_id'], user=user, created_by=user, updated_by=user,
                                   address_id=user.default_address_id, start_date=start_date, end_date=end_date,
                                   cart_postal_text=data['cart_postal_text'], type=storage.product.booking_type)
            return JsonResponse({'message': 'با موفقیت رزرو شد', 'variant': 'success'})
        except AttributeError:
            return JsonResponse({'message': 'امکان رزرو برای این محصول وجود ندارد', 'variant': 'error'})
