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


class GetSlider(Tools):
    def get(self, request):
        # step = request.GET.get('type', None)
        # step = request.GET.get('type', None)
        params = request.GET
        print(type(params))
        p = {}
        for key in params.keys():
            value = params.getlist(key)
            if len(value) == 1:
                p[key] = value[0]
                continue
            p[key[:-2]] = value
        print(p)
        param_dict = request.GET.dict()
        slider = Slider.objects.select_related('media').filter(**p)
        res = {'slider': SliderSchema(language='english').dump(slider, many=True)}
        return JsonResponse(res)


class GetSpecialOffer(Tools):
    def get(self, request):
        special_offer = SpecialOffer.objects.select_related('media').all()
        res = {'special_offer': SpecialOfferSchema().dump(special_offer, many=True)}
        return JsonResponse(res)


class GetSpecialProduct(Tools):
    def get(self, request):
        page = self.page
        step = self.step
        special_product = SpecialProduct.objects.select_related(
            'storage', 'storage__product', 'media').all().order_by('-id')[(page - 1) * step:step * page]
        best_sell_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
            default=True).order_by('-product__sold_count')[(page - 1) * step:step * page]
        res = {'special_product': SpecialProductSchema(language=request.lang).dump(special_product, many=True),
               'best_sell_product': StorageSchema().dump(best_sell_storage, many=True)}
        return JsonResponse(res)


class AllSpecialProduct(Tools):
    def get(self, request):
        page = self.page
        step = self.step
        all_box = Box.objects.all()
        special_products = {}
        best_seller = {}
        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related('storage', 'media').filter(
                box=box).order_by('-created_by')[(page - 1) * step:step * page]

            special_products['items'] = SpecialProductSchema(request.lang).dump(box_special_product, many=True)
            best_seller_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
                default=True).order_by('-product__sold_count')[(page - 1) * step:step * page]
            best_seller['id'] = box.pk
            best_seller['name'] = box.name[request.lang]
            best_seller['items'] = StorageSchema(request.lang).dump(best_seller_storage, many=True)
        res = {'box_special_product': special_products, 'best_seller': best_seller}
        return JsonResponse(res)


class GetMenu(Tools):
    def get(self, request):
        return JsonResponse({'menu': MenuSchema(request.lang).dump(
            Menu.objects.select_related('media', 'parent').all(), many=True)})


class Search(Tools):
    def get(self, request):
        pass
