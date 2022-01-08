from itertools import chain

from django.contrib.admin.utils import flatten
from django.http import JsonResponse
from elasticsearch_dsl import Search

from mehr_takhfif.settings import ES_CLIENT
from server.serialize import *
from server.utils import *


# noinspection PyTypeChecker
class FilterDetail(View):
    query = None
    params = None
    category_permalink = None

    def add_query_filter(self, ):
        q = self.params.get('q', None)
        if q:
            query = [{"match": {"name_fa": {"query": q, "boost": 1}}},
                     {"match": {"name_fa2": {"query": q, "boost": 0.2}}},
                     {"match": {"tags": {"query": q, "boost": 0.2}}}]
            self.query['query']["bool"]["should"].extend(query)
            self.query['min_score'] += 4

    def add_category_filter(self, ):
        self.category_permalink = self.params.get('cat', )
        if self.category_permalink:
            query = [
                {
                    "nested": {
                        "path": "categories",
                        "query": {
                            "match": {
                                "categories.permalink": self.category_permalink
                            }
                        }
                    }
                },
                {
                    "term": {
                        "category.permalink": self.category_permalink
                    }
                }
            ]
            self.query['query']["bool"]["should"].extend(query)

    def get_breadcrumb(self, permalink):
        categories = Category.objects.filter(permalink=permalink).values('name__fa', 'permalink', 'parent__name__fa',
                                                                         'parent__permalink',
                                                                         'parent__parent__name__fa',
                                                                         'parent__parent__permalink')[0]
        categories = [
            {"name": categories["parent__parent__name__fa"], "permalink": categories["parent__parent__permalink"]},
            {"name": categories["parent__name__fa"], "permalink": categories["parent__permalink"]},
            {"name": categories["name__fa"], "permalink": categories["permalink"]}]
        breadcrumb = []
        for item in categories:
            if None in item.values():
                continue
            breadcrumb.append(item)
        return breadcrumb

    def add_type_filter(self):
        product_type = self.params.get('type', None)
        if product_type:
            query = {"product": {"must_not": [{"term": {"disable": True}}],
                                 "must": [{"term": {"type": {"value": "product", "boost": 10}}}]},
                     "service": {
                         "must": [{"term": {"disable": False}}, {"term": {"type": {"value": "service", "boost": 10}}}]}}
            query = query.get(product_type, query["product"])
            self.query["query"]["bool"] = query
            self.query['min_score'] += 0.9

    def get(self, request):
        s = Search(using=ES_CLIENT, index="product")
        self.params = request.GET
        self.query = {"query": {"bool": {"must": [], "should": [], "must_not": [{"term": {"disable": True}}]}},
                      "size": 10000, "min_score": 0}
        self.add_query_filter()
        self.add_category_filter()
        self.add_type_filter()
        products = s.from_dict(self.query)
        # products = s.query("match_all")[:20]
        products.aggs.metric('max_price', 'max', field='default_storage.discount_price') \
            .metric('min_price', 'min', field='default_storage.discount_price')
        products = products.execute()
        if not products.hits:
            return JsonResponse({"brands": [], "colors": [], "categories": [], "breadcrumb": [], 'min_price': 0,
                                 'max_price': 0})
        brands = s.from_dict({"_source": "brand", "collapse": {"field": "brand.id"}, **self.query})
        brands = brands.execute()
        brands = [hit.brand.to_dict() for hit in brands if hit.brand]
        # category_ids = s.from_dict({"_source": "category_id", "collapse": {"field": "category_id"}, **self.query})
        category_ids_object = s.from_dict({"_source": "categories.id", **self.query})
        # category_ids_object = s.from_dict({"_source": "categories.id", **self.query})
        category_ids_hits = category_ids_object.execute()
        # category_ids_list = [hit.categories[0].id for hit in category_ids_hits]
        category_ids_list = list(filter(None, map(lambda x: x.to_dict().get("id"), category_ids_hits)))
        category_ids = set(category_ids_list)
        list_of_colors = [getattr(hit, 'colors', {}) for hit in products]
        colors = list(chain.from_iterable(list_of_colors))
        unique_colors = list({v['id']: v.to_dict() for v in colors}.values())
        prices = products.aggregations.to_dict()
        # products_id = [product.id for product in products]
        # category_filters = Q(products__in=products_id)
        # categories = get_categories(category_filters)
        categories = get_categories({"id__in": category_ids})
        breadcrumb = []
        if self.category_permalink:
            breadcrumb = self.get_breadcrumb(self.category_permalink)
            print(breadcrumb)
        return JsonResponse({"brands": brands, "colors": unique_colors, "categories": categories,
                             "breadcrumb": breadcrumb, 'min_price': prices['min_price']['value'],
                             'max_price': prices['max_price']['value']})


# noinspection PyTypeChecker
class Filter(View):
    query = None
    params = None
    category_description = None

    def add_query_filter(self, ):
        q = self.params.get('q', None)
        if q:
            query = [{"match": {"name_fa": {"query": q, "boost": 1}}},
                     {"match": {"name_fa2": {"query": q, "boost": 0.2}}},
                     {"match": {"tags": {"query": q, "boost": 0.2}}}]
            self.query['query']["bool"]["should"].extend(query)
            self.query['min_score'] += 4

    def add_brand_filter(self, ):
        brands = self.params.getlist('brands', None)
        if brands:
            self.query['query']["bool"]["must"].append({"terms": {"brand.permalink": brands, "boost": 1}})

    def add_color_filter(self, ):
        colors = self.params.getlist('colors', None)
        if colors:
            query = {
                "nested": {
                    "path": "colors",
                    "query": {
                        "terms": {
                            "colors.id": colors
                        }
                    }
                }
            }

            self.query['query']["bool"]["must"].append(query)

    def add_available_filter(self, ):
        only_available = self.params.get('available', None)
        if only_available:
            self.query['query']["bool"]["must"].append({"term": {"available": only_available}})

    def add_category_filter(self, ):
        category_permalink = self.params.get('cat', )
        if category_permalink:
            category_document = Search(using=ES_CLIENT, index="category")
            query = {"query": {"match": {"permalink": category_permalink}}, 'min_score': 1}
            category_query = category_document.from_dict(query)
            category_result = category_query.execute()
            self.category_description = getattr(category_result[0], 'description', None)
            query = [
                {
                    "nested": {
                        "path": "categories",
                        "query": {
                            "match": {
                                "categories.permalink": category_permalink
                            }
                        }
                    }
                },
                {
                    "term": {
                        "category.permalink": category_permalink
                    }
                }
            ]
            self.query['query']["bool"]["should"].extend(query)

    def add_price_filter(self, ):
        min_price = self.params.get('min_price', )
        max_price = self.params.get('max_price', )
        if min_price and max_price:
            self.query['query']["bool"]["must"].append({
                "range": {"default_storage.discount_price": {"gte": min_price, "lte": max_price}}})

    def add_sort_type(self):
        sort = self.params.get('o', None)
        available_sorts = {'price': {"default_storage.discount_price": {"order": "asc"}},
                           '-price': {"default_storage.discount_price": {"order": "desc"}},
                           'best_seller': {"default_storage.sold_count": {"order": "desc"}},
                           'discount': {"default_storage.discount_percent": {"order": "desc"}}}
        if sort:
            self.query['sort'].append(available_sorts[sort])

    def add_type_filter(self):
        product_type = self.params.get('type', None)
        if product_type:
            query = {"product": {"must_not": [{"term": {"disable": True}}],
                                 "must": [{"term": {"type": {"value": "product", "boost": 10}}}]},
                     "service": {
                         "must": [{"term": {"disable": False}}, {"term": {"type": {"value": "service", "boost": 10}}}]}}
            query = query.get(product_type, query["product"])
            self.query["query"]["bool"] = query
            self.query['min_score'] += 0.9

    def get(self, request):
        self.params = request.GET
        self.query = {"query": {"bool": {"must": [], "should": [], "must_not": [{"term": {"disable": True}}]}},
                      "sort": [{"available": {"order": "desc"}}, "_score", ], "from": request.step * (request.page - 1),
                      "size": request.step, "min_score": 0}

        self.add_query_filter()
        self.add_color_filter()
        self.add_brand_filter()
        self.add_available_filter()
        self.add_category_filter()
        self.add_price_filter()
        self.add_sort_type()
        self.add_type_filter()
        s = Search(using=ES_CLIENT, index="product")
        products = s.from_dict(self.query)
        products = products.execute()
        count = products.hits.total['value']
        pagination = {"count": count, "step": request.step, "last_page": ceil(count / request.step)}
        serialized_products = FilterProductSchema().dump(products, many=True)
        # todo vip prices
        return JsonResponse({"data": serialized_products, "description": self.category_description,
                             "pagination": pagination})


class GetFeature(View):
    def get(self, request):
        category_permalink = request.GET.get('category', None)
        try:
            category = Category.objects.filter(permalink=category_permalink).prefetch_related(
                *Category.prefetch).first()
            features = category.feature_set.all()
            features = FeatureSchema(**request.schema_params).dump(features, many=True)
            return JsonResponse({'feature': features})
        except Exception:
            return JsonResponse({}, status=400)
