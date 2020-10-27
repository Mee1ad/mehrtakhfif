import json
from statistics import mean, StatisticsError

from django.shortcuts import render_to_response
from django.utils.crypto import get_random_string

from mtadmin.serializer import *
from mtadmin.utils import *
from server.models import Media


# from server.models import Product


class CategoryView(TableView):
    permission_required = 'server.view_category'

    def get(self, request):
        params = get_params(request, 'box_id')
        parent_id = params['filter'].get('parent_id')
        pk = request.GET.get('id', None)
        if pk:
            data = serialized_objects(request, Category, single_serializer=CategoryESchema, box_key='box_id')
            return JsonResponse(data)
        if parent_id:
            # params['filter'].pop('box_id', None)
            box_id = Category.objects.get(pk=parent_id).box_id
            box_permissions = request.user.box_permission.all().values_list('id', flat=True)
            if box_id not in box_permissions:
                raise PermissionDenied
        else:
            params['filter']['parent_id'] = None
        categories = Category.objects.filter(
            Q(**params['filter']) | Q(box_id=params['filter']['box_id'], permalink__isnull=True,
                                      parent__isnull=False)).order_by(*params['order'])
        for category in categories:
            children = self.get_child_count(category)
            if children == 0:
                children = {'count': 0, 'childes': []}
            category.child_count = children['count']
            category.category_child_product_count = Product.objects.filter(categories__in=children['childes']).count()
            category.product_count = Product.objects.filter(categories=category).count()
        test = {}
        # test = {'html': "hello </br> world", 'variant': 'error', 'duration': 15000}
        return JsonResponse({**get_pagination(request, categories, CategoryASchema, request.all), **test})

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
        return JsonResponse(serialized_objects(request, Feature, FeatureASchema, FeatureASchema, error_null_box=False))

    def post(self, request):
        data = get_data(request, require_box=True)
        feature_type = [v[0] for i, v in enumerate(Feature.types) if v[1] == data['type']][0]
        feature = Feature.objects.filter(name__fa=data['name']['fa'], type=feature_type)
        if feature.exists():
            return JsonResponse({'data': FeatureASchema().dump(feature.first())}, status=200)
        return create_object(request, Feature, error_null_box=False)

    def put(self, request):
        return update_object(request, Feature, serializer=FeatureASchema, require_box=False, return_item=True,
                             restrict_m2m=['features'])

    def patch(self, request):
        check_user_permission(request.user, 'server.change_feature')
        data = get_data(request, require_box=False)
        ids = data['ids']
        features = FeatureValue.objects.filter(pk__in=ids)
        for feature in features:
            feature.priority = ids.index(feature.pk)
        FeatureValue.objects.bulk_update(features, ['priority'])
        return JsonResponse({**responses['priority']}, status=202)

    def delete(self, request):
        return delete_base(request, Feature)


class FeatureValueView(TableView):
    permission_required = 'server.view_featurevalue'

    def get(self, request):
        return JsonResponse(serialized_objects(request, FeatureValue, FeatureValueASchema, FeatureValueASchema,
                                               error_null_box=False))

    def post(self, request):
        return create_object(request, FeatureValue, serializer=FeatureValueASchema, error_null_box=False,
                             return_item=True)

    def put(self, request):
        return update_object(request, FeatureValue, serializer=FeatureValueASchema, require_box=False, return_item=True)

    def delete(self, request):
        return delete_base(request, FeatureValue)


class FeatureGroupView(TableView):
    permission_required = 'server.view_featuregroup'

    def get(self, request):
        required_box = {'error_null_box': True}
        if request.GET.get('id', None) or request.GET.get('name__fa', None):
            required_box = {'error_null_box': False}
        return JsonResponse(serialized_objects(request, FeatureGroup, FeatureGroupASchema, FeatureGroupASchema,
                                               **required_box))

    def post(self, request):
        return create_object(request, FeatureGroup)

    def put(self, request):
        return update_object(request, FeatureGroup)

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
        if params['filter'].get('only_id', False) and params['filter'].get('box_id', False):
            params['filter'].pop('only_id')
            return JsonResponse({'data': list(Product.objects.filter(**params['filter']).order_by('id').distinct('id')
                                              .values_list('id', flat=True))})
        return JsonResponse(serialized_objects(request, Product, ProductASchema, ProductESchema, params=params,
                                               **required_box))

    def post(self, request):
        # data = get_data(request, require_box=True)
        return create_object(request, Product, serializer=ProductESchema, box_key='storage__product')

    def put(self, request):
        data = get_data(request, require_box=True)
        product = Product.objects.get(id=data['id'])
        extra_response = {}
        features = []
        used_product_feature_ids = []
        if data.get('features'):
            storages = product.storages.all()
            used_product_features = ProductFeatureStorage.objects.filter(storage__in=storages)
            used_product_feature_ids = list(set(used_product_features.values_list('product_feature__id', flat=True)))
            used_feature_ids = list(set(used_product_features.values_list('product_feature__feature_id', flat=True)))
            new_feature_ids = list(set([item['feature_id'] for item in data['features']]))
            restrict_objects = list(set(used_feature_ids) - set(new_feature_ids))
            extra_response = {}
            features = Feature.objects.filter(pk__in=restrict_objects)
            if restrict_objects:
                features = features.values_list('name__fa', flat=True)
                message = f"""محصول آپدیت شد ولی فیچرا همونجوری که بودن میمونن میدونی چرا؟
                چون که این فیچرا رو از محصولت حذف کردی ولی تو انبار داشت استفاده میشد:
                {', '.join(features)}"""
                extra_response = {'message': message, 'variant': 'warning'}
                # data.pop('features')
        return update_object(request, Product, data=data, extra_response=extra_response, restrict_objects=features,
                             restrict_m2m=['features'], used_product_feature_ids=used_product_feature_ids)

    def delete(self, request):
        return delete_base(request, Product)


class ProductFeatureView(TableView):
    permission_required = 'server.view_productfeature'

    def get(self, request):
        params = get_params(request)
        params['order'].append('feature_id')
        params['distinct'] = True
        if not request.GET.get('product_id', None):
            return JsonResponse({'data': []})
        return JsonResponse(serialized_objects(request, ProductFeature, ProductFeatureASchema, ProductFeatureASchema,
                                               error_null_box=False, params=params))


class DiscountCodeView(AdminView):
    def get(self, request):
        params = get_params(request, box_key='storage__product__box_id')
        new_params = {'not_used': 'invoice__isnull'}
        params['filter'] = translate_params(params['filter'], new_params)
        if params['filter'].pop('html', None):
            if params['filter'].pop('redirect', None):
                s = request.step
                discount_codes = list(
                    DiscountCode.objects.filter(**params['filter'])[:s].values_list('code', flat=True))
                ipp = 84  # item per page
                discount_codes = [discount_codes[n * ipp: (n + 1) * ipp] for n in
                                  range(int(len(discount_codes) / ipp) + 1)]
                return render_to_response('discount_code.html', {'discount_codes': discount_codes})
            return JsonResponse({'url': HOST + request.get_full_path() + '&redirect=true'})
        return JsonResponse(serialized_objects(request, DiscountCode, DiscountASchema, DiscountASchema,
                                               required_fields=['storage_id'], box_key='storage__product__box_id',
                                               params=params))

    def post(self, request):
        data = json.loads(request.body)
        storage_id = data['storage_id']
        count = data['count']
        code_len = data.get('len', 5)
        storage = Storage.objects.get(pk=storage_id)
        prefix = data.get('prefix', storage.title['fa'][:2])
        codes = [prefix + '-' + get_random_string(code_len, random_data) for c in range(count)]
        while len(set(codes)) < count:
            codes = list(set(codes))
            codes += [prefix + '-' + get_random_string(code_len, random_data) for c in range(count - len(set(codes)))]
        user = request.user
        items = [DiscountCode(code=code, storage=storage, created_by=user, updated_by=user) for code in codes]
        discount_codes = DiscountCode.objects.bulk_create(items)
        storage.available_count_for_sale = DiscountCode.objects.filter(storage=storage, invoice__isnull=True).count()
        storage.available_count = storage.available_count_for_sale
        storage.save()
        return JsonResponse({'data': DiscountASchema().dump(discount_codes, many=True)})


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

    def get_old(self, request):
        with open("test.json", "r", encoding="utf-8") as read_file:
            icons = json.load(read_file)
        return JsonResponse(icons)

    def get(self, request):
        Storage.objects.filter(deadline__lt=timezone.now(), disable=False).update(disable=True)
        required_fields = ['id', 'name', 'type', 'manage', 'default_storage_id', 'has_selectable_feature',
                           'booking_type', 'thumbnail', 'storages']
        extra_data = []
        box_key = 'product__box'
        params = get_params(request, box_key)
        if request.GET.get('product_type[]'):
            product_type = request.GET.getlist('product_type[]')
            params['filter']['product__type__in'] = product_type
            del params['filter']['product_type__in']
        if not params['filter'].get(box_key):
            box_check = get_box_permission(request, box_key)
            params['filter'] = {**params['filter'], **box_check}
        params['order'] = ['-priority']
        data = {}
        if not params['filter'].get('product_only', None):
            params['filter'].pop('product_only', None)
            data = serialized_objects(request, Storage, StorageASchema, StorageESchema, box_key,
                                      params=params, error_null_box=False)
        try:
            try:
                product_id = int(request.GET.get('product_id', None) or data.get('data').get('product_id'))
            except AttributeError:
                extra_data.append('box')
                product_id = Storage.objects.filter(pk=params['filter']['id']).values_list('product__id', flat=True)[0]
            product = Product.objects.get(pk=product_id)

            if params['filter'].get('id') or params['filter'].get('product_only'):
                extra_data.append('features')
            product = ProductESchema(only=[*required_fields, *extra_data], include_storage=True).dump(product)
        except TypeError:
            product = {}
        return JsonResponse({"product": product, **data})

        # if request.GET.get('product__type'):
        #     product_type = request.GET.getlist('product_type[]')
        #     print(product_type)
        #     return JsonResponse({})
        #     # product = Product.objects.get(pk=product_id)

    def post(self, request):
        data = get_data(request, require_box=True)
        if data.get('reference_id'):
            storage = Storage.objects.get(pk=data['reference_id'])
            storage.pk = None
            storage.save()

            return JsonResponse({"message": "انبارو برای تو کپی کردم :)", "variant": "success"})
        return create_object(request, Storage, box_key='product__box', error_null_box=False, data=data)

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
        params = get_params(request, box_key='box_id')
        status = params['filter'].get('status', None)
        if status:
            params['filter']['status'] = {'pending': 1, 'payed': 2, 'canceled': 3, 'rejected': 4,
                                          'sent': 5, 'ready': 6}[status]
        params['filter']['final_price__isnull'] = False
        return JsonResponse(serialized_objects(request, Invoice, InvoiceASchema, InvoiceESchema, error_null_box=False,
                                               params=params))

    def put(self, request):
        # todo limit fields for update
        return update_object(request, Invoice, require_box=False)


class BookingView(TableView):
    permission_required = 'server.view_booking'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Booking, BookingASchema, BookingESchema))

    def put(self, request):
        # todo limit fields for update
        return update_object(request, Booking)


class InvoiceProductView(TableView):
    permission_required = 'server.view_invoicestorage'

    def get(self, request):
        params = get_params(request, box_key='box_id')
        params['filter']['invoice__status__in'] = Invoice.success_status
        serializer = InvoiceStorageASchema
        if get_group(request.user) in ['superuser', 'accountants']:
            serializer = InvoiceStorageFDSchema
        return JsonResponse(serialized_objects(request, InvoiceStorage, serializer, serializer,
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


class TagGroupView(TableView):
    permission_required = 'server.view_taggroup'

    def get(self, request):
        return JsonResponse(serialized_objects(request, TagGroup, TagGroupASchema, TagGroupASchema))

    def post(self, request):
        # data = get_data(request)
        # tags = []
        # for tag in data['tags']:
        #     tags.append({'tag_id': tag, 'show': False})
        # data['tags'] = tags
        return create_object(request, TagGroup, serializer=TagGroupASchema)

    def put(self, request):
        return update_object(request, TagGroup, serializer=TagGroupASchema, return_item=True)

    def delete(self, request):
        return delete_base(request, TagGroup)


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
    rm_list = ['email', 'password', 'is_ban', 'is_active', 'privacy_agreement', ]

    def get(self, request):
        params = get_params(request)
        params['filter']['is_supplier'] = True
        return JsonResponse(serialized_objects(request, User, SupplierESchema, SupplierESchema, error_null_box=False,
                                               params=params))

    def post(self, request):
        data = get_data(request, require_box=False)
        data['is_supplier'] = True
        [data.pop(k, None) for k in self.rm_list]
        message = f"{data['first_name']} {data['last_name']}\n{data['shaba']}\n{data['settings']}"
        send_email('MT new supplier', 'soheilravasani@gmail.com', message=message)
        return create_object(request, User, serializer=SupplierESchema, error_null_box=False,
                             data=data, return_item=True)


class Tax(AdminView):
    permission_required = 'server.view_invoice_storage'

    def get(self, request):
        # todo
        params = get_params(request, date_key='invoice__payed_at')
        # params['aggregate'] = {'tax': Sum('tax')}
        return JsonResponse(serialized_objects(request, InvoiceStorage, InvoiceStorageASchema))
