from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server import serializer as serialize
from server.views.utils import Tools
from server.views.admin_panel.read import ReadAdminView
import json
import time
import pysnooper
from django.views.decorators.cache import cache_page
from django.db.models import Max, Min
from server.serialize import *


class GetSpecialOffer(Tools):
    def get(self, request, name):
        special_offer = SpecialOffer.objects.select_related('media').filter(box__name__persian=name).order_by('-id')
        res = {'special_product': SpecialProductSchema(language=request.lang).dump(special_offer, many=True)}
        return JsonResponse(res)


class BoxDetail(Tools):
    def get(self, request, pk):
        max_price = Storage.objects.filter(box_id=pk).aggregate(Max('discount_price'))['discount_price__max']
        min_price = Storage.objects.filter(box_id=pk).aggregate(Min('discount_price'))['discount_price__min']
        box = Box.objects.filter(pk=pk).first()
        categories = Category.objects.select_related('media', 'parent').filter(
            box_id=pk, deactive=False).order_by('-priority')
        return JsonResponse({'box': BoxSchema(request.lang).dump(box), 'max_price': max_price, 'min_price': min_price,
                             'categories': CategorySchema(request.lang).dump(categories, many=True)})


class BoxView(Tools):
    def get(self, request, name):
        step = int(request.GET.get('s', self.step))
        page = int(request.GET.get('p', self.page))
        params = self.get_params(request.GET)
        print(params)
        box = Box.objects.filter(meta_key=name).first()
        latest = Storage.objects.filter(box=box, **params).select_related(
            'product', 'product__thumbnail').order_by('-updated_by')[(page-1)*step:step*page]
        return JsonResponse({'latest': StorageSchema(request.lang).dump(latest, many=True),
})


class BoxCategory(Tools):
    def get(self, request, pk):
        step = int(request.GET.get('s', self.step))
        page = int(request.GET.get('e', self.page))
        storage = Storage.objects.filter(category_id=pk).select_related(
                'product', 'product__thumbnail').order_by('-updated_at')[(page-1)*step:step*page]
        special_products = SpecialProduct.objects.filter(category_id=pk).select_related('storage')
        return JsonResponse({'products': serialize.storage(storage, True),
                             'special_products': serialize.special_product(special_products, True)})


class TagView(Tools):
    def get(self, request, pk):
        step = int(request.GET.get('s', self.step))
        page = int(request.GET.get('p', self.page))
        tag = Tag.objects.filter(pk=pk).first()
        products = tag.product.all().order_by('created_at')[(page-1)*step:step*page]
        return JsonResponse({'products': serialize.product(products)})
