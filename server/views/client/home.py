import json

from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.http import JsonResponse
import pysnooper

from server.documents import *
from server.serialize import *
from server.views.utils import *


def func():
    State(id=34, name='fuuuuuuuuuuuuuuunc').save()
    return 'fuck yeah'


class Test(View):
    def get(self, request):
        # django_rq.enqueue(func)   
        # scheduler = django_rq.get_scheduler('schedule')
        # job2 = scheduler.enqueue_in(timedelta(minutes=5), fuckingtest, 12)
        # scheduler.enqueue_in(timedelta(minutes=2), func)
        return JsonResponse({})


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
        all_box = Box.objects.all()
        language = request.lang
        products = []

        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related(*SpecialProduct.select) \
                                      .filter(box=box)[(page - 1) * step:step * page]
            product = {}
            product['id'] = box.pk
            product['name'] = box.name[language]
            product['key'] = box.permalink
            # product['special_product'] = SpecialProductSchema(request.lang).dump(box_special_product, many=True)
            # best_seller_storage = Storage.objects.select_related(*Storage.select)\
            #                           .filter(default=True, box=box).order_by('-product__sold_count')\
            #                             [(page - 1) * step:step * page]

            products.append(product)
        res = {'products': products}
        return JsonResponse(res)


class BestSeller(View):
    def get(self, request):
        all_box = Box.objects.all()
        last_week = add_days(-7)
        boxes = []
        language = request.lang
        basket_ids = Invoice.objects.filter(created_at__gte=last_week, status='payed').values('basket')
        for box, index in zip(all_box, range(len(all_box))):
            item = {}
            item['id'] = box.pk
            item['name'] = box.name[language]
            item['key'] = box.permalink
            item['best_seller'] = get_best_seller(box, basket_ids, language)
            boxes.append(item)
        return JsonResponse({'box': boxes})


class AllBoxWithCategories(View):
    def get(self, request):
        boxes = Box.objects.all()
        box_list = []
        for box in boxes:
            categories = get_categories(request.lang, box.id)
            box = BoxSchema(language=request.lang).dump(box)
            box['categories'] = categories
            box_list.append(box)
        return JsonResponse({'boxes': box_list})


class AllCategory(View):
    def get(self, request):
        box_id = request.GET.get('box_id', None)
        if box_id is None:
            box_permalink = request.GET.get('box_permalink', None)
            box_id = None
            if box_permalink:
                box_id = Box.objects.filter(permalink=box_permalink).first().pk
        categories = get_categories(request.lang, box_id)
        return JsonResponse({'categories': categories})


class GetMenu(View):
    def get(self, request):
        menu = Menu.objects.select_related(*Menu.select).all()
        return JsonResponse({'menu': MenuSchema(request.lang).dump(menu, many=True)})


class GetAds(View):
    def get(self, request):
        return JsonResponse({'ads': AdSchema(request.lang).dump(
            Ad.objects.select_related(*Ad.select).all(), many=True)})


class GetProducts(View):
    def post(self, request):
        data = json.loads(request.body)
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
        return JsonResponse({'products': products, 'profit': profit, 'address_required': address_required})


class Search(View):
    #  py manage.py search_index --rebuild
    def get(self, request):
        q = request.GET.get('q', '')
        sv = SearchVector(KeyTextTransform('persian', 'product__name'), weight='A')  # + \
        # SearchVector(KeyTextTransform('persian', 'product__category__name'), weight='B')
        sq = SearchQuery(q)
        rank = SearchRank(sv, sq, weights=[0.2, 0.4, 0.6, 0.8])
        product = Storage.objects.select_related(*Storage.select).annotate(rank=rank) \
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
        s = s.query("multi_match", query=q, fields=['name_fa', 'category_fa'])
        products = []
        for hit in s:
            product = {'name': hit.name_fa, 'thumbnail': hit.thumbnail}
            products.append(product)
        return JsonResponse({'products': products})
