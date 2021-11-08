from itertools import groupby
from operator import itemgetter

from django.http import JsonResponse, HttpResponseNotFound

from server.documents import *
from server.serialize import *
from server.utils import *
from elasticsearch_dsl import Search

from mehr_takhfif.settings import ES_CLIENT


class PingView(View):
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
        res = set_custom_signed_cookie(res, 'basket_count', basket_count + 1)
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
    def get(self, request):
        res = self.set_basket_count_cookie(request)
        res = self.set_login_cookie(request.user, res)
        return res

    @staticmethod
    def set_basket_count_cookie(request, res=None):
        if res is None:
            res = JsonResponse({})
        new_basket_count = None
        user_basket_count = get_custom_signed_cookie(request, 'basket_count', -1)

        try:
            db_basket_count = request.user.basket_count
        except AttributeError:
            db_basket_count = get_basket_count(session=request.session)

        if db_basket_count != user_basket_count:
            new_basket_count = db_basket_count

        if new_basket_count:
            return set_custom_signed_cookie(res, 'basket_count', new_basket_count)
        return res

    @staticmethod
    def set_login_cookie(user, res=None):
        if res is None:
            res = JsonResponse({})
        if user.is_authenticated:
            return set_custom_signed_cookie(res, 'is_login', True)
        return set_custom_signed_cookie(res, 'is_login', False)


class ClientSpecialOffer(View):
    def get(self, request):
        special_offer = SpecialOffer.objects.select_related(*SpecialOffer.select).all()
        res = {'special_offer': SpecialOfferSchema().dump(special_offer, many=True)}
        return JsonResponse(res)


class LimitedSpecialProduct(View):
    def get(self, request):
        today = timezone.now()
        selected_date = DateRange.objects.filter(start_date__lte=today, end_date__gte=today).first()
        products = SpecialProduct.objects.filter(date_id=selected_date.id) \
            .select_related('thumbnail', 'storage__product__thumbnail', 'category') \
            .prefetch_related('storage__vip_prices')
        products = SpecialProductSchema(**request.schema_params).dump(products, many=True)
        return JsonResponse({'products': products})


class ClientSpecialProduct(View):
    def get(self, request):
        special_products = []
        products = SpecialProduct.objects.filter(category__isnull=False) \
            .select_related('thumbnail', 'storage__product__thumbnail', 'category') \
            .prefetch_related('storage__vip_prices')
        products = SpecialProductSchema(**request.schema_params).dump(products, many=True)
        for category, event_list in groupby(sorted(products, key=itemgetter('category_id')), itemgetter('category')):
            sp = list(event_list)
            list(map(lambda d: d.pop('category'), sp))
            special_products.append({**category, 'special_products': sp})
        return JsonResponse({'products': sorted(special_products, key=itemgetter('priority'))})


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
        res = cache.get('home-categories', {})
        if not res:
            all_category = get_categories({"parent_id": None})
            for category_type, categories in groupby(sorted(all_category, key=itemgetter('type')), itemgetter('type')):
                res[category_type] = list(categories)
            cache.set('home-categories', res, 3000000)  # about 1 month
        return JsonResponse(res)


class PromotedCategories(View):
    def get(self, request):
        categories = Category.objects.filter(promote=True)
        categories = CategorySchema().dump(categories, many=True)
        res = {}
        for category_type, categories in groupby(sorted(categories, key=itemgetter('type')), itemgetter('type')):
            res[category_type] = list(categories)
        return JsonResponse(res)


class ClientMenu(View):
    def get(self, request):
        menu = Menu.objects.select_related('media').all()
        return JsonResponse({'menu': MenuSchema(request.lang).dump(menu, many=True)})


class ClientAds(View):
    def get(self, request):
        agent = request.user_agent
        preview = get_preview_permission(request.user, category_check=False, box_check=False)
        ads = Media.objects.filter(priority__isnull=False, type=5, **preview).order_by('-priority')[:7]
        if agent.is_mobile:
            ads = Media.objects.filter(priority__isnull=False, type=6, **preview).order_by('-priority')[:7]
        return JsonResponse({'ads': AdsSchema().dump(ads, many=True)})


class PermalinkToId(LoginRequired):
    # todo admin required
    def get(self, request, permalink):
        try:
            product = Product.objects.get(permalink=permalink)
            return JsonResponse({'id': product.pk, 'disable': product.disable, 'review': product.review})
        except Product.DoesNotExist:
            raise ValidationError('محصول پیدا نشد')


class ClientSlider(View):
    def get(self, request):
        agent = request.user_agent
        preview = get_preview_permission(request.user, category_check=False, box_check=False)
        sliders = Media.objects.filter(priority__isnull=False, type=4, **preview).order_by('-priority')[:5]
        if agent.is_mobile:
            sliders = Media.objects.filter(priority__isnull=False, type=8, **preview).order_by('-priority')[:5]
        return JsonResponse({'slider': AdsSchema().dump(sliders, many=True)})


class ElasticSearch(View):
    def get(self, request):
        q = request.GET.get('q', '')
        p = Search(using=ES_CLIENT, index="product")
        # category_index = Search(using=ES_CLIENT, index="category")
        c = CategoryDocument.search()
        product_query = {"query": {"bool": {"should": [{"match": {"name_fa": {"query": q, "boost": 1}}},
                                                       {"wildcard": {"name_fa": f"{q}*"}},
                                                       {"match": {"name_fa2": {"query": q, "boost": .2}}}],
                                            "must": [{"match": {"disable": False}}, {"match": {"available": True}}]}},
                         "min_score": 5}
        p = p.from_dict(product_query)[:3]

        #
        category_search_result = c.query({"bool": {"should": [{"match": {"name_fa": {"query": q, "boost": 5}}},
                                                              {"wildcard": {"name_fa": f"{q}*"}}]}}).query('match',
                                                                                                           disable=False)
        # category_query = {"query": {"bool": {"should": [{"match": {"name_fa": {"query": q, "boost": 5}}},
        #                                                 {"wildcard": {"name_fa": f"{q}*"}}],
        #                             "must": [{"match": {"disable": False}}]}}, "min_score": 5}
        # category_search_result = category_index.from_dict(category_query)[:3]
        t = Search(using=ES_CLIENT, index="tag")
        tag_query = {"query": {"bool": {"should": [{"match": {"name_fa": {"query": q, "boost": 1}}},
                                                   {"wildcard": {"name_fa": f"{q}*"}},
                                                   {"match": {"name_fa2": {"query": q, "boost": 0.2}}}]}},
                     "min_score": 5}
        t = t.from_dict(tag_query)[:3]
        products, categories, tags = [], [], []
        for hit in p[:3]:
            product = {'name': hit.name_fa, 'permalink': hit.permalink, 'thumbnail': hit.thumbnail}
            products.append(product)
        for hit in category_search_result[:3]:
            category = {'name': hit.name_fa, 'permalink': hit.permalink, 'parent': hit.parent}
            categories.append(category)
        for hit in t[:3]:
            tags.append(hit.name_fa)
        categories = sorted(categories, key=lambda i: 1 if i['parent'] else 0)
        return JsonResponse({'categories': categories, 'tags': tags, 'products': products})
