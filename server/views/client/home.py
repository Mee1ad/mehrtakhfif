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
        all_category = cache.get('categories', None)
        if not all_category:
            all_category = get_categories({"parent_id": None})
            cache.set('categories', all_category, 3000000)  # about 1 month
        return JsonResponse({'data': all_category})


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


class ClientSlider(View):
    def get(self, request, slider_type):
        agent = request.user_agent
        slider = Slider.objects.filter(priority__isnull=False, type=slider_type).select_related('media')
        return JsonResponse({'slider': SliderSchema(is_mobile=agent.is_mobile).dump(slider, many=True)})


class ElasticSearch(View):
    def get(self, request):
        q = request.GET.get('q', '')
        p = ProductDocument.search()
        c = CategoryDocument.search()
        t = TagDocument.search()
        p = p.query({"bool": {"should": [{"match": {"name_fa": {"query": q, "boost": 1}}},
                                         {"wildcard": {"name_fa": f"{q}*"}},
                                         {"match": {"name_fa2": {"query": q, "boost": 1}}}],
                              "must": [{"match": {"disable": False}}, {"match": {"available": True}}]}})

        # p = p.query({"bool": {"should": [{"match": {"name_fa2": {"query": q, "boost": 1}}}]}})

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
