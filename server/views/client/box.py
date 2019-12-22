from django.db.models import Max, Min
from django.http import JsonResponse
import pysnooper
from server.views.utils import *


class GetSpecialOffer(View):
    def get(self, request, name):
        special_offer = SpecialOffer.objects.select_related('media').filter(box__meta_key=name).order_by('-id')
        res = {'special_product': SpecialProductSchema(language=request.lang).dump(special_offer, many=True)}
        return JsonResponse(res)


class GetSpecialProduct(View):
    def get(self, request, permalink):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        special_products = SpecialProduct.objects.filter(box__permalink=permalink)\
            .select_related(*SpecialProduct.min_select)[(page - 1) * step:step * page]
        special_products = MinSpecialProductSchema(language=request.lang).dump(special_products, many=True)
        return JsonResponse({'special_product': special_products})


class BoxDetail(View):
    @pysnooper.snoop()
    def get(self, request, permalink):
        try:
            box = Box.objects.filter(permalink=permalink).first()
            max_price = Storage.objects.filter(product__box=box).aggregate(Max('discount_price'))['discount_price__max']
            min_price = Storage.objects.filter(product__box=box).aggregate(Min('discount_price'))['discount_price__min']
            categories = get_categories(request.lang, box_id=box.id)
            return JsonResponse({'box': BoxSchema(request.lang).dump(box), 'max_price': max_price,
                                 'min_price': min_price, 'categories': categories})
        except Exception as e:
            print(e)
            return JsonResponse({}, status=400)


class BoxView(View):
    def get(self, request, permalink='all'):
        params = filter_params(request.GET)
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('p', default_page))
        try:
            box = Box.objects.get(permalink=permalink)
            query = {'box': box}
        except Box.DoesNotExist:
            box = Box.objects.all()
            query = {'box__in': box}

        products = Product.objects.filter(verify=True, **query, **params['filter'])
        last_page_number = last_page(products, step)
        products = products.select_related(*Product.select).order_by(*params['order'])
        # products = available_products(products, step, page)
        serialized_products = MinProductSchema(request.lang).dump(products, many=True)
        return JsonResponse({'data': serialized_products,
                             'current_page': page, 'last_page': last_page_number})


class GetFeature(View):
    def get(self, request):
        box_permalink = request.GET.get('box', None)
        category_permalink = request.GET.get('category', None)
        try:
            if box_permalink:
                box = Box.objects.filter(permalink=box_permalink).first()
                features = Feature.objects.filter(box=box)
            else:
                category = Category.objects.filter(permalink=category_permalink).prefetch_related(*Category.prefetch).first()
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
        basket_ids = Invoice.objects.filter(created_at__gte=last_week, status='payed').values('basket')
        best_seller = get_best_seller(box, basket_ids, language)
        return JsonResponse({'best_seller': best_seller})


class BoxCategory(View):
    def get(self, request, box, category):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        cat = Category.objects.filter(permalink=category).first()
        products = Product.objects.filter(box__permalink=box, category__permalink=category)\
            .select_related(*Product.permalink).order_by('-updated_at')[(page - 1) * step:step * page]

        # storage = Storage.objects.filter(box__meta_key=box, category__meta_key=category).select_related(
        #     'product', 'product__thumbnail').order_by('-updated_at')[(page - 1) * step:step * page]

        # special_products = SpecialProduct.objects.filter(category_id=pk).select_related('storage')
        # return JsonResponse({'products': serialize.storage(storage, True)})
        return JsonResponse({'category': CategorySchema(request.lang).dump(cat)})
        # 'special_products': serialize.special_product(special_products, True)}


class TagView(View):
    def get(self, request, pk):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        tag = Tag.objects.filter(pk=pk).first()
        products = tag.product.all().order_by('created_at')[(page - 1) * step:step * page]
        return JsonResponse({'products': TagSchema().dump(products, many=True)})


class Filter(View):
    def get(self, request):
        params = filter_params(request.GET)
        print(params)
        try:
            products = Storage.objects.filter(**params['filter']).order_by(*params['order'])
        except Exception:
            products = Storage.objects.all().order_by('-created_at')
        return JsonResponse({'products': StorageSchema(language=request.lang).dump(products, many=True)})
