from server.models import *
from django.http import JsonResponse, HttpResponse
from server.views.utils import View
import json
from server.serialize import *
from django.db import IntegrityError
from django.db.models import F


class Buy(View):

    def get(self, request):
        products = BasketProduct.objects.select_related('storage', 'basket').filter(basket__user=request.user)
        basket = BasketSchema(request.lang).dump(products[0].basket)
        basket['products'] = BasketProductSchema(request.lang).dump(products, many=True)
        return JsonResponse({'basket': basket})

    def post(self, request):
        data = json.loads(request.body)
        try:
            basket = Basket.objects.get(user=request.user, status=0)
            assert not BasketProduct.objects.filter(basket_id=basket.pk, storage_id=data['product_id'])
            BasketProduct(basket_id=basket.pk, storage_id=data['product_id'], count=data['count']).save()
            Basket.objects.filter(user=request.user).update()
            return JsonResponse(self.response['ok'])
        except Basket.DoesNotExist:
            Basket(user=request.user, count=data['count'], created_by=request.user, updated_by=request.user,
                   status=0).save()
            self.post(request)
        except AssertionError:
            return JsonResponse(self.response['ok'])
        except IntegrityError:
            return JsonResponse(self.response['bad'])


    def put(self, request):
        data = json.loads(request.body)
        try:
            basket = Basket.objects.get(user=request.user, status=0)
            basket_product = BasketProduct.objects.select_related('storage')\
                .get(basket_id=basket.pk, storage_id=data['product_id'])

            available_count = basket_product.storage.available_count_for_sale
            if available_count >= data['count']:
                basket_product.count = data['count']
                basket_product.save()
                return JsonResponse(self.response['ok'])
            return JsonResponse({'count': available_count}, status=204)
        except (Basket.DoesNotExist, BasketProduct.DoesNotExist):
            return JsonResponse(self.response['bad'])

    def delete(self, request):
        storage_id = request.GET.get('product_id', None)
        try:
            basket = Basket.objects.get(user=request.user, status=0)
            assert BasketProduct.objects.filter(basket__user=request.user, basket_id=basket.id,
                                                storage_id=storage_id).exists()
            BasketProduct.objects.filter(basket_id=basket.id, storage_id=storage_id).delete()
            return JsonResponse(self.response['ok'])
        except (AssertionError, Basket.DoesNotExist):
            return JsonResponse(self.response['bad'], status=400)