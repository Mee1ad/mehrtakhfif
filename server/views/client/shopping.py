from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server import serializer as serialize
from server.views.mylib import Tools
from server.views.admin_panel.read import ReadAdminView
import json
import time
import pysnooper
from django.views.decorators.cache import cache_page
from django.db.models import Max, Min
from server.serialize import *



class Buy(Tools):
    def get(self, request):
        basket_id = request.GET.get('basket_id', None)
        basket = Basket.objects.filter(user=1, pk=basket_id).first()
        products = [item for item in basket.products.all()]
        # products = Storage.objects.filter(product__in=products)
        products = Storage.objects.filter(product__in=basket.products.all())
        basket = serialize.basket(basket)
        basket['products'] = serialize.storage(products, array=True)
        return JsonResponse({'basket': basket})

    def post(self, request):
        data = json.loads(request.body)
        basket = Basket(user_id=request.user, count=data['count'], description=data['description'],
                        created_by_id=request.user, updated_by_id=request.user, product=data['product'])
        basket.save()
        return JsonResponse({'basket_id': basket.pk})

    def put(self, request):
        data = json.loads(request.body)
        basket = Basket.objects.get(pk=data['basket_id'])
        storage = Storage.objects.filter(pk=data['storage_id'])
        basket.product.add(storage)
        return HttpResponse('ok')