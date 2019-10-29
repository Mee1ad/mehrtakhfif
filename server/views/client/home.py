from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server.views.utils import *
from server.views.admin_panel.read import ReadAdminView
import json
import time
import pysnooper
from django.views.decorators.cache import cache_page
from django.db.models import Max, Min
from server.serialize import *
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.contrib.postgres.search import TrigramSimilarity
from mehr_takhfif.settings import HOST, MEDIA_ROOT


class Test(View):
    @pysnooper.snoop()
    def get(self, request):
        from PIL import Image
        media = Media.objects.get(pk=1)
        # url = HOST + media.file.url
        img = Image.open(media.file.path)
        img2 = img.resize((500, 500))
        img2.save(MEDIA_ROOT + '/test.jpg', 'JPEG')
        w = request.GET.get('w', 300)
        h = request.GET.get('h', 300)
        from sorl.thumbnail import get_thumbnail
        im = get_thumbnail(media.file.path, f'{w}x{h}', quality=100)
        return HttpResponse(im.read(), content_type="image/jpeg")
        # return HttpResponse(img2)


class GetSlider(View):
    def get(self, request):
        slider = Slider.objects.select_related('media').all()
        res = {'slider': SliderSchema(
            language='english').dump(slider, many=True)}
        return JsonResponse(res)


class GetSpecialOffer(View):
    def get(self, request):
        special_offer = SpecialOffer.objects.select_related('media').all()
        res = {'special_offer': SpecialOfferSchema().dump(
            special_offer, many=True)}
        return JsonResponse(res)


class GetSpecialProduct(View):
    def get(self, request):
        special_product = SpecialProduct.objects.select_related(
            'storage', 'storage__product', 'media').all().order_by('-id')[(page - 1) * step:step * page]
        best_sell_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
            default=True).order_by('-product__sold_count')[(page - 1) * step:step * page]
        res = {'special_product': SpecialProductSchema(language=request.lang).dump(special_product, many=True),
               'best_sell_product': StorageSchema().dump(best_sell_storage, many=True)}
        return JsonResponse(res)


class AllSpecialProduct(View):
    def get(self, request):
        all_box = Box.objects.all()
        products = []
        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related('storage', 'media').filter(
                box=box).order_by('-created_by')[(page - 1) * step:step * page]
            product = {}
            product['id'] = box.pk
            product['name'] = box.name[request.lang]
            # product['special_product'] = SpecialProductSchema(request.lang).dump(box_special_product, many=True)
            best_seller_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
                default=True, box=box).order_by('-product__sold_count')[(page - 1) * step:step * page]
            product['best_seller'] = StorageSchema(
                request.lang).dump(best_seller_storage, many=True)
            products.append(product)
        res = {'products': products}
        return JsonResponse(res)


class AllCategory(View):
    def get(self, request):
        category = Category.objects.all()
        new_cats = [*category]
        remove_index = []
        for cat, index in zip(category, range(len(category))):
            if cat.parent is None:
                continue
            parent_index = new_cats.index(
                category.filter(pk=cat.parent_id).first())
            if not hasattr(new_cats[parent_index], 'child'):
                new_cats[parent_index].child = []
            new_cats[parent_index].child.append(cat)
            remove_index.append(cat)
        new_cats = [x for x in new_cats if x not in remove_index]
        b = {'items': CategoryMinSchema().dump(new_cats, many=True)}
        return JsonResponse(b)


class GetMenu(View):
    def get(self, request):
        return JsonResponse(json.dumps({'menu': MenuSchema(request.lang).dump(
            Menu.objects.select_related('media', 'parent').all(), many=True)}))


class GetAds(View):
    def get(self, request):
        return JsonResponse({'ads': AdSchema(request.lang).dump(
            Ad.objects.select_related('media', 'storage').all(), many=True)})


class Search(View):
    def get(self, request):
        q = request.GET.get('q', '')
        sv = SearchVector(KeyTextTransform('persian', 'product__name'), KeyTextTransform('persian', 'product__category__name'))
        sq = SearchQuery(q)
        product = Storage.objects.select_related('product').annotate(rank=SearchRank(sv, sq)).order_by('rank')[(page-1)*step:step*page]
        return JsonResponse({'products': StorageSchema(request.lang).dump(product, many=True)})
