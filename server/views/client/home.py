from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server import serializer as serialize
from server.views.utils import Tools
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
import requests


class Test(Tools):
    def get(self, request):
        pass
        return JsonResponse({})


class GetSlider(Tools):
    def get(self, request):
        slider = Slider.objects.select_related('media').all()
        res = {'slider': SliderSchema(language='english').dump(slider, many=True)}
        return JsonResponse(res)


class GetSpecialOffer(Tools):
    def get(self, request):
        special_offer = SpecialOffer.objects.select_related('media').all()
        res = {'special_offer': SpecialOfferSchema().dump(special_offer, many=True)}
        return JsonResponse(res)


class GetSpecialProduct(Tools):
    def get(self, request):
        page = self.page
        step = self.step
        special_product = SpecialProduct.objects.select_related(
            'storage', 'storage__product', 'media').all().order_by('-id')[(page - 1) * step:step * page]
        best_sell_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
            default=True).order_by('-product__sold_count')[(page - 1) * step:step * page]
        res = {'special_product': SpecialProductSchema(language=request.lang).dump(special_product, many=True),
               'best_sell_product': StorageSchema().dump(best_sell_storage, many=True)}
        return JsonResponse(res)


class AllSpecialProduct(Tools):
    def get(self, request):
        page = self.page
        step = self.step
        all_box = Box.objects.all()
        products = []
        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related('storage', 'media').filter(
                box=box).order_by('-created_by')[(page - 1) * step:step * page]
            product = {}
            product['id'] = box.pk
            product['name'] = box.name[request.lang]
            product['special_product'] = SpecialProductSchema(request.lang).dump(box_special_product, many=True)
            best_seller_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
                default=True).order_by('-product__sold_count')[(page - 1) * step:step * page]
            product['best_seller'] = StorageSchema(request.lang).dump(best_seller_storage, many=True)
            products.append(product)
        res = {'products': products}
        return JsonResponse(res)


class AllCategory(Tools):
    @pysnooper.snoop()
    def get(self, request):
        category = Category.objects.all()
        new_cats = [*category]
        remove_index = []
        for cat, index in zip(category, range(len(category))):
            if cat.parent is None:
                continue
            parent_index = new_cats.index(category.filter(pk=cat.parent_id).first())
            if not hasattr(new_cats[parent_index], 'child'):
                new_cats[parent_index].child = []
            new_cats[parent_index].child.append(cat)
            remove_index.append(cat)
        new_cats = [x for x in new_cats if x not in remove_index]
        b = {'items': CategoryMinSchema().dump(new_cats, many=True)}
        return JsonResponse(b)


class AllCategoryOld(Tools):
    def get(self, request):
        category = Category.objects.all()
        cat_ids = []
        for cat in category:
            try:
                cat_ids.append((cat.parent.id, cat.id))
                # cat_ids.append((CategoryMinSchema().dump(cat.parent), CategoryMinSchema().dump(cat.id)))
            except AttributeError:
                cat_ids.append([cat.id, cat.id])
                # cat_ids.append([CategoryMinSchema().dump(cat), CategoryMinSchema().dump(cat)])
        duplicates = []
        parent_childes = []
        root_parent_childes = []
        for cat_id in cat_ids:
            if cat_id in duplicates:
                continue
            same_parent = [x for x in cat_ids if x[0] == cat_id[0]]
            if len(same_parent) > 1:
                parent_child = [cat_id[0], [x[1] for x in same_parent]]
                print(parent_child)
                parent_childes.append(parent_child)
                duplicates += same_parent
                print(duplicates)
                cat_ids = [x for x in cat_ids if x not in duplicates]
                print(cat_ids)
                print('--------')
            else:
                root_parent_childes.append(cat_id[0])
        self.test(parent_childes)
        categories = self.test(parent_childes) + root_parent_childes
        categories = self.categories_serilizer(categories, category)
        # categories = CategorySchema().dump(my_list, many=True)
        return JsonResponse({'categories': 'ok'})

    def categories_serilizer(self, categories, category):
        print(categories)
        for cat in categories:
            try:
                cat[0] = category.filter(pk=cat[0]).first()
            except TypeError:
                categories[categories.index(cat)] = category.filter(pk=cat).first()
                print(cat)
        print(categories)


    def test(self, parent_childes):
        for parent_child in parent_childes:
            for i in parent_childes:
                if i == parent_child:
                    continue
                if i[0] in parent_child[1]:
                    parent_child[1].remove(i[0])
                    parent_child[1].append([i[0], i[1]])
                    parent_childes.remove(i)
        return parent_childes


    def organize_cat(self, category):
        print('category.child:', category.child)
        if category.child:
            category.child.parent = None
        print('category.parent:', category.parent)
        if category.parent is None:
            print('category:', category)
            return category
        print('category:', category)
        return self.inheritance(category)

    def inheritance(self, category):
        print('category.parent.child:', category.parent.child)
        category.parent.child = category
        print('category.parent:', category.parent)
        return self.organize_cat(category.parent)


class GetMenu(Tools):
    def get(self, request):
        return JsonResponse({'menu': MenuSchema(request.lang).dump(
            Menu.objects.select_related('media', 'parent').all(), many=True)})


class GetAds(Tools):
    def get(self, request):
        return JsonResponse({'ads': AdSchema(request.lang).dump(
            Ad.objects.select_related('media', 'storage').all(), many=True)})


class Search(Tools):
    def get(self, request):
        step = self.step
        page = self.page
        q = request.GET.get('q', '')
        sv = SearchVector(KeyTextTransform('persian', 'product__name'),
                          KeyTextTransform('persian', 'product__category__name'))
        sq = SearchQuery(q)
        product = Storage.objects.select_related('product').annotate(rank=SearchRank(sv, sq)).order_by('rank')\
        [(page-1)*step:step*page]
        return JsonResponse({'products': StorageSchema(request.lang).dump(product, many=True)})
