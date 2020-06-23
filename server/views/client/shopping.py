from server.utils import *
from django.http import JsonResponse, HttpResponseBadRequest
from mehr_takhfif.settings import TOKEN_SALT, DEBUG
import pysnooper
from django.db.models import F
from django.utils.translation import gettext_lazy as _
from server.serialize import BasketProductSchema
from server.views.post import *


class BasketView(LoginRequired):
    def get(self, request):
        basket = Basket.objects.filter(user=request.user).order_by('-id').first()
        deleted_items = self.check_basket(basket)
        return JsonResponse({**get_basket(request.user, request.lang, basket=basket, tax=True),
                             'deleted_items': deleted_items})

    def post(self, request):
        data = load_data(request)
        try:
            assert request.user.is_authenticated
            basket = Basket.objects.filter(user=request.user).order_by('-id').first()
            if not basket:
                basket = Basket.objects.create(user=request.user, created_by=request.user, updated_by=request.user)
        except AssertionError:
            return JsonResponse({}, status=401)
        basket_count = self.add_to_basket(basket, data['products'])
        res = {'new_basket_count': basket_count, **get_basket(request.user, request.lang)}
        res = JsonResponse(res)
        res = set_custom_signed_cookie(res, 'new_basket_count', basket_count)
        return res

    def patch(self, request):
        data = load_data(request)
        pk = data['basket_product_id']
        count = data['count']
        basket = Basket.objects.filter(user=request.user).order_by('-id').first()
        storage = BasketProduct.objects.filter(basket=basket, pk=pk).select_related('storage').first().storage
        assert storage.available_count_for_sale >= count and storage.max_count_for_sale >= count
        assert BasketProduct.objects.filter(id=pk, basket=basket).update(count=data['count'])
        return JsonResponse(get_basket(request.user, request.lang))

    def delete(self, request):
        basket_product_id = request.GET.get('basket_product_id', None)
        summary = request.GET.get('summary', None)
        try:
            basket = Basket.objects.filter(user=request.user).order_by('-id').first()
            BasketProduct.objects.filter(basket=basket, id=basket_product_id).delete()
            res = {}
            if summary:
                res = get_basket(request.user, request.lang)
            return JsonResponse(res)
        except (AssertionError, Basket.DoesNotExist):
            return JsonResponse(default_response['bad'], status=400)

    def add_to_basket(self, basket, products):
        # {"id": 1, "count": 5, "features": [{"fsid": 16, "fvid": [1, 2]}]}
        for product in products:
            pk = int(product['id'])
            count = int(product['count'])
            features = product['features']
            try:
                basket_product = BasketProduct.objects.filter(basket=basket, storage_id=pk, features=features). \
                    select_related('storage')
                storage = basket_product.first().storage
                if storage.available_count_for_sale < count or storage.max_count_for_sale < count or storage.disable \
                        or storage.product.disable:
                    raise ValidationError(_('متاسفانه این محصول ناموجود میباشد'))
                basket_product.update(count=count)
            except AttributeError:
                box = Storage.objects.get(pk=pk).product.box
                basket_product = BasketProduct(basket=basket, storage_id=pk, count=count, box=box, features=features)
                basket_product.validation()
                storage = basket_product.storage
                if storage.available_count_for_sale < count or storage.max_count_for_sale < count or storage.disable \
                        or storage.product.disable:
                    raise ValidationError(_('متاسفانه این محصول ناموجود میباشد'))
                basket_product.save()

        basket.count = basket.products.all().count()
        basket.save()
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

        basket = get_basket(request.user, request.lang, basket=basket, basket_products=basket.basket_products)
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
        return JsonResponse(default_response['ok'])
