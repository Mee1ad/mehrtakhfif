from statistics import mean, StatisticsError
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from mtadmin.utils import *
from mtadmin.serializer import *
import pysnooper
from django.db.utils import IntegrityError
from django.db.models import Sum
import json
from server.documents import TagDocument
from server.models import Media


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
            params['filter'].pop('box_id', None)
            box_id = Category.objects.get(pk=parent_id).box_id
            box_permissions = request.user.box_permission.all().values_list('id', flat=True)
            if box_id not in box_permissions:
                raise PermissionDenied
        else:
            params['filter']['parent_id'] = None
        categories = Category.objects.filter(**params['filter']).order_by(*params['order'])
        for category in categories:
            children = self.get_child_count(category)
            if children == 0:
                children = {'count': 0, 'childes': []}
            category.child_count = children['count']
            category.category_child_product_count = Product.objects.filter(categories__in=children['childes']).count()
            category.product_count = Product.objects.filter(categories=category).count()

        return JsonResponse(get_pagination(request, categories, CategoryASchema, request.all))

    def post(self, request):
        return create_object(request, Category, serializer=CategoryASchema, return_item=True)

    def put(self, request):
        return update_object(request, Category, return_item=True, serializer=CategoryASchema)

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
        params = get_params(request, 'box_id')
        if params['annotate']:
            params['filter'].pop('box_id', None)
            brands = Brand.objects.annotate(**params['annotate']).filter(**params['filter']).order_by(*params['order'])
        elif 'box_id' in params['filter']:
            products = Product.objects.filter(box_id=params['filter']['box_id'])
            brands = [product.brand for product in products.order_by('brand_id').distinct('brand_id') if product.brand]
        else:
            brands = Brand.objects.all().order_by(*params['order'])
        return JsonResponse(get_pagination(request, brands, BrandASchema, show_all=request.all))

    def post(self, request):
        return create_object(request, Brand, return_item=True, serializer=BrandASchema, error_null_box=False)

    def put(self, request):
        return update_object(request, Brand, return_item=True, serializer=BrandASchema, require_box=False)

    def delete(self, request):
        return delete_base(request, Brand, require_box=False)


class BoxView(TableView):
    permission_required = 'server.view_box'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Box, BoxASchema, BoxASchema, error_null_box=False))


class FeatureView(TableView):
    permission_required = 'server.view_feature'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Feature, FeatureASchema, FeatureASchema))

    def post(self, request):
        return create_object(request, Feature)

    def put(self, request):
        return update_object(request, Feature)

    def delete(self, request):
        return delete_base(request, Feature)


class ProductView(TableView):
    permission_required = 'server.view_product'

    # todo clean
    def get(self, request):
        types = request.GET.getlist('type[]')
        types2 = []
        params = get_params(request, 'box_id')
        required_box = {'error_null_box': True}
        for t in types:
            types2.append({'service': 1, 'product': 2, 'tourism': 3, 'package': 4, 'package_item': 5}[t])
            params['filter'].pop('type__in')
            params['filter']['type__in'] = types2
        if 'review__isnull' in params['filter']:
            required_box = {'error_null_box': False}
        return JsonResponse(serialized_objects(request, Product, ProductASchema, ProductESchema, params=params,
                                               **required_box))

    def post(self, request):
        return create_object(request, Product, serializer=ProductESchema, box_key='storage__product')

    def put(self, request):
        return update_object(request, Product)

    def delete(self, request):
        return delete_base(request, Product)


class HouseView(TableView):
    permission_required = 'server.view_house'

    # todo get single house like storage
    def get(self, request):
        return JsonResponse(serialized_objects(request, House, HouseESchema, HouseESchema, box_key='product__box'))

    def post(self, request):
        return create_object(request, House, HouseESchema)

    def put(self, request):
        return update_object(request, House)

    def delete(self, request):
        return delete_base(request, House)


class StorageView(TableView):
    permission_required = 'server.view_storage'

    def get(self, request):
        # todo clean
        Storage.objects.filter(deadline__lt=timezone.now(), disable=False).update(disable=True)
        box_key = 'product__box'
        params = get_params(request, box_key)
        if request.GET.get('product_type[]'):
            product_type = request.GET.getlist('product_type[]')
            params['filter']['product__type__in'] = product_type
            del params['filter']['product_type__in']
        if not params['filter'].get(box_key):
            box_check = get_box_permission(request.user, box_key)
            params['filter'] = {**params['filter'], **box_check}
        params['order'] = ['-priority']
        data = serialized_objects(request, Storage, StorageESchema, StorageESchema, box_key,
                                  params=params, error_null_box=False)
        if request.GET.get('product_id'):
            product_id = int(request.GET.get('product_id'))
            product = Product.objects.get(pk=product_id)
            box = BoxASchema().dump(product.box)
            return JsonResponse({"product": {"id": product.id, "name": product.name, "permalink": product.permalink,
                                             "default_storage": {"id": product.default_storage_id},
                                             "manage": product.manage, 'box': box, 'type': product.get_type_display()},
                                 "data": data})
        return JsonResponse(data)

        # if request.GET.get('product__type'):
        #     product_type = request.GET.getlist('product_type[]')
        #     print(product_type)
        #     return JsonResponse({})
        #     # product = Product.objects.get(pk=product_id)

    def post(self, request):
        return create_object(request, Storage, box_key='product__box', error_null_box=False)

    def put(self, request):
        return update_object(request, Storage, require_box=False, box_key='product__box')

    def delete(self, request):
        return delete_base(request, Storage)


class PackageView(TableView):
    permission_required = 'server.view_package'

    def get(self, request):
        params = get_params(request, box_key='product__box')
        params['filter']['product__type'] = 4
        return JsonResponse(serialized_objects(request, Storage, PackageASchema, box_key='product__box_id',
                                               params=params))

    def post(self, request):
        return create_object(request, Package, PackageASchema)

    def put(self, request):
        return update_object(request, Package)

    def delete(self, request):
        return delete_base(request, Package)


class VipPriceView(TableView):
    permission_required = 'server.view_vip_price'

    def get(self, request):
        return JsonResponse(serialized_objects(request, VipPrice, VipPriceASchema, VipPriceASchema,
                                               box_key='storage__product__box'))

    def post(self, request):
        return create_object(request, VipPrice)

    def put(self, request):
        return update_object(request, VipPrice)

    def delete(self, request):
        return delete_base(request, VipPrice)


class VipTypeView(TableView):
    permission_required = 'server.view_viptype'

    def get(self, request):
        return JsonResponse(serialized_objects(request, VipType, VipTypeASchema, error_null_box=False))


class InvoiceView(TableView):
    permission_required = 'server.view_invoice'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Invoice, InvoiceASchema, InvoiceESchema, error_null_box=False))


class InvoiceProductView(TableView):
    permission_required = 'server.view_invoice'

    def get(self, request):
        params = get_params(request, box_key='box_id')
        params['filter']['invoice__status'] = 2
        return JsonResponse(serialized_objects(request, InvoiceStorage, InvoiceStorageASchema, InvoiceStorageASchema,
                                               error_null_box=False, params=params))

    def put(self, request):
        return update_object(request, InvoiceStorage, require_box=False, box_key='box_id')


class MenuView(TableView):
    permission_required = 'server.view_menu'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Menu, MenuASchema, MenuESchema))

    def post(self, request):
        return create_object(request, Menu)

    def put(self, request):
        return update_object(request, Menu)

    def delete(self, request):
        return delete_base(request, Menu)


class TagView(TableView):
    permission_required = 'server.view_tag'

    def patch(self, request):
        data = json.loads(request.body)
        tags = data['tags']
        tags = Tag.objects.filter(id__in=tags)
        return JsonResponse({'tags': TagASchema().dump(tags, many=True)})

    def post(self, request):
        return create_object(request, Tag, box_key=None, return_item=True, serializer=TagASchema, error_null_box=False)

    def put(self, request):
        return update_object(request, Tag, serializer=TagASchema, require_box=False, return_item=True)

    def delete(self, request):
        return delete_base(request, Tag)


class SpecialOfferView(TableView):
    permission_required = 'server.view_specialoffer'

    def get(self, request):
        return JsonResponse(serialized_objects(request, SpecialOffer, SpecialOfferASchema, SpecialOfferESchema))

    def post(self, request):
        return create_object(request, SpecialOffer)

    def put(self, request):
        return update_object(request, SpecialOffer)

    def delete(self, request):
        return delete_base(request, SpecialOffer)


class SpecialProductView(TableView):
    permission_required = 'server.view_specialproduct'

    def get(self, request):
        data = serialized_objects(request, SpecialProduct, SpecialProductASchema, SpecialProductESchema)
        for index, item in enumerate(data['data']):
            data['data'][index]['product']['default_storage'] = data['data'][index].pop('default_storage')
            data['data'][index].pop('default_storage', None)
        return JsonResponse(data)

    def post(self, request):
        return create_object(request, SpecialProduct, SpecialProductESchema)

    def put(self, request):
        return update_object(request, SpecialProduct)

    def delete(self, request):
        # todo make it global
        pk = request.GET.get('id')
        item = SpecialProduct.objects.get(pk=pk)
        item.safe_delete(request.user.id)
        return JsonResponse({'message': 'با موفقیت حذف شد'})


class MediaView(TableView):
    permission_required = 'server.view_media'

    def get(self, request):
        no_box = [4, 5, 6]
        require_box = {}
        params = get_params(request, 'box_id')
        try:
            if int(params['filter']['type']) in no_box:
                require_box = {'error_null_box': False}
        except Exception:
            pass
        return JsonResponse(serialized_objects(request, Media, MediaASchema, MediaESchema, **require_box))

    def post(self, request):
        data = json.loads(request.POST.get('data'))
        titles = data['titles']
        box_id = data.get('box_id')
        media_type = data['type']
        if box_id not in request.user.box_permission.all().values_list('id', flat=True) and \
                media_type not in Media.no_box_type:
            raise PermissionDenied

        media = upload(request, titles, media_type, box_id)
        if media:
            return JsonResponse({'media': MediaASchema().dump(media, many=True)})
        return JsonResponse({}, status=res_code['bad_request'])

    def patch(self, request):
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


class AdsView(TableView):
    permission_required = 'server.view_ad'

    def get(self, request):
        params = get_params(request)
        if params['filter'].get('priority') == 'true':
            params['filter']['priority__isnull'] = False
            params['filter'].pop('priority')
        print(params)
        return JsonResponse(serialized_objects(request, Ad, AdASchema, AdASchema, error_null_box=False, params=params))

    def post(self, request):
        return create_object(request, Ad, error_null_box=False)

    def patch(self, request):
        priorities = json.loads(request.body)['priorities']
        Ad.objects.update(priority=None)
        [Ad.objects.filter(pk=pk).update(priority=priorities.index(pk)) for pk in priorities]
        return JsonResponse({'message': 'باموفقیت ذخیرته شد'})

    def put(self, request):
        return update_object(request, Ad, require_box=False)

    def delete(self, request):
        return delete_base(request, Ad)


class SliderView(TableView):
    permission_required = 'server.view_slider'

    def get(self, request):
        params = get_params(request)
        if params['filter'].get('priority') == 'true':
            params['filter']['priority__isnull'] = False
            params['filter'].pop('priority')
        return JsonResponse(serialized_objects(request, Slider, SliderASchema, SliderASchema, error_null_box=False,
                                               params=params))

    def post(self, request):
        return create_object(request, Slider, error_null_box=False)

    def patch(self, request):
        priorities = json.loads(request.body)['priorities']
        Slider.objects.update(priority=None)
        [Slider.objects.filter(pk=pk).update(priority=priorities.index(pk)) for pk in priorities]
        return JsonResponse({'message': 'باموفقیت ذخیرته شد'})

    def put(self, request):
        return update_object(request, Slider, require_box=False)

    def delete(self, request):
        return delete_base(request, Slider)


class SupplierView(TableView):
    permission_required = 'server.view_user'
    rm_list = ['email', 'password', 'is_ban', 'is_active', 'is_verify', 'privacy_agreement', ]

    def get(self, request):
        params = get_params(request)
        params['filter']['is_supplier'] = True
        return JsonResponse(serialized_objects(request, User, SupplierESchema, SupplierESchema, error_null_box=False,
                                               params=params))

    def post(self, request):
        data = get_data(request, require_box=False)
        data['is_supplier'] = True
        [data.pop(k, None) for k in self.rm_list]
        return create_object(request, User, serializer=SupplierESchema, error_null_box=False,
                             data=data, return_item=True)

    def put(self, request):
        data = get_data(request, require_box=False)
        data['is_supplier'] = True
        [data.pop(k, None) for k in self.rm_list]
        return update_object(request, User, serializer=SupplierESchema, data=data, return_item=True, require_box=False)


class Tax(AdminView):
    permission_required = 'server.view_invoice_storage'

    def get(self, request):
        # todo
        params = get_params(request, date_key='invoice__payed_at')
        # params['aggregate'] = {'tax': Sum('tax')}
        return JsonResponse(serialized_objects(request, InvoiceStorage, InvoiceStorageASchema))
