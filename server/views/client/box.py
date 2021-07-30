from itertools import chain

from django.contrib.admin.utils import flatten
from django.db.models import Max, Min
from django.http import JsonResponse
from elasticsearch_dsl import Search

from mehr_takhfif.settings import ES_CLIENT
from server.serialize import *
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
    query = None
    params = None
    category_permalink = None

    def add_query_filter(self, ):
        query = self.params.get('q', None)
        if query:
            self.query["query"]["bool"]["must"].append({"match": {"name_fa": {"query": query, "boost": 1}}})
            self.query["query"]["bool"]["must"].append({"match": {"tags": {"query": query, "boost": 0.5}}})

    def add_brand_filter(self, ):
        brands = self.params.getlist('brands', None)
        if brands:
            self.query["query"]["bool"]["must"].append({"terms": {"brand.name": brands}})

    def add_color_filter(self, ):
        colors = self.params.getlist('colors', None)
        if colors:
            self.query["query"]["bool"]["must"].append({"nested": {"query": {"terms": {"colors.name": colors}},
                                                                   "path": "colors",
                                                                   "inner_hits": {"_source": ["name"]}}})

    def add_available_filter(self, ):
        only_available = self.params.get('available', None)
        if only_available:
            self.query["query"]["bool"]["must"].append({"term": {"available": only_available}})

    def add_category_filter(self, ):
        self.category_permalink = self.params.get('cat', )
        if self.category_permalink:
            self.query["query"]["bool"]["must"].append({"match": {"category_fa": self.category_permalink}})

    def get_breadcrumb(self, permalink):
        category = Category.objects.filter(disable=False, box__disable=False, permalink=permalink) \
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

    def get(self, request):
        s = Search(using=ES_CLIENT, index="product")
        self.params = request.GET
        self.query = {"query": {"bool": {"must": [{"term": {"disable": False}}]}}, "min_score": 2}
        self.add_query_filter()
        self.add_category_filter()
        products = s.from_dict(self.query)[:500]
        # products = s.query("match_all")[:20]
        products.aggs.metric('max_price', 'max', field='default_storage.discount_price') \
            .metric('min_price', 'min', field='default_storage.discount_price')
        products = products.execute()
        if not products.hits or not self.query["query"]["bool"]["must"]:
            return JsonResponse({"brands": [], "colors": [], "categories": [], "breadcrumb": [], 'min_price': 0,
                                 'max_price': 0})
        brands = s.from_dict({"_source": "brand", "collapse": {"field": "brand.id"}, **self.query})
        brands = brands.execute()
        brands = [hit.brand.to_dict() for hit in brands if hit.brand]
        box_ids = s.from_dict({"_source": "box_id", "collapse": {"field": "box_id"}, **self.query})
        box_ids = box_ids.execute()
        box_ids = [hit.box_id for hit in box_ids]
        box_ids = flatten(box_ids)
        box_ids = [item for sublist in box_ids for item in sublist]
        list_of_colors = [hit.colors for hit in products]
        colors = list(chain.from_iterable(list_of_colors))
        unique_colors = list({v['id']: v.to_dict() for v in colors}.values())
        prices = products.aggregations.to_dict()
        # products_id = [product.id for product in products]
        # category_filters = Q(products__in=products_id)
        # categories = get_categories(category_filters)
        categories = get_categories_with_box({"id__in": box_ids})
        breadcrumb = []
        if self.category_permalink:
            breadcrumb = self.get_breadcrumb(self.category_permalink)
        return JsonResponse({"brands": brands, "colors": unique_colors, "categories": categories,
                             "breadcrumb": breadcrumb, 'min_price': prices['min_price']['value'],
                             'max_price': prices['max_price']['value']})


class Filter(View):
    query = None
    params = None

    def add_query_filter(self, ):
        query = self.params.get('q', None)
        if query:
            self.query['query']["bool"]["should"] = [{"match": {"name_fa": {"query": query, "boost": 1}}},
                                                     {"match": {"tags": {"query": query, "boost": 0.5}}}]

    def add_brand_filter(self, ):
        brands = self.params.getlist('brands', None)
        if brands:
            self.query['query']["bool"]["must"].append({"terms": {"brand.permalink": brands}})

    def add_color_filter(self, ):
        colors = self.params.getlist('colors', None)
        if colors:
            self.query['query']["bool"]["must"].append({"nested": {"query": {"terms": {"colors.id": colors}},
                                                                   "path": "colors",
                                                                   "inner_hits": {"_source": ["id"]}}})

    def add_available_filter(self, ):
        only_available = self.params.get('available', None)
        if only_available:
            self.query['query']["bool"]["must"].append({"term": {"available": only_available}})

    def add_category_filter(self, ):
        category_permalink = self.params.get('cat', )
        if category_permalink:
            self.query['query']["bool"]["must"].append({"term": {"category_fa": category_permalink}})

    def add_price_filter(self, ):
        min_price = self.params.get('min_price', )
        max_price = self.params.get('max_price', )
        if min_price and max_price:
            self.query['query']["bool"]["must"].append({"range": {"default_storage.discount_price": {"gte": min_price,
                                                                                                     "lte": max_price}}})

    def get(self, request):
        available_sorts = {'cheap': 'default_storage.discount_price', 'expensive': '-default_storage.discount_price',
                           'best_seller': '-default_storage.sold_count',
                           'discount': '-default_storage.discount_percent'}
        self.params = request.GET
        sort = self.params.get('o', None)
        self.query = {"query": {"bool": {"must": [{"term": {"disable": False}}]}}, "min_score": 2}
        self.add_query_filter()
        self.add_color_filter()
        self.add_brand_filter()
        self.add_available_filter()
        self.add_category_filter()
        self.add_price_filter()

        s = Search(using=ES_CLIENT, index="product")
        products = s.from_dict(self.query)[:500]
        products = products.execute()
        count = products.hits.total['value']

        # product = ProductDocument.search()
        # products = product.query(self.query).extra(min_score=2)
        # count = products.count()
        # print(count)
        pagination = {"count": count, "step": request.step, "last_page": ceil(count / request.step)}
        if sort:
            products = products.sort(available_sorts[sort])
        products = products[request.step * (request.page - 1):request.step * request.page]
        serialized_products = FilterProductSchema().dump(products, many=True)
        # todo vip prices, to_json()
        return JsonResponse({"data": serialized_products, "pagination": pagination})


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
