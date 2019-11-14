from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server.views.utils import *
from server.views.admin_panel.read import ReadAdminView
import json
import time
import pysnooper
from django.views.decorators.cache import cache_page
from django.db.models import Max, Min
from server.serialize import *
import math


class GetSpecialOffer(View):
    def get(self, request, name):
        special_offer = SpecialOffer.objects.select_related('media').filter(box__meta_key=name).order_by('-id')
        res = {'special_product': SpecialProductSchema(language=request.lang).dump(special_offer, many=True)}
        return JsonResponse(res)


class BoxDetail(View):
    def get(self, request, key):
        try:
            box = Box.objects.filter(meta_key=key).first()
            max_price = Storage.objects.filter(box=box).aggregate(Max('discount_price'))['discount_price__max']
            min_price = Storage.objects.filter(box=box).aggregate(Min('discount_price'))['discount_price__min']
            categories = get_categories(box)
            return JsonResponse({'box': BoxSchema(request.lang).dump(box), 'max_price': max_price,
                                 'min_price': min_price, 'categories': categories})
        except Exception:
            return JsonResponse({}, status=400)


class BoxView(View):
    def get(self, request, name='all'):
        params = filter_params(request.GET)
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('p', default_page))
        try:
            box = Box.objects.get(meta_key=name)
            query = {'box': box}
        except Box.DoesNotExist:
            box = Box.objects.all()
            query = {'box__in': box}
        query = Storage.objects.filter(**query, **params['filter'])
        latest = query.select_related('product', 'product__thumbnail').order_by(
            *params['order'])[(page-1)*step:step*page]
        return JsonResponse({'data': StorageSchema(request.lang).dump(latest, many=True),
                             'current_page': page, 'last_page': last_page(query, step)})


class BoxCategory(View):
    def get(self, request, box, category):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        cat = Category.objects.filter(meta_key=category).first()
        storage = Storage.objects.filter(box__meta_key=box, category__meta_key=category).select_related(
                'product', 'product__thumbnail').order_by('-updated_at')[(page-1)*step:step*page]
        # special_products = SpecialProduct.objects.filter(category_id=pk).select_related('storage')
        # return JsonResponse({'products': serialize.storage(storage, True)})
        return JsonResponse({'category': CategorySchema(request.lang).dump(cat)})
        # 'special_products': serialize.special_product(special_products, True)}


class TagView(View):
    def get(self, request, pk):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        tag = Tag.objects.filter(pk=pk).first()
        products = tag.product.all().order_by('created_at')[(page-1)*step:step*page]
        return JsonResponse({'products': TagSchema().dump(products, many=True)})


class Filter(View):
    def get(self, request):
        params = filter_params(request.GET)
        print(params)
        try:
            products = Storage.objects.filter(**params['filter']).order_by(*params['order'])
        except Exception:
            products = Storage.objects.all().order_by('-created_at')
        return JsonResponse({'products': StorageSchema(language=request.lang).dump(products, many=True)})