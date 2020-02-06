
from statistics import mean, StatisticsError

from server.utils import *
from mtadmin.utils import *
from mtadmin.serializer import *


class CategoryView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Category, CategorySchema))

    def post(self, request):
        last_items = create_object(request, Category, CategorySchema)
        return JsonResponse(last_items, status=201)

    def patch(self, request):
        data = get_data(request)
        category = Category.objects.filter(pk=data['category']).first()
        features = Feature.objects.filter(pk__in=data['features'])
        category.feature_set.add(*features)
        return JsonResponse({})

    def put(self, request):
        update_object(request, Category)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Category)


class BrandView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Brand, BrandSchema))

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
        return JsonResponse(serialized_objects(request, Feature, FeatureSchema))

    def post(self, request):
        items = create_object(request, Feature, FeatureSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, Feature)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Feature)


class ProductView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Product, ProductSchema))

    def post(self, request):
        items = create_object(request, Product, ProductESchema)
        return JsonResponse(items, status=201)

    def patch(self, request):
        data = get_data(request)
        product = Product.objects.filter(pk=data['product']).first()
        tags = Tag.objects.filter(pk__in=data['tags'])
        media = Media.objects.filter(pk__in=data['media'])
        product.tag.add(*tags)
        product.media.add(*media)
        return JsonResponse({})

    def put(self, request):
        update_object(request, Product)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Product)


class StorageView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Storage, StorageSchema))

    def post(self, request):
        storage = create_object(request, Storage, StorageSchema)

        return JsonResponse(storage, status=201)

    def patch(self, request):
        data = get_data(request)
        storage = Storage.objects.filter(pk=data['storage']).first()
        features = Feature.objects.filter(pk__in=data['features'])
        storage.feature.add(*features)
        return JsonResponse({})

    def put(self, request):
        update_object(request, Storage)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Storage)


class InvoiceView(AdminView):
    def get(self, request):
        return JsonResponse(serialized_objects(request, Invoice, InvoiceSchema))


class InvoiceStorageView(AdminView):
    def get(self, request):
        pk = request.GET.get('id', 0)
        storages = InvoiceStorage.objects.filter(invoice_id=pk)
        return JsonResponse({'data': InvoiceStorageSchema().dump(storages, many=True)})


class MenuView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Menu, MenuSchema))

    def post(self, request):
        items = create_object(request, Menu, MenuSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, Menu)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Menu)


class TagView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Tag, TagSchema))

    def post(self, request):
        items = create_object(request, Tag, TagSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, Tag)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Tag)


class SpecialOfferView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, SpecialOffer, SpecialOfferSchema))

    def post(self, request):
        items = create_object(request, SpecialOffer, SpecialOfferSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, SpecialOffer)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, SpecialOffer)


class SpecialProductView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, SpecialProduct, SpecialProductSchema))

    def post(self, request):
        items = create_object(request, SpecialProduct, SpecialProductSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, SpecialProduct)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, SpecialProduct)


class MediaView(AdminView):
    def get(self, request):
        return JsonResponse(serialized_objects(request, Media, MediaSchema))

    def post(self, request):
        data = json.loads(request.POST.get('data'))
        titles = data['titles']
        box_id = data['box_id']
        box_id = validate_box_id(request.user, box_id)
        if upload(request, titles, box_id):
            return JsonResponse({})
        return JsonResponse({}, status=res_code['bad_request'])

    def delete(self, request):
        return delete_base(request, Media)


class BlogView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, Blog, BlogSchema))

    def post(self, request):
        items = create_object(request, Blog, BlogSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, Blog)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, Blog)


class BlogPostView(AdminView):

    def get(self, request):
        return JsonResponse(serialized_objects(request, BlogPost, BlogPostSchema))

    def post(self, request):
        items = create_object(request, BlogPost, BlogPostSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        update_object(request, BlogPost)
        return JsonResponse({})

    def delete(self, request):
        return delete_base(request, BlogPost)


class CommentView(AdminView):
    def get(self, request):
        return JsonResponse(serialized_objects(request, Comment, CommentSchema))

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
