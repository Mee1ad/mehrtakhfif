from django.db.models import Max, Min
from django.http import JsonResponse
from server.utils import *
from server.serialize import BoxSchema, FeatureSchema, MinProductSchema, BrandSchema
import pysnooper

class GetSpecialOffer(View):
    def get(self, request, name):
        special_offer = SpecialOffer.objects.select_related('media').filter(box__meta_key=name).order_by('-id')
        res = {'special_product': SpecialProductSchema(language=request.lang).dump(special_offer, many=True)}
        return JsonResponse(res)


class GetSpecialProduct(View):
    def get(self, request, permalink):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        special_products = SpecialProduct.objects.filter(box__permalink=permalink) \
                               .select_related(*SpecialProduct.min_select)[(page - 1) * step:step * page]
        special_products = MinSpecialProductSchema(language=request.lang).dump(special_products, many=True)
        return JsonResponse({'special_product': special_products})


class FilterDetail(View):
    def get(self, request):
        permalink = request.GET.get('b', None)
        q = request.GET.get('q', {})
        box = {}
        product_box = {}
        rank = {}
        res = {'box': None}
        if q:
            rank = get_rank(q, request.lang, 'product__name')
            rank = {'rank': rank}
        if permalink:
            res['box'] = Box.objects.filter(permalink=permalink).first()
            box = {'box': res['box']}
            product_box = {'product__box': res['box']}
            res['box'] = BoxSchema(request.lang).dump(res['box'])
        max_price = Storage.objects.annotate(**rank).filter(**product_box).aggregate(Max('discount_price'))['discount_price__max']
        min_price = Storage.objects.annotate(**rank).filter(**product_box).aggregate(Min('discount_price'))['discount_price__min']
        categories = get_categories(request.lang, box.get('box', None))
        brands = Brand.objects.filter(**box)
        return JsonResponse({'max_price': max_price, 'brands': BrandSchema(request.lang).dump(brands, many=True),
                             'min_price': min_price, 'categories': categories, **res})


class Filter(View):
    @pysnooper.snoop()
    def get(self, request):
        params = filter_params(request.GET, request.lang)
        products = Product.objects.annotate(**params['rank']).\
            filter(verify=True, **params['filter']).order_by(params['order'])
        pg = get_pagination(products, request.step, request.page, MinProductSchema)
        return JsonResponse(pg)


class GetFeature(View):
    def get(self, request):
        box_permalink = request.GET.get('box', None)
        category_permalink = request.GET.get('category', None)
        try:
            if box_permalink:
                box = Box.objects.filter(permalink=box_permalink).first()
                features = Feature.objects.filter(box=box)
            else:
                category = Category.objects.filter(permalink=category_permalink).prefetch_related(
                    *Category.prefetch).first()
                features = category.feature_set.all()
            features = FeatureSchema(language=request.lang).dump(features, many=True)
            return JsonResponse({'feature': features})
        except Exception:
            return JsonResponse({}, status=400)


class BestSeller(View):
    def get(self, request, permalink):
        box = Box.objects.get(permalink=permalink)
        last_week = add_days(-7)
        language = request.lang
        invoice_ids = Invoice.objects.filter(created_at__gte=last_week, status='payed').values('id')
        best_seller = get_best_seller(box, invoice_ids, request.step, request.page)
        return JsonResponse({'best_seller': best_seller})


class TagView(View):
    def get(self, request, permalink):
        tag = Tag.objects.filter(permalink=permalink).first()
        products = tag.product_set.all()
        pg = get_pagination(products, request.step, request.page, MinProductSchema)
        return JsonResponse(pg)


class CategoryView(View):
    def get(self, request, permalink):
        category = Category.objects.filter(permalink=permalink).first()
        products = Product.objects.filter(category=category)
        pg = get_pagination(products, request.step, request.page, MinProductSchema)
        return JsonResponse(pg)
