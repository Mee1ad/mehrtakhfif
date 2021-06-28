from django.db.models import Max, Min
from django.http import JsonResponse

from server.serialize import FeatureSchema, BrandSchema, SpecialProductSchema
from server.utils import *
import pysnooper


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
    @pysnooper.snoop()
    def get(self, request):
        q = request.GET.get('q', {})
        permalink = request.GET.get('cat', None)
        new_params = {'colors': 'product_features__feature_value_id', 'b': 'box__permalink',
                      'cat': 'categories__permalink', 'tag': 'tags__permalink',
                      'available': 'storages__available_count_for_sale__gte', 'brand': 'brand__in'}
        params = filter_params(request.GET, new_params, request.lang)
        disable = {'disable': False} if not request.user.is_staff else {}
        category_filters = {}
        if permalink:
            category_filters = {'permalink': permalink}
        if q:
            p = ProductDocument.search()
            p = p.query({"bool": {"should": [{"match": {"name_fa": {"query": q}}},
                                             {"wildcard": {"name_fa": f"{q}*"}},
                                             {"match": {"name_fa2": {"query": q}}}]}}).query('match', disable=False)
            product_ids = []
            for hit in p:
                product_ids.append(hit.id)

            category_filters['products__in'] = product_ids
            params['id__in'] = product_ids
        print(params)
        products = Product.objects.filter(**params['filter'], **disable).order_by(). \
            select_related('brand', 'default_storage').only('brand', 'categories', 'default_storage', 'name')

        if not products:
            return JsonResponse({'max_price': 0, 'min_price': 0, 'brands': [],
                                 'categories': [], 'breadcrumb': [], 'colors': []})
        prices = products.aggregate(max=Max('default_storage__discount_price'),
                                    min=Min('default_storage__discount_price'))
        brands = [product.brand for product in products.order_by('brand_id').distinct('brand_id') if product.brand]
        breadcrumb = self.get_breadcrumb(permalink)
        colors = get_colors_hex(products)
        categories = get_categories(category_filters)
        return JsonResponse({'max_price': prices['max'], 'min_price': prices['min'],
                             'brands': BrandSchema(**request.schema_params).dump(brands, many=True),
                             'categories': categories, 'breadcrumb': breadcrumb, 'colors': colors})

    def get_breadcrumb(self, permalink):
        category = Category.objects.filter(disable=False, box__disable=False, permalink=permalink)\
            .select_related('parent', 'box').first()
        if category:
            breadcrumb = [{'name': category.box.get_name_fa(), 'permalink': category.box.permalink}]
            if category.parent_id:
                breadcrumb.append({'name': category.parent.get_name_fa(), 'permalink': category.parent.permalink})
            breadcrumb.append({'name': category.get_name_fa(), 'permalink': category.permalink})
            return breadcrumb
        box = Box.objects.filter(disable=False, permalink=permalink).first()
        if box:
            return [{'name': box.get_name_fa(), 'permalink': box.permalink}]
        return []


class Filter(View):
    def get(self, request):
        new_params = {'colors': 'product_features__feature_value_id', 'b': 'box__permalink',
                      'cat': 'categories__permalink', 'tag': 'tags__permalink',
                      'available': 'storages__available_count_for_sale__gte', 'brand': 'brand__in'}
        params = filter_params(request.GET, new_params, request.lang)
        query = Q(verify=True, **params['filter'])
        disable = get_product_filter_params(request.user.is_staff)
        if params['related']:
            query = Q(verify=True, **params['filter']) | Q(verify=True, **params['related'])
        print(query)
        products = Product.objects.filter(query, Q(**disable), ~Q(type=5)). \
            prefetch_related('default_storage__vip_prices__vip_type', 'storages',
                             Prefetch('product_features',
                                      queryset=ProductFeature.objects.filter(feature_id=color_feature_id)
                                      .prefetch_related('product_feature_storages__storage__media'),
                                      to_attr='colors')) \
            .select_related('thumbnail', 'default_storage').order_by('-available', '-id').distinct('available', 'id')
        if params['order']:
            products = products.order_by(params['order']).distinct(params['order'].replace('-', ''))
        if 'id__in' in 'filter' in params:
            products = sorted(products, key=lambda x: params['filter']['id__in'].index(x['id']))
        products = list(products)
        colors = get_colors_hex(products)
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
