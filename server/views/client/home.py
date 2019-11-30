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
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.contrib.postgres.search import TrigramSimilarity
from mehr_takhfif.settings import HOST, MEDIA_ROOT


class Test(View):
    @pysnooper.snoop()
    def get(self, request):
        l = {}


class GetSlider(View):
    def get(self, request):
        slider = Slider.objects.select_related('media').all()
        res = {'slider': SliderSchema(
            language='english').dump(slider, many=True)}
        return JsonResponse(res)


class GetSpecialOffer(View):
    def get(self, request):
        special_offer = SpecialOffer.objects.select_related('media').all()
        res = {'special_offer': SpecialOfferSchema().dump(
            special_offer, many=True)}
        return JsonResponse(res)


class GetSpecialProduct(View):
    def get(self, request):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        special_product = SpecialProduct.objects.select_related(
            'storage', 'storage__product', 'media').all().order_by('-id')[(page - 1) * step:step * page]
        best_sell_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
            default=True).order_by('-product__sold_count')[(page - 1) * step:step * page]
        res = {'special_product': SpecialProductSchema(language=request.lang).dump(special_product, many=True),
               'best_sell_product': StorageSchema().dump(best_sell_storage, many=True)}
        return JsonResponse(res)


class AllSpecialProduct(View):
    def get(self, request):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        all_box = Box.objects.all()
        products = []
        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related('storage', 'media').filter(
                box=box).order_by('-created_by')[(page - 1) * step:step * page]
            product = {}
            product['id'] = box.pk
            product['name'] = box.name[request.lang]
            product['key'] = box.meta_key
            # product['special_product'] = SpecialProductSchema(request.lang).dump(box_special_product, many=True)
            best_seller_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
                default=True, box=box).order_by('-product__sold_count')[(page - 1) * step:step * page]
            product['best_seller'] = StorageSchema(
                request.lang).dump(best_seller_storage, many=True)
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
            Menu.objects.select_related('media', 'parent').all(), many=True)}))


class GetAds(View):
    def get(self, request):
        return JsonResponse({'ads': AdSchema(request.lang).dump(
            Ad.objects.select_related('media', 'storage').all(), many=True)})


class GetProducts(View):
    def post(self, request):
        try:
            assert not request.user.is_authenticated  # must be guest
            data = json.loads(request.body)
            products_id = [product['id'] for product in data['products']]
            products = Storage.objects.filter(id__in=products_id) \
                .select_related('product', 'category', 'product__box', 'product__thumbnail')\
                .prefetch_related('product__media')
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
        sv = SearchVector(KeyTextTransform('persian', 'product__name'), KeyTextTransform('persian', 'product__category__name'))
        sq = SearchQuery(q)
        print(sq)
        product = Storage.objects.select_related('product').annotate(rank=SearchRank(sv, sq)).order_by('-rank').filter(rank__gte=0.01)
        print(product)
        product = StorageSchema(request.lang).dump(product, many=True)
        return JsonResponse({'products': product})
