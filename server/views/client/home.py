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
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity, TrigramDistance
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from mehr_takhfif.settings import HOST, MEDIA_ROOT
from server.documents import *


class Test(View):
    # @pysnooper.snoop()
    def get(self, request):

        # a = ProductDocument.search().query("match", name="gym")
        # print(a)

        return HttpResponse('ok')

    def cl(self):
        l = {}
        for i in range(100000):
            l[f'bb{i}'] = i + 5
        return l


class GetSlider(View):
    def get(self, request):
        slider = Slider.objects.select_related(*Slider.select).all()
        res = {'slider': SliderSchema().dump(slider, many=True)}
        return JsonResponse(res)


class GetSpecialOffer(View):
    def get(self, request):
        special_offer = SpecialOffer.objects.select_related(*SpecialOffer.select).all()
        res = {'special_offer': SpecialOfferSchema().dump(special_offer, many=True)}
        return JsonResponse(res)


class GetSpecialProduct(View):
    def get(self, request):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))

        special_products = SpecialProduct.objects.select_related(*SpecialProduct.min_select).all()\
            [(page - 1) * step:step * page]
        serialized_products = MinSpecialProductSchema(language=request.lang).dump(special_products, many=True)
        for product, serialized_product in zip(special_products, serialized_products):
            if product.product: # else has link
                serialized_product['permalink'] = product.product.permalink
                serialized_product['default_storage'] = MinStorageSchema().dump(product.product.default_storage)

        # best_seller = Product.objects.select_related(*Product.select) \
        #                   .filter(verify=True).order_by('-sold_count')[(page - 1) * step:step * page]

        res = {'special_product': serialized_products}
               # 'best_sell_product': MinProductSchema().dump(best_seller, many=True)}
        return JsonResponse(res)


class AllSpecialProduct(View):
    def get(self, request):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        all_box = Box.objects.all()
        products = []
        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related(*SpecialProduct.select)\
                                    .filter( box=box)[(page - 1) * step:step * page]
            product = {}
            product['id'] = box.pk
            product['name'] = box.name[request.lang]
            product['key'] = box.meta_key
            # product['special_product'] = SpecialProductSchema(request.lang).dump(box_special_product, many=True)
            # best_seller_storage = Storage.objects.select_related(*Storage.select)\
            #                           .filter(default=True, box=box).order_by('-product__sold_count')\
            #                             [(page - 1) * step:step * page]

            best_seller = Product.objects.select_related(*Product.select) \
                              .filter(verify=True, box=box).order_by('-sold_count')[(page - 1) * step:step * page]
            product['best_seller'] = MinProductSchema(request.lang).dump(best_seller, many=True)
            products.append(product)
        res = {'products': products}
        return JsonResponse(res)


class AllCategory(View):
    def get(self, request):
        categories = get_categories()
        return JsonResponse(categories)


class GetMenu(View):
    def get(self, request):
        return JsonResponse(json.dumps({'menu': MenuSchema(request.lang).dump(
            Menu.objects.select_related(*Menu.select).all(), many=True)}))


class GetAds(View):
    def get(self, request):
        return JsonResponse({'ads': AdSchema(request.lang).dump(
            Ad.objects.select_related(*Ad.select).all(), many=True)})


class GetProducts(View):
    def post(self, request):
        try:
            assert not request.user.is_authenticated  # must be guest
            data = json.loads(request.body)
            products_id = [product['id'] for product in data['products']]
            products = Storage.objects.filter(id__in=products_id).select_related(*Storage.select)\
                .prefetch_related(*Storage.prefetch)
            basket_products = []
            address_required = False

            for product in products:
                item = next(item for item in data['products'] if item["id"] == product.pk)
                count = item['count']
                obj = BasketProduct(storage=product, count=count)
                basket_products.append(obj)
            products = BasketProductSchema().dump(basket_products, many=True)
            for product in products:
                if product['product']['product']['type'] == 'product':
                    address_required = True
                    break
            profit = calculate_profit(basket_products)
            return JsonResponse({'basket': {'products': products}, 'summary': profit,
                                 'address_required': address_required})
        except AssertionError:
            return JsonResponse({}, status=400)


class Search(View):
    def get(self, request):
        q = request.GET.get('q', '')
        sv = SearchVector(KeyTextTransform('persian', 'product__name'), weight='A') # + \
             # SearchVector(KeyTextTransform('persian', 'product__category__name'), weight='B')
        sq = SearchQuery(q)
        rank = SearchRank(sv, sq, weights=[0.2, 0.4, 0.6, 0.8])
        product = Storage.objects.select_related(*Storage.select).annotate(rank=rank)\
            .filter(rank__gt=0).order_by('-rank')
        for p in product:
            print(p.rank)
        product = StorageSchema(request.lang).dump(product, many=True)
        return JsonResponse({'products': product})


class ElasticSearch(View):
    def get(self, request):
        q = request.GET.get('q', '')
        lang = request.lang
        s = ProductDocument.search()
        s = s.query("multi_match", query=q, fields=['name_fa^3', 'category_fa^1'])
        products = []
        for hit in s.scan():
            product = {'name': hit.name_fa, 'thumbnail': hit.thumbnail}
            products.append(product)
        return JsonResponse({'products': products})