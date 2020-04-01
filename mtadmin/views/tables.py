from statistics import mean, StatisticsError
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from server.utils import *
from mtadmin.utils import *
from mtadmin.serializer import *
import pysnooper
from django.db.utils import IntegrityError


class CategoryView(TableView):
    permission_required = 'server.view_category'

    def get(self, request):
        params = get_params(request, 'box_id')
        box_id = params['filter'].get('box_id')
        parent_id = params['filter'].get('parent_id')
        pk = request.GET.get('id', None)
        if pk:
            data = serialized_objects(request, Category, single_serializer=CategoryESchema, box_key='box_id')
            return JsonResponse(data)
        if box_id is None and parent_id is None:
            raise PermissionDenied
        if parent_id:
            box_id = Category.objects.get(parent_id=parent_id).pk
            box_permissions = request.user.box_permission.all().values_list('id', flat=True)
            if box_id not in box_permissions:
                raise PermissionDenied
        categories = Category.objects.filter(**params['filter']).order_by(*params['order'])
        for category in categories:
            children = self.get_child_count(category)
            if children == 0:
                children = {'count': 0, 'childes': []}
            category.child_count = children['count']
            category.category_child_product_count = Product.objects.filter(category__in=children['childes']).count()
            category.product_count = Product.objects.filter(category=category).count()

        return JsonResponse(get_pagination(categories, request.step, request.page, CategoryASchema))

    def post(self, request):
        pk = create_object(request, Category)
        return JsonResponse(pk, status=201)

    def put(self, request):
        update_object(request, Category)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Category)

    def get_child_count(self, category, sibling=0, childes=None):
        sibling_categories = Category.objects.filter(parent_id=category.pk)
        if not childes:
            childes = list(sibling_categories)
        childes += list(sibling_categories)
        sibling_count = sibling_categories.count()
        if sibling_count == 0:
            return sibling
        for sibl in sibling_categories:
            new_childes = self.get_child_count(sibl, childes=childes)
            if new_childes:
                sibling_count += new_childes['count']
        return {'count': sibling_count, 'childes': list(set(childes))}


class BrandView(TableView):
    permission_required = 'server.view_brand'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Brand, BrandASchema, BrandASchema))

    def post(self, request):
        pk = create_object(request, Brand, return_item=True, serializer=BrandASchema)
        return JsonResponse(pk, status=201)

    def put(self, request):
        item = update_object(request, Brand, return_item=True, serializer=BrandASchema)
        return JsonResponse({"data": item})

    def delete(self, request):
        return delete_base(request, Brand)


class FeatureView(TableView):
    permission_required = 'server.view_feature'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Feature, FeatureASchema, FeatureASchema))

    def post(self, request):
        pk = create_object(request, Feature)
        return JsonResponse(pk, status=201)

    def put(self, request):
        update_object(request, Feature)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Feature)


class ProductView(TableView):
    permission_required = 'server.view_product'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Product, ProductASchema, ProductESchema))

    def post(self, request):
        pk = create_object(request, Product, ProductESchema)
        return JsonResponse(pk, status=201)

    def put(self, request):
        update_object(request, Product)
        return JsonResponse({})

    def patch(self, request):
        data = json.loads(request.body)
        pk = data['id']
        permalink = data['permalink']
        if Product.objects.filter(pk=pk).update(permalink=permalink):
            return JsonResponse({})
        return HttpResponseBadRequest()

    def delete(self, request):
        return delete_base(request, Product)


class ProductStorage(TableView):
    permission_required = ['server.view_storage', 'server.view_product']

    def get(self, request, pk):
        storages = Storage.objects.filter(product_id=pk)
        product = storages.first().product
        data = StorageESchema().dump(storages, many=True)
        return JsonResponse({"product": {"id": product.id, "name": product.name, "permalink": product.permalink},
                             "data": data})


class StorageView(TableView):
    permission_required = 'server.view_storage'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Storage, StorageASchema, StorageESchema, 'product__box'))

    def post(self, request):
        pk = create_object(request, Storage)
        return JsonResponse(pk, status=201)

    def put(self, request):
        update_object(request, Storage)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Storage)


class InvoiceView(TableView):
    permission_required = 'server.view_invoice'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Invoice, InvoiceASchema, InvoiceESchema, error_null_box=False))


class InvoiceStorageView(TableView):
    permission_required = 'server.view_invoicestorage'

    def get(self, request):
        pk = request.GET.get('id', 0)
        storages = InvoiceStorage.objects.filter(invoice_id=pk)
        return JsonResponse({'data': InvoiceStorageSchema().dump(storages, many=True)})


class MenuView(TableView):
    permission_required = 'server.view_menu'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Menu, MenuASchema, MenuESchema))

    def post(self, request):
        pk = create_object(request, Menu)
        return JsonResponse(pk, status=201)

    def put(self, request):
        update_object(request, Menu)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Menu)


class TagView(TableView):
    permission_required = 'server.view_tag'

    def get(self, request):
        pk = request.GET.get('id', None)
        contain = request.GET.get('contain')
        if pk:
            obj = Tag.objects.get(pk=pk)
            return JsonResponse({"data": TagESchema().dump(obj)})
        try:
            query = Tag.objects.annotate(new_name=SearchVector(KeyTextTransform(request.lang, 'name')), ). \
                filter(new_name__contains=contain)
            res = get_pagination(query, request.step, request.page, TagASchema)
        except (FieldError, ValueError):
            query = Tag.objects.all()
            res = get_pagination(query, request.step, request.page, TagASchema)

        return JsonResponse(res)

    def post(self, request):
        items = create_object(request, Tag, return_item=True, serializer=TagASchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, Tag)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Tag)


class SpecialOfferView(TableView):
    permission_required = 'server.view_specialoffer'

    def get(self, request):
        return JsonResponse(serialized_objects(request, SpecialOffer, SpecialOfferASchema, SpecialOfferESchema))

    def post(self, request):
        pk = create_object(request, SpecialOffer)
        return JsonResponse(pk, status=201)

    def put(self, request):
        update_object(request, SpecialOffer)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, SpecialOffer)


class SpecialProductView(TableView):
    permission_required = 'server.view_specialproduct'

    def get(self, request):
        return JsonResponse(serialized_objects(request, SpecialProduct, SpecialProductASchema, SpecialProductESchema))

    def post(self, request):
        pk = create_object(request, SpecialProduct)
        return JsonResponse(pk, status=201)

    def put(self, request):
        update_object(request, SpecialProduct)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, SpecialProduct)


class MediaView(TableView):
    permission_required = 'server.view_media'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Media, MediaASchema, MediaESchema))

    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.POST.get('data'))
        titles = data['titles']
        box_id = data.get('box_id')
        if box_id not in request.user.box_permission.all().values_list('id', flat=True):
            raise PermissionDenied
        media_type = data['type']
        media = upload(request, titles, media_type, box_id)
        if media:
            return JsonResponse({'media': MediaASchema().dump(media, many=True)})
        return JsonResponse({}, status=res_code['bad_request'])

    def patch(self, request):
        import time
        time.sleep(5)
        data = json.loads(request.body)
        title = data['title']
        pk = data['id']
        media = Media.objects.filter(pk=pk)
        assert request.user.box_permission.filter(id=media.first().box_id).exists()
        media.update(title=title)
        return JsonResponse({'media': MediaASchema().dump(media.first())})

    def delete(self, request):
        return delete_base(request, Media)


class CommentView(TableView):
    permission_required = 'server.view_comment'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Comment, CommentASchema, CommentESchema, error_null_box=False))

    def patch(self, request):
        data = get_data(request)
        pk = data['id']
        comment = Comment.objects.get(pk=pk)
        duplicate_comment = Comment.objects.filter(user=comment.user, type=2, product=comment.product,
                                                   approved=True).count() > 1
        comment.approved = True
        comment.save()
        rates = Comment.objects.filter(product_id=comment.product_id, approved=True, type=2).values_list('rate')
        try:
            if duplicate_comment:
                raise StatisticsError
            average_rate = round(mean([rate[0] for rate in rates]))
            Product.objects.filter(pk=comment.product_id).update(rate=average_rate)
        except StatisticsError:
            pass
        return JsonResponse({})

    def delete(self, request):
        pk = int(request.GET.get('id', None))
        Comment.objects.filter(pk=pk).update(suspend=True)
        return JsonResponse({})
