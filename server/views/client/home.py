from django.http import JsonResponse, HttpResponseNotFound

from server.documents import *
from server.serialize import *
from server.utils import *
import pysnooper
from django.contrib.auth import logout


class Test(View):
    def get(self, request):
        print('old', request.session.get('basket'))
        if request.session.get('basket') is None:
            request.session['basket'] = []
            request.session['basket'].append({'fuck': 'yeah'})
            request.session.save()
        print('new', request.session.get('basket'))

        # print(get_custom_signed_cookie(request, 'y'))
        res = JsonResponse({})
        set_custom_signed_cookie(res, 'x', 'oskole')
        y = 1
        try:
            y = int(get_custom_signed_cookie(request, 'y')) + 1
        except Exception:
            pass
        set_custom_signed_cookie(res, 'y', y)
        return res

    def delete(self, request):
        res = JsonResponse({})
        res = delete_custom_signed_cookie(res, 'x')
        res = delete_custom_signed_cookie(res, 'y')
        return res

    def patch(self, request):
        is_login = get_custom_signed_cookie(request, 'is_login') == 'True'
        res = JsonResponse({})
        return set_custom_signed_cookie(res, 'is_login', not is_login)


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
    @pysnooper.snoop()
    def get(self, request):
        res = JsonResponse({})
        if request.user.is_authenticated:
            res = set_custom_signed_cookie(res, 'is_login', True)
        else:
            res = set_custom_signed_cookie(res, 'is_login', False)
        return res


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
    def get(self, request):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        all_box = Box.objects.all()
        language = request.lang
        products = []

        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related(*SpecialProduct.select).filter(box=box) \
                [(page - 1) * step:step * page]
            if box_special_product:
                box = {'id': box.pk, 'name': box.name[language], 'key': box.permalink}
                box['special_products'] = SpecialProductSchema(**request.schema_params).dump(box_special_product,
                                                                                             many=True)
                products.append(box)
        res = {'products': products}
        return JsonResponse(res)


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
        try:
            disable = {'disable': False} if not request.user.is_staff else {}
            box = Box.objects.get(**box_filter, **disable)
            categories = get_categories(request.lang, box.pk, is_admin=is_admin, disable=disable)
            box = BoxSchema(**request.schema_params).dump(box)
            res = {'categories': categories, 'box': box}
        except Box.DoesNotExist:
            boxes = Box.objects.filter(**disable)
            res = {'boxes': BoxSchema(**request.schema_params).dump(boxes, many=True)}
        return JsonResponse(res)


class GetMenu(View):
    def get(self, request):
        menu = Menu.objects.select_related(*Menu.select).all()
        return JsonResponse({'menu': MenuSchema(request.lang).dump(menu, many=True)})


class GetAds(View):
    def get(self, request, ads_type):
        agent = request.user_agent
        ads = Ad.objects.filter(priority__isnull=False, type=ads_type).select_related(*Ad.select).order_by('priority')
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
        slider = Slider.objects.filter(priority__isnull=False, type=slider_type).select_related(
            *Slider.select).order_by('priority')
        return JsonResponse({'slider': SliderSchema(is_mobile=agent.is_mobile).dump(slider, many=True)})


class ElasticSearch(View):
    def get(self, request):
        q = request.GET.get('q', '')
        lang = request.lang
        s = ProductDocument.search()
        s = s.query("multi_match", query=q, fields=['name_fa', 'category_fa'])
        products = []
        for hit in s:
            products.append({'name': hit.name_fa, 'permalink': hit.permalink, 'thumbnail': hit.thumbnail})
        return JsonResponse({'products': products})


class ElasticSearch2(View):
    def get(self, request):
        q = request.GET.get('q', '')
        lang = request.lang
        p = ProductDocument.search()
        c = CategoryDocument.search()
        t = TagDocument.search()
        p = p.query("multi_match", query=q, fields=['name_fa', 'category_fa'])
        c = c.query("match", name_fa=q)
        t = t.query("match", name_fa=q)
        products, categories, tags = [], [], []
        for hit in p[:3]:
            products.append({'name': hit.name_fa, 'permalink': hit.permalink, 'thumbnail': hit.thumbnail})
        for hit in c[:3]:
            categories.append({'name': hit.name_fa, 'permalink': hit.permalink, 'media': hit.media})
        for hit in t[:3]:
            tags.append({'name': hit.name_fa, 'permalink': hit.permalink})
        return JsonResponse({'products': products, 'categories': categories, 'tags': tags})
