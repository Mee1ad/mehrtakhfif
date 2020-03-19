from server.utils import *
from django.http import JsonResponse
from mehr_takhfif.settings import TOKEN_SALT
import pysnooper
from django.db.models import F


class BasketView(LoginRequired):
    def get(self, request):
        basket_id = request.GET.get('basket_id', None)
        return JsonResponse(get_basket(request.user, request.lang, basket_id))

    @pysnooper.snoop()
    def post(self, request):
        data = load_data(request)
        try:
            assert request.user.is_authenticated
            basket = Basket.objects.filter(user=request.user).order_by('-id').first()
        except Basket.DoesNotExist:
            basket = Basket.objects.create(user=request.user, created_by=request.user, updated_by=request.user)
        except AssertionError:
            return JsonResponse({}, status=401)
        basket_count = self.add_to_basket(basket, data['products'])
        res = {'new_basket_count': basket_count, **get_basket(request.user, request.lang)}
        res = JsonResponse(res)
        res.set_signed_cookie('new_basket_count', basket_count, TOKEN_SALT)
        return res

    def patch(self, request):
        data = load_data(request)
        basket = Basket.objects.filter(user=request.user).order_by('-id').first()
        # todo remove assertion
        assert BasketProduct.objects.filter(id=data['basket_product_id'], basket=basket).update(count=data['count'])
        return JsonResponse(get_basket(request.user, request.lang))

    def delete(self, request):
        basket_product_id = request.GET.get('basket_product_id', None)
        basket_id = request.GET.get('basket_id', None)
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
        # {"id": 1, "count": 5, "features": [{"fid": 16, "fvid": [1, 2]}]}
        for product in products:
            pk = int(product['id'])
            count = int(product['count'])
            features = product['features']
            # todo validate features
            # https://github.com/alecthomas/voluptuous
            try:
                basket_product = BasketProduct.objects.filter(basket=basket, storage_id=pk, features=features).\
                    select_related('storage')
                storage = basket_product.first().storage
                assert storage.available_count_for_sale >= count and storage.max_count_for_sale >= count
                basket_product.update(count=count)
            except AttributeError:
                box = Storage.objects.get(pk=pk).product.box
                BasketProduct.objects.create(basket=basket, storage_id=pk, count=count, box=box, features=features)

        basket.count = basket.products.all().count()
        basket.save()
        return basket.count

    @staticmethod
    def check_basket(user, basket):
        products = basket.product.all()
        count = 0
        amount = 0
        for product in products:
            count += product.count
            amount += product.discount_price * product.count
        return count


class GetProducts(View):
    def post(self, request):
        data = load_data(request)
        storage_ids = [item['id'] for item in data['basket']]
        basket = data['basket']
        assert not request.user.is_authenticated
        storages = Storage.objects.filter(id__in=storage_ids).select_related('product')
        basket_products = []
        address_required = False
        for item in basket:
            print('hey')
            storage = next(storage for storage in storages if item['id'] == storage.pk)  # search
            obj = type('BasketProduct', (object,), {})()
            obj.count = item['count']
            obj.product = storage.product
            obj.storage_id = storage.pk
            obj.features = item['features']
            if obj.product.type == 'product' and not address_required:
                address_required = True
            obj.product.default_storage = storage
            basket_products.append(obj)

        products = BasketProductSchema(language=request.lang).dump(basket_products, many=True)
        products = add_feature_price(products)

        profit = calculate_profit(products)
        return JsonResponse({'products': products, 'summary': profit, 'address_required': address_required})


class InvoiceView(View):
    @pysnooper.snoop()
    def get(self, request):
        # email.attach_file('/images/weather_map.png')
        return JsonResponse(default_response['ok'])
