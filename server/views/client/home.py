from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.http import JsonResponse

from server.documents import *
from server.serialize import *
from server.utils import *


class GetSlider(View):
    def get(self, request, slider_type):
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
        special_product = SpecialProduct.objects.select_related(*SpecialProduct.select).filter(special=True)[:5]
        res = {'special_product': SpecialProductSchema(language=request.lang).dump(special_product, many=True)}
        return JsonResponse(res)


class BoxesGetSpecialProduct(View):
    def get(self, request):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        all_box = Box.objects.all()
        language = request.lang
        products = []

        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related(*SpecialProduct.select).filter(box=box) \
                [(page - 1) * step:step * page]
            box = {'id': box.pk, 'name': box.name[language], 'key': box.permalink}
            box['special_products'] = SpecialProductSchema(request.lang).dump(box_special_product, many=True)
            products.append(box)
        res = {'products': products}
        return JsonResponse(res)


class BestSeller(View):
    def get(self, request):
        all_box = Box.objects.all()
        last_week = add_days(-7)
        boxes = []
        language = request.lang
        invoice_ids = Invoice.objects.filter(created_at__gte=last_week, status='payed').values('id')
        for box, index in zip(all_box, range(len(all_box))):
            item = {}
            item['id'] = box.pk
            item['name'] = box.name[language]
            item['key'] = box.permalink
            item['best_seller'] = get_best_seller(box, invoice_ids, request.step, request.page)
            boxes.append(item)
        return JsonResponse({'box': boxes})


class BoxWithCategory(View):
    def get(self, request):
        box_permalink = request.GET.get('box_permalink', None)
        if box_permalink:
            box_id = Box.objects.filter(permalink=box_permalink).first().pk
            categories = get_categories(request.lang, box_id)
            res = {'categories': categories}
        else:
            boxes = Box.objects.all()
            box_list = []
            for box in boxes:
                categories = get_categories(request.lang, box.id)
                box = BoxSchema(language=request.lang).dump(box)
                box['categories'] = categories
                box_list.append(box)
            res = {'boxes': box_list}
        return JsonResponse(res)


class GetMenu(View):
    def get(self, request):
        menu = Menu.objects.select_related(*Menu.select).all()
        return JsonResponse({'menu': MenuSchema(request.lang).dump(menu, many=True)})


class GetAds(View):
    def get(self, request):
        return JsonResponse({'ads': AdSchema(request.lang).dump(
            Ad.objects.select_related(*Ad.select).all(), many=True)})


class Search(View):
    #  py manage.py search_index --rebuild
    def get(self, request):
        q = request.GET.get('q', '')
        sv = SearchVector(KeyTextTransform('fa', 'name'), weight='A')  # + \
        # SearchVector(KeyTextTransform('fa', 'product__category__name'), weight='B')
        sq = SearchQuery(q)
        rank = SearchRank(sv, sq, weights=[0.2, 0.4, 0.6, 0.8])
        products = Product.objects.annotate(rank=rank).order_by('-rank')
        print(products[0])
        products = MinProductSchema(language=request.lang).dump(products, many=True)
        return JsonResponse({'products': products})


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
