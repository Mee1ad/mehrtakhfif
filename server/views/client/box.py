from django.db.models import Max, Min
from django.http import JsonResponse

from server.serialize import *
from server.views.utils import *


class GetSpecialOffer(View):
    def get(self, request, name):
        special_offer = SpecialOffer.objects.select_related('media').filter(box__meta_key=name).order_by('-id')
        res = {'special_product': SpecialProductSchema(language=request.lang).dump(special_offer, many=True)}
        return JsonResponse(res)


class BoxDetail(View):
    def get(self, request, permalink):
        try:
            box = Box.objects.filter(permalink=permalink).first()
            max_price = Storage.objects.filter(box=box).aggregate(Max('discount_price'))['discount_price__max']
            min_price = Storage.objects.filter(box=box).aggregate(Min('discount_price'))['discount_price__min']
            categories = get_categories(box)
            return JsonResponse({'box': BoxSchema(request.lang).dump(box), 'max_price': max_price,
                                 'min_price': min_price, 'categories': categories})
        except Exception:
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
        products = products.select_related('default_storage').order_by(*params['order'])[(page - 1) * step:step * page]
        serialized_products = MinProductSchema(request.lang).dump(products, many=True)
        return JsonResponse({'data': serialized_products,
                             'current_page': page, 'last_page': last_page_number})


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
