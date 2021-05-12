from django.db.models import Max, Min
from django.db.models import Prefetch
from django.http import JsonResponse

from server.serialize import BoxSchema, FeatureSchema, BrandSchema, SpecialProductSchema
from server.utils import *


class GetSpecialOffer(View):
    def get(self, request, name):
        special_offer = SpecialOffer.objects.select_related('media').filter(box__meta_key=name).order_by('-id')
        res = {'special_product': SpecialProductSchema(**request.schema_params).dump(special_offer, many=True)}
        return JsonResponse(res)


class GetSpecialProduct(View):
    def get(self, request, permalink):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        special_products = SpecialProduct.objects.filter(box__permalink=permalink) \
                               .select_related(*SpecialProduct.select)[(page - 1) * step:step * page]
        special_products = SpecialProductSchema(**request.schema_params).dump(special_products, many=True)
        return JsonResponse({'special_product': special_products})


class FilterDetail(View):

    def get(self, request):
        box_permalink = request.GET.get('b', None)
        q = request.GET.get('q', {})
        category_permalink = request.GET.get('cat', None)
        filter_by = {}
        rank = {}
        res = {'box': None}
        order_by = []
        disable = {'disable': False} if not request.user.is_staff else {}
        cat_filter_by = {}
        if box_permalink:
            filter_by['box'] = Box.objects.get(permalink=box_permalink, **disable)
            cat_filter_by['box'] = filter_by['box']
            res['box'] = BoxSchema(**request.schema_params).dump(filter_by['box'])
        if category_permalink:
            category = Category.objects.get(permalink=category_permalink, **disable)
            filter_by['categories'] = category
            cat_filter_by['box'] = category.box
            res['box'] = BoxSchema(**request.schema_params).dump(category.box)
        categories = Category.objects.filter(**cat_filter_by, **disable).select_related('media', 'parent')
        if q:
            rank = get_rank(q, request.lang)
            rank = {'rank': rank}
            order_by = ['-rank']
        products = Product.objects.annotate(**rank).filter(**filter_by, **disable).order_by(*order_by). \
            select_related('brand', 'default_storage').only('brand', 'categories', 'default_storage', 'name')
        if not products:
            return JsonResponse({'max_price': 0, 'min_price': 0, 'brands': [],
                                 'categories': [], 'breadcrumb': [], 'colors': []})
        if q:
            categories = Category.objects.filter(
                pk__in=list(filter(None, set(products.values_list('categories', flat=True)))),
                **disable).select_related('media', 'parent')
        prices = products.aggregate(max=Max('default_storage__discount_price'),
                                    min=Min('default_storage__discount_price'))
        categories = get_categories(request.lang, categories=categories)
        brands = [product.brand for product in products.order_by('brand_id').distinct('brand_id') if product.brand]
        breadcrumb = self.get_breadcrumb(category_permalink)
        colors = get_colors_hex(products)
        return JsonResponse({'max_price': prices['max'], 'min_price': prices['min'], **res,
                             'brands': BrandSchema(**request.schema_params).dump(brands, many=True),
                             'categories': categories, 'breadcrumb': breadcrumb, 'colors': colors})

    def get_breadcrumb(self, category_permalink, lang='fa'):
        breadcrumb = []
        if not category_permalink:
            return breadcrumb
        category = None
        while True:
            if not breadcrumb:
                category = Category.objects.get(permalink=category_permalink)
            try:
                breadcrumb.insert(0, {'permalink': category.permalink, 'name': category.name[lang]})
                category = category.parent
            except AttributeError:
                return breadcrumb


class Filter(View):
    def get(self, request):
        new_params = {'fv': 'product_features__feature_value_id', 'b': 'box__permalink',
                      'cat': 'categories__permalink', 'tag': 'tags__permalink',
                      'available': 'storages__available_count_for_sale__gte', 'brand': 'brand__in'}
        params = filter_params(request.GET, new_params, request.lang)
        query = Q(verify=True, **params['filter'])
        disable = get_product_filter_params(request.user.is_staff)
        if params['related']:
            query = Q(verify=True, **params['filter']) | Q(verify=True, **params['related'])
        products = Product.objects.filter(query, Q(**disable), ~Q(type=5)). \
            prefetch_related('default_storage__vip_prices__vip_type', 'storages',
                             Prefetch('product_features',
                                      queryset=ProductFeature.objects.filter(feature_id=color_feature_id)
                                      .prefetch_related('product_feature_storages__storage__media'),
                                      to_attr='colors')) \
            .select_related('thumbnail', 'default_storage')
        if params['order']:
            products = products.order_by(params['order'], '-id').distinct('id', params['order'].replace('-', ''))
        if 'id__in' in 'filter' in params:
            products = sorted(products, key=lambda x: params['filter']['id__in'].index(x['id']))
        products = list(products)
        colors = cache.get('colors', None)
        if colors is None:
            colors = get_colors_hex(products)
        cache.set('colors', colors)
        # params['order']).order_by('-id').distinct('id')
        pg = get_pagination(request, products, MinProductSchema, serializer_args={'colors': colors})
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
            features = FeatureSchema(**request.schema_params).dump(features, many=True)
            return JsonResponse({'feature': features})
        except Exception:
            return JsonResponse({}, status=400)


class BestSeller(View):
    def get(self, request, permalink):
        box = Box.objects.get(permalink=permalink)
        last_week = add_days(-7)
        language = request.lang
        invoice_ids = Invoice.objects.filter(created_at__gte=last_week, status='payed').values('id')
        best_seller = get_best_seller(request, box, invoice_ids)
        return JsonResponse({'best_seller': best_seller})


class CategoryView(View):
    def get(self, request, permalink):
        category = Category.objects.filter(permalink=permalink, disable=False).first()
        products = Product.objects.filter(categories=category)
        pg = get_pagination(request, products, MinProductSchema)
        return JsonResponse(pg)
