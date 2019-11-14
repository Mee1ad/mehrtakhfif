from server.views.utils import *
from django.http import HttpResponse
from django.template.loader import render_to_string
import tempfile
from mehr_takhfif.settings import TOKEN_SALT
from django.core.mail import EmailMessage
import pysnooper
import pdfkit
from django.db.models import F


class BasketView(View):
    def get(self, request):
        try:
            assert request.user.is_authenticated  # must be logged in
            return JsonResponse(self.get_basket(request.user, request.lang))
        except AssertionError:
            return JsonResponse({}, status=401)

    def post(self, request):
        data = json.loads(request.body)
        try:
            assert request.user.is_authenticated
            basket = Basket.objects.get(user=request.user, active=True)
        except Basket.DoesNotExist:
            basket = Basket(user=request.user, created_by=request.user, updated_by=request.user, active=True)
            basket.save()
        except AssertionError:
            return JsonResponse({}, status=401)
        basket_count = self.add_to_basket(basket, data['products'], data['override'], data['add'])
        res = {'new_basket_count': basket_count}
        if data['summary']:
            res = {**res, **self.get_basket(request.user, request.lang)}
        res = JsonResponse(res)
        res.set_signed_cookie('new_basket_count', basket_count, TOKEN_SALT)
        return res

    def delete(self, request):
        storage_id = request.GET.get('product_id', None)
        summary = request.GET.get('summary', None)
        try:
            basket = Basket.objects.get(user=request.user, active=True)
            assert BasketProduct.objects.filter(basket__user=request.user, basket_id=basket.id,
                                                storage_id=storage_id).exists()
            BasketProduct.objects.filter(basket_id=basket.id, storage_id=storage_id).delete()
            res = {}
            if summary:
                res = self.get_basket(request.user, request.lang)
            return JsonResponse(res)
        except (AssertionError, Basket.DoesNotExist):
            return JsonResponse(default_response['bad'], status=400)

    def get_basket(self, user, lang):
        products = BasketProduct.objects.select_related('storage', 'basket').filter(basket__user=user)
        profit = calculate_profit(products)
        basket = BasketSchema(lang).dump(products[0].basket)
        basket['products'] = BasketProductSchema(lang).dump(products, many=True)
        return {'basket': basket, 'summary': profit}

    def add_to_basket(self, basket, products, override, add):
        for product in products:
            pk = int(product['id'])
            count = int(product['count'])
            try:
                product = BasketProduct.objects.filter(basket=basket, storage_id=pk).\
                    select_related('storage')
                if product:
                    available_count = product.first().storage.available_count_for_sale
                    assert available_count >= count
                    if add:
                        product.update(count=F('count') + count)
                    if override:
                        product.update(count=count)
                    continue
                product = Storage.objects.filter(id=pk)
                if product.exists():
                    BasketProduct(basket=basket, storage_id=pk, count=count).save()
                    continue
            except AssertionError:
                product.update(count=count)
        basket.count = basket.products.all().count()
        basket.save()
        return basket.count

    def get_basket_count(self, basket_id, user):
        basket = Basket.objects.filter(pk=basket_id, user=user, active=True).prefetch_related('product')
        products = basket.product.all()
        count = 0
        for product in products:
            count += product.count
        return count


class InvoiceView(View):
    @pysnooper.snoop()
    def get(self, request):

        # email.attach_file('/images/weather_map.png')
        return JsonResponse(default_response['ok'])


