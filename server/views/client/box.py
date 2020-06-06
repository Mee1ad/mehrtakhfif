from django.db.models import Max, Min, Q
from django.http import JsonResponse
from server.utils import *
from server.serialize import BoxSchema, FeatureSchema, MinProductSchema, BrandSchema
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
                               .select_related(*SpecialProduct.min_select)[(page - 1) * step:step * page]
        special_products = MinSpecialProductSchema(**request.schema_params).dump(special_products, many=True)
        return JsonResponse({'special_product': special_products})


class FilterDetail(View):
    @pysnooper.snoop()
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
            filter_by['box'] = Box.objects.get(permalink=box_permalink)
            cat_filter_by['box'] = filter_by['box']
            res['box'] = BoxSchema(**request.schema_params).dump(filter_by['box'])
        if category_permalink:
            category = Category.objects.get(permalink=category_permalink)
            filter_by['categories'] = category
            cat_filter_by['box'] = category.box
            res['box'] = BoxSchema(**request.schema_params).dump(category.box)
        categories = Category.objects.filter(**cat_filter_by, **disable)
        if q:
            rank = get_rank(q, request.lang)
            rank = {'rank': rank}
            order_by = ['-rank']
        products = Product.objects.annotate(**rank).filter(**filter_by).order_by(*order_by). \
            select_related('brand', 'default_storage')
        if q:
            categories = Category.objects.filter(
                pk__in=list(filter(None, set(products.values_list('categories', flat=True)))), **disable)
        prices = products.aggregate(max=Max('default_storage__discount_price'),
                                    min=Min('default_storage__discount_price'))
        categories = get_categories(request.lang, categories=categories)
        brands = [product.brand for product in products.order_by('brand_id').distinct('brand_id') if product.brand]
        breadcrumb = self.get_breadcrumb(category_permalink)
        return JsonResponse({'max_price': prices['max'], 'min_price': prices['min'], **res,
                             'brands': BrandSchema(**request.schema_params).dump(brands, many=True),
                             'categories': categories, 'breadcrumb': breadcrumb})

    def get_breadcrumb(self, category_permalink, lang='fa'):
        breadcrumb = []
        if not category_permalink:
            return breadcrumb
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
        params = filter_params(request.GET, request.lang)
        query = Q(verify=True, **params['filter'])
        disable = get_product_filter_params(request.user.is_staff)
        if params['related']:
            query = Q(verify=True, **params['filter']) | Q(verify=True, **params['related'])
        print(params)
        print(disable)
        products = Product.objects.annotate(**params['annotate']).filter(query, Q(**disable), ~Q(type=5)).order_by(
            params['order'], '-id').distinct('id', params['order'].replace('-', ''))
        # params['order']).order_by('-id').distinct('id')
        pg = get_pagination(request, products, MinProductSchema)
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


class TagView(View):
    def get(self, request, permalink):
        tag = Tag.objects.filter(permalink=permalink).first()
        products = tag.products.all()
        pg = get_pagination(request, products, MinProductSchema)
        return JsonResponse(pg)


class CategoryView(View):
    def get(self, request, permalink):
        category = Category.objects.filter(permalink=permalink, disable=False).first()
        products = Product.objects.filter(category=category)
        pg = get_pagination(request, products, MinProductSchema)
        return JsonResponse(pg)
