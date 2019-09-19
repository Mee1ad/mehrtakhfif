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
        slider = Slider.objects.select_related('media').all()
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
        products = []
        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related('storage', 'media').filter(
                box=box).order_by('-created_by')[(page - 1) * step:step * page]
            product = {}
            product['id'] = box.pk
            product['name'] = box.name[request.lang]
            product['special_product'] = SpecialProductSchema(request.lang).dump(box_special_product, many=True)
            best_seller_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
                default=True).order_by('-product__sold_count')[(page - 1) * step:step * page]
            product['best_seller'] = StorageSchema(request.lang).dump(best_seller_storage, many=True)
            products.append(product)
        res = {'products': products}
        return JsonResponse(res)


class GetMenu(Tools):
    def get(self, request):
        return JsonResponse({'menu': MenuSchema(request.lang).dump(
            Menu.objects.select_related('media', 'parent').all(), many=True)})


class Filter(Tools):
    def get(self, request):
        params = self.get_params(request.GET)
        products = Storage.objects.filter(**params)
        return JsonResponse({'products': StorageSchema(language=request.lang).dump(products, many=True)})

    def box_search(self, params):
        box = Storage.objects.filter(**params)


class Search(Tools):
    def get(self, request):
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
        from django.contrib.postgres.fields.jsonb import KeyTextTransform
        from django.contrib.postgres.search import TrigramSimilarity

        sv = SearchVector(KeyTextTransform('persian', 'product__name'),
                          KeyTextTransform('persian', 'product__category__name'))
        sq = SearchQuery("هتل | متل", search_type='raw')

        # product = Storage.objects.annotate(rank=SearchRank(sv, sq)).order_by('rank')\
        #     .values_list(KeyTextTransform('persian', 'product__name'), flat=True)

        product = Product.objects.annotate(
            similarity=TrigramSimilarity(KeyTextTransform('persian', 'name'), 'اگامت')) \
            .values_list(KeyTextTransform('persian', 'name'), flat=True).order_by('similarity')

        print(product)
        print(len(product))
        return HttpResponse(product)
