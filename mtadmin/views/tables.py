from statistics import mean, StatisticsError
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from server.utils import *
from mtadmin.utils import *
from mtadmin.serializer import *
import pysnooper


class CategoryView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Category, CategoryASchema, CategoryESchema))

    def post(self, request):
        last_items = create_object(request, Category, CategoryASchema)
        return JsonResponse(last_items, status=201)

    def put(self, request):
        update_object(request, Category)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Category)


class BrandView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Brand, BrandSchema, BrandSchema))

    def post(self, request):
        last_items = create_object(request, Brand, BrandSchema)
        return JsonResponse(last_items, status=201)

    def put(self, request):
        update_object(request, Brand)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Brand)


class FeatureView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Feature, FeatureASchema, FeatureESchema))

    def post(self, request):
        items = create_object(request, Feature, FeatureASchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, Feature)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Feature)


class ProductView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Product, ProductASchema, ProductESchema))

    def post(self, request):
        items = create_object(request, Product, ProductESchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, Product)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Product)


class StorageView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Storage, StorageASchema, StorageESchema))

    def post(self, request):
        storage = create_object(request, Storage, StorageASchema)
        return JsonResponse(storage, status=201)

    def put(self, request):
        update_object(request, Storage)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Storage)


class InvoiceView(AdminView):
    def get(self, request):
        return JsonResponse(serialized_objects(request, Invoice, InvoiceASchema, InvoiceESchema))


class InvoiceStorageView(AdminView):
    def get(self, request):
        pk = request.GET.get('id', 0)
        storages = InvoiceStorage.objects.filter(invoice_id=pk)
        return JsonResponse({'data': InvoiceStorageSchema().dump(storages, many=True)})


class MenuView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Menu, MenuASchema, MenuESchema))

    def post(self, request):
        items = create_object(request, Menu, MenuASchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, Menu)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Menu)


class TagView(AdminView):
    def get(self, request):
        pk = request.GET.get('id', None)
        params = get_params(request)
        if pk:
            obj = Tag.objects.get(pk=pk)
            return JsonResponse({"data": TagESchema().dump(obj)})
        try:
            query = Tag.objects.annotate(contain=SearchVector(KeyTextTransform(request.lang, 'name')), ). \
                filter(**params['filter']).order_by(*params['order'])
            res = get_pagination(query, request.step, request.page, TagASchema)
        except (FieldError, ValueError):
            query = Tag.objects.all()
            res = get_pagination(query, request.step, request.page, TagASchema)

        return JsonResponse(res)

    def post(self, request):
        items = create_object(request, Tag, TagASchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, Tag)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Tag)


class SpecialOfferView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, SpecialOffer, SpecialOfferASchema, SpecialOfferESchema))

    def post(self, request):
        items = create_object(request, SpecialOffer, SpecialOfferASchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, SpecialOffer)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, SpecialOffer)


class SpecialProductView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, SpecialProduct, SpecialProductASchema, SpecialProductESchema))

    def post(self, request):
        items = create_object(request, SpecialProduct, SpecialProductASchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, SpecialProduct)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, SpecialProduct)


class MediaView(AdminView):
    def get(self, request):
        return JsonResponse(serialized_objects(request, Media, MediaASchema, MediaESchema))

    def post(self, request):
        data = json.loads(request.POST.get('data'))
        titles = data['titles']
        box_id = data['box_id']
        media_type = data['type']
        box_id = validate_box_id(request.user, box_id)
        media = upload(request, titles, media_type, box_id)
        if media:
            return JsonResponse({'media': MediaASchema().dump(media, many=True)})
        return JsonResponse({}, status=res_code['bad_request'])

    @pysnooper.snoop()
    def patch(self, request):
        data = json.loads(request.body)
        title = data['title']
        pk = data['id']
        media = Media.objects.filter(pk=pk)
        assert request.user.box_permission.filter(box=media.first().box).exists()
        media.update(title=title)
        return JsonResponse({'media': MediaASchema().dump(media, many=True)})

    def delete(self, request):
        return delete_base(request, Media)


class CommentView(AdminView):
    def get(self, request):
        return JsonResponse(serialized_objects(request, Comment, CommentASchema, CommentESchema))

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
