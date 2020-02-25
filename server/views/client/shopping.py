from server.utils import *
from django.http import JsonResponse
from mehr_takhfif.settings import TOKEN_SALT
import pysnooper
from django.db.models import F


class BasketView(LoginRequired):
    def get(self, request):
        return JsonResponse(get_basket(request.user, request.lang))

    def post(self, request):
        data = load_data(request)
        try:
            assert request.user.is_authenticated
            basket = Basket.objects.filter(user=request.user).order_by('-id').first()
        except Basket.DoesNotExist:
            basket = Basket.objects.create(user=request.user, created_by=request.user, updated_by=request.user)
        except AssertionError:
            return JsonResponse({}, status=401)
        basket_count = self.add_to_basket(basket, data['products'], data['override'], data['add'])
        res = {'new_basket_count': basket_count, **get_basket(request.user, request.lang)}
        res = JsonResponse(res)
        res.set_signed_cookie('new_basket_count', basket_count, TOKEN_SALT)
        return res

    @pysnooper.snoop()
    def delete(self, request):
        storage_id = request.GET.get('storage_id', None)
        basket_id = request.GET.get('basket_id', None)
        summary = request.GET.get('summary', None)
        try:
            basket = Basket.objects.get(pk=basket_id, user=request.user, active=True)
            assert BasketProduct.objects.filter(basket__user=request.user, basket_id=basket.id,
                                                storage_id=storage_id).exists()
            BasketProduct.objects.filter(basket_id=basket.id, storage_id=storage_id).delete()
            res = {}
            if summary:
                res = get_basket(request.user, request.lang)
            return JsonResponse(res)
        except (AssertionError, Basket.DoesNotExist):
            return JsonResponse(default_response['bad'], status=400)

    def add_to_basket(self, basket, products, override, can_add):
        for product in products:
            pk = int(product['id'])
            count = int(product['count'])
            try:
                product = BasketProduct.objects.filter(basket=basket, storage_id=pk). \
                    select_related('storage')
                if product:
                    available_count = product.first().storage.available_count_for_sale
                    assert available_count >= count
                    if can_add:
                        product.update(count=F('count') + count)
                    if override:
                        product.update(count=count)
                    continue
                product = Storage.objects.filter(id=pk)
                if product.exists():
                    BasketProduct.objects.create(basket=basket, storage_id=pk, count=count,
                                                 box=product.first().product.box, )
                    continue
            except AssertionError:
                product.update(count=count)
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
        for storage, item in zip(storages, basket):
            item = next(item for item in basket if item['id'] == storage.pk)  # search in dictionary
            obj = type('Basket', (object,), {})()
            obj.count = item['count']
            obj.product = storage.product
            if obj.product.type == 'product' and not address_required:
                address_required = True
            obj.product.default_storage = storage
            basket_products.append(obj)

        products = BasketProductSchema(language=request.lang).dump(basket_products, many=True)
        profit = calculate_profit(products)
        return JsonResponse({'products': products, 'summary': profit, 'address_required': address_required})


class InvoiceView(View):
    @pysnooper.snoop()
    def get(self, request):
        # email.attach_file('/images/weather_map.png')
        return JsonResponse(default_response['ok'])
