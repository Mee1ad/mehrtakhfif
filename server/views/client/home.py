from itertools import groupby
from operator import itemgetter

from django.http import JsonResponse, HttpResponseNotFound

from server.documents import *
from server.serialize import *
from server.utils import *


class Test(View):
    def get(self, request):
        return JsonResponse({"message": "pong"})

    def delete(self, request):
        res = JsonResponse({})
        res = delete_custom_signed_cookie(res, 'x')
        res = delete_custom_signed_cookie(res, 'y')
        return res

    def patch(self, request):
        is_login = get_custom_signed_cookie(request, 'is_login') == 'True'
        res = JsonResponse({})
        return set_custom_signed_cookie(res, 'is_login', not is_login)

    def post(self, request):
        request.user = None
        res = JsonResponse({})
        basket_count = int(request.GET.get('basket_count', get_custom_signed_cookie(request, 'basket_count')))
        res = set_custom_signed_cookie(res, 'basket_count', basket_count+1)
        return res


class NotifTest(View):
    def get(self, request, pk):
        if not request.user.is_superuser:
            return HttpResponseNotFound()
        message = request.GET.get('m')
        title = request.GET.get('t')
        if not pk:
            devices = GCMDevice.objects.all()
            return JsonResponse({'devices': GCMDeviceSchema().dump(devices, many=True)})
        device = GCMDevice.objects.get(pk=pk)
        device.send_message(message, extra={'title': title})
        return JsonResponse({"message": "ok"})


class Init(View):
    @staticmethod
    def get(request):
        res = JsonResponse({})
        if request.user.is_authenticated:
            return set_custom_signed_cookie(res, 'is_login', True)
        return set_custom_signed_cookie(res, 'is_login', False)


class GetSpecialOffer(View):
    def get(self, request):
        special_offer = SpecialOffer.objects.select_related(*SpecialOffer.select).all()
        res = {'special_offer': SpecialOfferSchema().dump(special_offer, many=True)}
        return JsonResponse(res)


class GetSpecialProduct(View):
    def get(self, request):
        special_product = SpecialProduct.objects.select_related(*SpecialProduct.select)[:5]
        res = {'special_product': SpecialProductSchema(**request.schema_params).dump(special_product, many=True)}
        return JsonResponse(res)


class BoxesGetSpecialProduct(View):
    def get_old(self, request):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        all_box = Box.objects.all()
        language = request.lang
        products = []

        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related('thumbnail', 'storage__product__thumbnail') \
                                      .prefetch_related('storage__vip_prices') \
                                      .filter(box=box)[(page - 1) * step:step * page]
            if box_special_product:
                box = {'id': box.pk, 'name': box.name[language], 'key': box.permalink}
                box['special_products'] = SpecialProductSchema(**request.schema_params).dump(box_special_product,
                                                                                             many=True)
                products.append(box)
        res = {'products': products}
        return JsonResponse(res)

    def get(self, request):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        language = request.lang
        special_products = []
        products = SpecialProduct.objects.select_related('thumbnail', 'storage__product__thumbnail', 'box') \
            .prefetch_related('storage__vip_prices')
        products = SpecialProductSchema(**request.schema_params).dump(products, many=True)
        # products = groupby(sorted(products, key=itemgetter('box')), key=itemgetter('box'))
        # for item in products:
        #     special_products.append({**item[0], 'special_products': item[1]})
        for box, event_list in groupby(sorted(products, key=itemgetter('box_id')), itemgetter('box')):
            sp = list(event_list)
            list(map(lambda d: d.pop('box'), sp))
            special_products.append({**box, 'special_products': sp})

            # for e in event_list:
            #     print(e)
        return JsonResponse({'products': sorted(special_products, key=itemgetter('priority'))})


class BestSeller(View):
    def get(self, request):
        all_box = Box.objects.all()
        last_week = add_days(-7)
        boxes = []
        language = request.lang
        invoice_ids = Invoice.objects.filter(created_at__gte=last_week, status=2).values('id')
        for box, index in zip(all_box, range(len(all_box))):
            item = {}
            item['id'] = box.pk
            item['name'] = box.name[language]
            item['key'] = box.permalink
            item['best_seller'] = get_best_seller(request, box, invoice_ids)
            boxes.append(item)
        return JsonResponse({'box': boxes})


class BoxWithCategory(View):
    def get(self, request):
        box_permalink = request.GET.get('permalink', None)
        box_id = request.GET.get('box_id', None)
        box_filter = {'permalink': box_permalink} if box_permalink else {'id': box_id}
        is_admin = False
        if request.headers.get('admin', None):
            is_admin = True
        disable = {}
        try:
            disable = {'disable': False} if not request.user.is_staff else {}
            box = Box.objects.get(**box_filter, **disable)
            categories = get_categories_old(request.lang, box.pk, is_admin=is_admin, disable=disable)
            box = BoxSchema(**request.schema_params, exclude=['children']).dump(box)
            res = {'categories': categories, 'box': box}
        except Box.DoesNotExist:
            boxes = Box.objects.filter(**disable)
            res = {'boxes': BoxSchema(**request.schema_params, exclude=['children']).dump(boxes, many=True)}
        return JsonResponse(res)


class Categories(View):
    def get(self, request):
        all_category = cache.get('categories', None)
        if not all_category:
            all_category = get_categories()
            cache.set('categories', all_category, 3000000)  # about 1 month
        return JsonResponse({'data': all_category})


class GetMenu(View):
    def get(self, request):
        menu = Menu.objects.select_related('media').all()
        return JsonResponse({'menu': MenuSchema(request.lang).dump(menu, many=True)})


class GetAds(View):
    def get(self, request, ads_type):
        agent = request.user_agent
        ads = Ad.objects.filter(priority__isnull=False, type=ads_type).select_related('media')
        return JsonResponse({'ads': AdSchema(is_mobile=agent.is_mobile).dump(ads, many=True)})


class PermalinkToId(LoginRequired):
    # todo admin required
    def get(self, request, permalink):
        try:
            product = Product.objects.get(permalink=permalink)
            return JsonResponse({'id': product.pk, 'disable': product.disable, 'review': product.review})
        except Product.DoesNotExist:
            raise ValidationError('محصول پیدا نشد')


class GetSlider(View):
    def get(self, request, slider_type):
        agent = request.user_agent
        slider = Slider.objects.filter(priority__isnull=False, type=slider_type).select_related('media')
        return JsonResponse({'slider': SliderSchema(is_mobile=agent.is_mobile).dump(slider, many=True)})


class Suggest(View):
    def get(self, request):
        q = request.GET.get('q', '')
        lang = request.lang
        s = ProductDocument.search()
        s = s.query("multi_match", query=q, fields=['name_fa', 'category_fa'])
        products = []
        for hit in s:
            products.append({'name': hit.name_fa, 'permalink': hit.permalink, 'thumbnail': hit.thumbnail})
        return JsonResponse({'products': products})


class ElasticSearch(View):
    def get(self, request):
        q = request.GET.get('q', '')
        p = ProductDocument.search()
        c = CategoryDocument.search()
        t = TagDocument.search()
        p = p.query({"bool": {"should": [{"match": {"name_fa": {"query": q, "boost": 1}}},
                                         {"wildcard": {"name_fa": f"{q}*"}},
                                         {"match": {"name_fa2": {"query": q, "boost": 0.5}}}],
                              "must": [{"match": {"disable": False}}, {"match": {"available": True}}]}})
        c = c.query({"bool": {"should": [{"match": {"name_fa": {"query": q, "boost": 1}}},
                                         {"wildcard": {"name_fa": f"{q}*"}}]}}).query('match', disable=False)
        t = t.query({"bool": {"should": [{"match": {"name_fa": {"query": q, "boost": 1}}},
                                         {"wildcard": {"name_fa": f"{q}*"}},
                                         {"match": {"name_fa2": {"query": q, "boost": 0.5}}}]}})
        products, categories, tags = [], [], []
        for hit in p[:3]:
            product = {'name': hit.name_fa, 'permalink': hit.permalink, 'thumbnail': hit.thumbnail}
            products.append(product)
        for hit in c[:3]:
            category = {'name': hit.name_fa, 'permalink': hit.permalink, 'media': hit.media, 'parent': hit.parent}
            categories.append(category)
        for hit in t[:3]:
            tag = {'name': hit.name_fa, 'permalink': hit.permalink}
            tags.append(tag)
        categories = sorted(categories, key=lambda i: 1 if i['parent'] else 0)
        return JsonResponse({'categories': categories, 'tags': tags, 'products': products})