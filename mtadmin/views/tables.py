from statistics import mean, StatisticsError

from django.shortcuts import render_to_response

from mtadmin.serializer import *
from mtadmin.utils import *
from server.models import Media


# from server.models import Product


class CategoryView(TableView):
    permission_required = 'server.view_category'

    def get(self, request):
        params = get_params(request, 'category_id')
        parent_id = params['filter'].get('parent_id')
        pk = request.GET.get('id', None)
        if pk:
            data = serialized_objects(request, Category, single_serializer=CategoryESchema, category_key='id')
            return JsonResponse(data)
        # todo external categories, permalink__isnull=True,
        categories = Category.objects.filter(**params['filter']).order_by(*params['order'])
        if not categories:
            return JsonResponse({'data': []})
        has_access(request.user, categories[0].parent)
        for category in categories:
            category.child_count = self.get_child_count(category)
            category.category_child_product_count = self.get_category_product_count(category)
            category.product_count = Product.objects.filter(categories=category).count()
        return JsonResponse(get_pagination(request, categories, CategoryASchema, request.all))

    def post(self, request):
        data = get_data(request)
        required_fields = ['parent_id']
        check_required_fields(data, required_fields)
        data.pop('promote', None)
        return create_object(request, Category, serializer=CategoryASchema, return_item=True, category_key='id',
                             data=data)

    def put(self, request):
        data = get_data(request)
        if data.get('parent_id', None) is None:
            raise ValidationError("دسته بندی والد نمیتواند خالی باشد")
        data.pop('promote', None)
        category = update_object(request, Category, return_item=True, serializer=CategoryASchema, category_key='id',
                                 data=data)
        cache.set('categories', get_categories(), 3000000)
        return category

    def delete(self, request):
        return delete_base(request, Category)

    def get_child_count(self, category):
        return Category.objects.filter(parent=category).count()

    def get_category_product_count(self, category):
        return Product.objects.filter(categories=category).count()


class DateRangeView(TableView):
    permission_required = 'server.view_daterange'

    def get(self, request):
        return JsonResponse(
            serialized_objects(request, DateRange, DateRangeASchema, error_null_category=False))

    def post(self, request):
        return create_object(request, DateRange, return_item=True, serializer=DateRangeASchema,
                             error_null_category=False)

    def put(self, request):
        return update_object(request, DateRange, return_item=True, serializer=DateRangeASchema, require_category=False)


class BrandView(TableView):
    permission_required = 'server.view_brand'

    def get(self, request):
        params = get_params(request, 'category_id')
        if params['annotate']:
            params['filter'].pop('category_id', None)
            brands = Brand.objects.annotate(**params['annotate']).filter(**params['filter']).order_by(*params['order'])
        elif 'category_id' in params['filter']:
            products = Product.objects.filter(category_id=params['filter']['category_id'])
            brands = [product.brand for product in products.order_by('brand_id').distinct('brand_id') if product.brand]
        else:
            brands = Brand.objects.all().order_by(*params['order'])
        return JsonResponse(get_pagination(request, brands, BrandASchema, show_all=request.all))

    def post(self, request):
        return create_object(request, Brand, return_item=True, serializer=BrandASchema, error_null_category=False)

    def put(self, request):
        return update_object(request, Brand, return_item=True, serializer=BrandASchema, require_category=False)

    def delete(self, request):
        return delete_base(request, Brand, require_category=False)


class FeatureView(TableView):
    permission_required = 'server.view_feature'

    def get(self, request):
        return JsonResponse(
            serialized_objects(request, Feature, FeatureASchema, FeatureASchema, error_null_category=False))

    def post(self, request):
        data = get_data(request, require_category=True)
        feature_type = [v[0] for i, v in enumerate(Feature.types) if v[1] == data['type']][0]
        feature = Feature.objects.filter(name__fa=data['name']['fa'], type=feature_type)
        if feature.exists():
            return JsonResponse({'data': FeatureASchema().dump(feature.first())}, status=200)
        return create_object(request, Feature, serializer=FeatureASchema, error_null_category=False)

    def put(self, request):
        if json.loads(request.body)['id'] == color_feature_id:
            return JsonResponse({'message': "برای تغییر این فیچر با پشتیبان تماس بگیرید", 'variant': 'Error'})
        return update_object(request, Feature, serializer=FeatureASchema, require_category=False, return_item=True,
                             restrict_m2m=['features'])

    def patch(self, request):
        check_user_permission(request.user, 'change_feature')
        data = get_data(request, require_category=False)
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
                                               error_null_category=False))

    def post(self, request):
        return create_object(request, FeatureValue, serializer=FeatureValueASchema, error_null_category=False,
                             return_item=True)

    def put(self, request):
        return update_object(request, FeatureValue, serializer=FeatureValueASchema, require_category=False,
                             return_item=True)

    def delete(self, request):
        return delete_base(request, FeatureValue)


class FeatureGroupView(TableView):
    permission_required = 'server.view_featuregroup'

    def get(self, request):
        required_category = {'error_null_category': True}
        if request.GET.get('id', None) or request.GET.get('name__fa', None):
            required_category = {'error_null_category': False}
        return JsonResponse(serialized_objects(request, FeatureGroup, FeatureGroupASchema, FeatureGroupASchema,
                                               category_key='category', **required_category))

    def post(self, request):
        return create_object(request, FeatureGroup, serializer=FeatureGroupASchema, category_key='category')

    def put(self, request):
        return update_object(request, FeatureGroup, serializer=FeatureGroupASchema, category_key='category')

    def delete(self, request):
        return delete_base(request, Feature)


class ProductView(TableView):
    permission_required = 'server.view_product'

    # todo clean
    def get(self, request):
        types = request.GET.getlist('type[]')
        types2 = []
        params = get_params(request, 'category_id')
        new_params = {'available': 'storages__available_count_for_sale__gt', 'state': 'review__state'}
        params['filter'] = translate_params(params['filter'], new_params)
        required_category = {'error_null_category': True}
        for t in types:
            types2.append({'service': 1, 'product': 2, 'tourism': 3, 'package': 4, 'package_item': 5}[t])
            params['filter'].pop('type__in')
            params['filter']['type__in'] = types2
        if 'review__isnull' in params['filter']:
            required_category = {'error_null_category': False}
        if params['filter'].get('only_id', False) and params['filter'].get('category_id', False):
            params['filter'].pop('only_id')
            return JsonResponse({'data': list(Product.objects.filter(**params['filter']).order_by('id').distinct('id')
                                              .values_list('id', flat=True))})
        return JsonResponse(serialized_objects(request, Product, ProductASchema, ProductESchema, params=params,
                                               category_key='category', **required_category))

    def post(self, request):
        data = get_data(request, require_category=True)
        return create_object(request, Product, serializer=ProductESchema, category_key='category', data=data)

    def put(self, request):
        data = get_data(request, require_category=True)
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
        notif = data.pop('notif', True)
        return update_object(request, Product, data=data, extra_response=extra_response, restrict_objects=features,
                             restrict_m2m=['features'], used_product_feature_ids=used_product_feature_ids, notif=notif,
                             serializer=ProductESchema, category_key='category')

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
                                               error_null_category=False, params=params))


class DiscountCodeView(AdminView):
    permission_required = 'server.view_discountcode'

    def get(self, request):
        params = get_params(request, category_key='storage__product__category')
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
                                               required_fields=['storage_id'],
                                               category_key='storage__product__category',
                                               params=params))

    def post(self, request):
        data = json.loads(request.body)
        if data.get('type', None) == 3 and request.user.is_superuser:
            code = get_random_string(10, random_data)
            user = User.objects.get(username=data['username'])
            DiscountCode.objects.create(code=code, type=3, created_by=user, updated_by=user)
            return JsonResponse({'code': code}, status=201)
        user = request.user
        storage_id = data['storage_id']
        count = data['count']
        code_len = data.get('len', 5)
        storage = Storage.objects.get(pk=storage_id)
        category = storage.product.category
        has_access(user, category)
        prefix = data.get('prefix', storage.title['fa'][:2])
        codes = [prefix + '-' + get_random_string(code_len, random_data) for c in range(count)]
        while len(set(codes)) < count:
            codes = list(set(codes))
            codes += [prefix + '-' + get_random_string(code_len, random_data) for c in range(count - len(set(codes)))]
        items = [DiscountCode(code=code, storage=storage, created_by=user, updated_by=user) for code in codes]
        discount_codes = DiscountCode.objects.bulk_create(items)
        storage.available_count_for_sale = DiscountCode.objects.filter(storage=storage, invoice__isnull=True).count()
        storage.available_count = storage.available_count_for_sale
        storage.save()
        return JsonResponse({'data': DiscountASchema().dump(discount_codes, many=True)}, status=201)

    def delete(self, request):
        ids = request.GET.getlist('ids')
        discount_codes = DiscountCode.objects.filter(pk__in=ids, basket=None, invoice=None)
        discount_codes.delete()
        return JsonResponse({})


class ManualDiscountCodeView(AdminView):
    permission_required = 'server.view_discountcode'

    def post(self, request):
        data = json.loads(request.body)
        user = request.user
        items = [DiscountCode(code=code, storage_id=data['storage_id'], created_by=user,
                              updated_by=user) for code in data['codes']]
        DiscountCode.objects.bulk_create(items)
        return JsonResponse({}, status=201)

class HouseView(TableView):
    permission_required = 'server.view_house'

    # todo get single house like storage
    def get(self, request):
        return JsonResponse(
            serialized_objects(request, House, HouseESchema, HouseESchema, category_key='product__category'))

    def post(self, request):
        return create_object(request, House, serializer=HouseESchema, category_key='product__category')

    def put(self, request):
        return update_object(request, House, category_key='product__category')

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
        # required_fields = ['id', 'name', 'type', 'manage', 'default_storage_id', 'has_selectable_feature',
        #                    'booking_type', 'thumbnail', 'storages', 'category', 'media']
        required_fields = ['id', 'name', 'type', 'manage', 'default_storage_id', 'has_selectable_feature',
                           'booking_type', 'category', 'media']
        extra_data = []
        category_key = 'product__category'
        params = get_params(request, category_key)
        params['order'] = ['-priority']
        data = serialized_objects(request, Storage, StorageASchema, StorageESchema, category_key,
                                  params=params, error_null_category=False)
        # if not params['filter'].get('product_only', None):
        #     params['filter'].pop('product_only', None)
        #     data = serialized_objects(request, Storage, StorageASchema, StorageESchema, category_key,
        #                               params=params, error_null_category=False)
        #     return JsonResponse({**data})
        try:
            try:
                product_id = int(request.GET.get('product_id', None) or data.get('data').get('product_id'))
            except AttributeError:
                # extra_data.append('category')
                product_id = Storage.objects.filter(pk=params['filter']['id']).values_list('product__id', flat=True)[0]
            product = Product.objects.filter(pk=product_id).select_related('thumbnail', 'category').first()

            if params['filter'].get('id') or params['filter'].get('product_only'):
                extra_data.append('features')
            product = ProductESchema(only=[*required_fields, *extra_data], include_storage=True).dump(product)
        except TypeError:
            product = {}

        # data features is in use
        return JsonResponse({"product": product, **data})

        # if request.GET.get('product__type'):
        #     product_type = request.GET.getlist('product_type[]')
        #     print(product_type)
        #     return JsonResponse({})
        #     # product = Product.objects.get(pk=product_id)

    def post(self, request):
        data = get_data(request, require_category=True)
        if data.get('reference_id'):
            storage = Storage.objects.get(pk=data['reference_id'])
            storage.pk = None
            storage.save()
            return JsonResponse({"message": "انبارو برای تو کپی کردم :)", "variant": "success"})
        return create_object(request, Storage, category_key='product__category', error_null_category=False, data=data,
                             serializer=StorageASchema)

    def put(self, request):
        data = get_data(request, require_category=True)
        return update_object(request, Storage, require_category=False, category_key='product__category', data=data,
                             serializer=StorageASchema)

    def delete(self, request):
        return delete_base(request, Storage)


class PackageView(TableView):
    permission_required = 'server.view_package'

    def get(self, request):
        params = get_params(request, category_key='product__category')
        params['filter']['product__type'] = 4
        return JsonResponse(serialized_objects(request, Storage, PackageASchema, category_key='product__category',
                                               params=params))

    def post(self, request):
        return create_object(request, Package, serializer=PackageASchema, category_key='package__product__category')

    def put(self, request):
        return update_object(request, Package, category_key='package__product__category')

    def delete(self, request):
        return delete_base(request, Package)


class VipPriceView(TableView):
    permission_required = 'server.view_vip_price'

    def get(self, request):
        return JsonResponse(serialized_objects(request, VipPrice, VipPriceASchema, VipPriceASchema,
                                               category_key='storage__product__category'))

    def post(self, request):
        return create_object(request, VipPrice, category_key='storage__product__category')

    def put(self, request):
        return update_object(request, VipPrice, category_key='storage__product__category')

    def delete(self, request):
        return delete_base(request, VipPrice)


class VipTypeView(TableView):
    permission_required = 'server.view_viptype'

    def get(self, request):
        return JsonResponse(serialized_objects(request, VipType, VipTypeASchema, error_null_category=False))


class InvoiceView(TableView):
    permission_required = 'server.view_invoice'

    def get(self, request):
        params = get_params(request, category_key='category')
        if params['filter'].pop('only_booking', None):
            params['filter']['start_date__isnull'] = False
        params['filter']['final_price__isnull'] = False
        status = params['filter'].get('status', None)
        if status:
            params['filter']['status'] = {'pending': 1, 'payed': 2, 'canceled': 3, 'rejected': 4,
                                          'sent': 5, 'ready': 6}[status]

        return JsonResponse(
            serialized_objects(request, Invoice, InvoiceASchema, InvoiceESchema, error_null_category=False,
                               params=params))

    def put(self, request):
        # todo limit fields for update
        return update_object(request, Invoice, serializer=InvoiceASchema, require_category=False)


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
        params = get_params(request, category_key='category')
        params['filter']['invoice__status__in'] = Invoice.success_status
        if params['filter'].pop('only_booking', None):
            params['filter']['invoice__start_date__isnull'] = False
        serializer = InvoiceStorageASchema
        if request.user.is_superuser or get_group(request.user) in ['superuser', 'accountants']:
            serializer = InvoiceStorageFDSchema
        return JsonResponse(serialized_objects(request, InvoiceStorage, serializer, serializer,
                                               error_null_category=False, params=params))

    def put(self, request):
        return update_object(request, InvoiceStorage, require_category=False, category_key='category')


class MenuView(TableView):
    permission_required = 'server.view_menu'

    def get(self, request):
        return JsonResponse(serialized_objects(request, Menu, MenuASchema, MenuESchema))

    def post(self, request):
        return create_object(request, Menu, serializer=MenuASchema)

    def put(self, request):
        return update_object(request, Menu, serializer=MenuASchema)

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
        return create_object(request, Tag, category_key=None, return_item=True, serializer=TagASchema,
                             error_null_category=False)

    def put(self, request):
        return update_object(request, Tag, serializer=TagASchema, require_category=False, return_item=True)

    def delete(self, request):
        return delete_base(request, Tag)


class TagGroupView(TableView):
    permission_required = 'server.view_taggroup'

    def get(self, request):
        return JsonResponse(serialized_objects(request, TagGroup, TagGroupASchema, TagGroupASchema,
                                               category_key='category'))

    def post(self, request):
        # data = get_data(request)
        # tags = []
        # for tag in data['tags']:
        #     tags.append({'tag_id': tag, 'show': False})
        # data['tags'] = tags
        return create_object(request, TagGroup, serializer=TagGroupASchema, category_key='category')

    def put(self, request):
        return update_object(request, TagGroup, serializer=TagGroupASchema, return_item=True, category_key='category')

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
        data = serialized_objects(request, SpecialProduct, serializer=SpecialProductASchema,
                                  single_serializer=SpecialProductESchema, category_key='category')
        for index, item in enumerate(data['data']):
            data['data'][index]['product']['default_storage'] = data['data'][index].pop('default_storage')
            data['data'][index].pop('default_storage', None)
        return JsonResponse(data)

    def post(self, request):
        return create_object(request, SpecialProduct, serializer=SpecialProductESchema, category_key='category')

    def put(self, request):
        return update_object(request, SpecialProduct, serializer=SpecialProductASchema, category_key='category')

    def delete(self, request):
        # todo make it global
        pk = request.GET.get('id')
        item = SpecialProduct.objects.get(pk=pk)
        item.safe_delete(request.user.id)
        return JsonResponse({'message': 'با موفقیت حذف شد'})


class MediaView(TableView):
    permission_required = 'server.view_media'

    def get(self, request):
        no_category = [4, 5, 6]
        require_category = {}
        params = get_params(request, 'category_id')
        try:
            if int(params['filter']['type']) in no_category:
                require_category = {'error_null_category': False}
        except Exception:
            pass
        return JsonResponse(serialized_objects(request, Media, MediaASchema, MediaESchema, **require_category,
                                               category_key='category_id'))

    def post(self, request):
        data = json.loads(request.POST.get('data'))
        titles = data['titles']
        category_id = data.get('category_id', None)
        category = None
        if category_id:
            category = Category.objects.get(pk=category_id)
        media_type = data['type']
        if (media_type not in Media.no_category_type) and (not has_access(request.user, category.id)):
            raise PermissionDenied

        media = upload(request, titles, media_type, category_id)
        if media:
            return JsonResponse({'media': MediaASchema().dump(media, many=True)})
        return JsonResponse({}, status=res_code['bad_request'])

    def patch(self, request):
        data = json.loads(request.body)
        title = data['title']
        pk = data['id']
        media = Media.objects.filter(pk=pk).first()
        if (media.type not in Media.no_category_type) and (not has_access(request.user, media.category_id)):
            raise PermissionDenied
        media.title = title
        media.save()
        return JsonResponse({'media': MediaASchema().dump(media)})

    def delete(self, request):
        return delete_base(request, Media)

    # def has_access(self, user, category_id):
    #     return user_


class CommentView(TableView):
    permission_required = 'server.view_comment'

    def get(self, request):
        return JsonResponse(
            serialized_objects(request, Comment, CommentASchema, CommentESchema, error_null_category=False))

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
        return JsonResponse(
            serialized_objects(request, Ad, AdASchema, AdASchema, error_null_category=False, params=params))

    def post(self, request):
        return create_object(request, Ad, error_null_category=False, serializer=AdASchema)

    def patch(self, request):
        priorities = json.loads(request.body)['priorities']
        Ad.objects.update(priority=0)
        [Ad.objects.filter(pk=pk).update(priority=priorities.index(pk)) for pk in priorities]
        return JsonResponse({'message': 'باموفقیت ذخیرته شد'})

    def put(self, request):
        return update_object(request, Ad, serializer=AdASchema, require_category=False)

    def delete(self, request):
        return delete_base(request, Ad)


class SliderView(TableView):
    permission_required = 'server.view_slider'

    def get(self, request):
        params = get_params(request)
        if params['filter'].get('priority') == 'true':
            params['filter']['priority__isnull'] = False
            params['filter'].pop('priority')
        return JsonResponse(serialized_objects(request, Slider, SliderASchema, SliderASchema, error_null_category=False,
                                               params=params))

    def post(self, request):
        return create_object(request, Slider, serializer=SliderASchema, error_null_category=False)

    def patch(self, request):
        priorities = json.loads(request.body)['priorities']
        Slider.objects.update(priority=None)
        [Slider.objects.filter(pk=pk).update(priority=priorities.index(pk)) for pk in priorities]
        return JsonResponse({'message': 'باموفقیت ذخیرته شد'})

    def put(self, request):
        return update_object(request, Slider, serializer=SliderASchema, require_category=False)

    def delete(self, request):
        return delete_base(request, Slider)


class SupplierView(TableView):
    permission_required = 'server.view_user'
    rm_list = ['email', 'password', 'is_ban', 'is_active', 'privacy_agreement', ]

    def get(self, request):
        params = get_params(request)
        params['filter']['is_supplier'] = True
        return JsonResponse(
            serialized_objects(request, User, SupplierESchema, SupplierESchema, error_null_category=False,
                               params=params))

    def post(self, request):
        data = get_data(request, require_category=False)
        data['is_supplier'] = True
        [data.pop(k, None) for k in self.rm_list]
        message = f"{data['first_name']} {data['last_name']}\n{data['shaba']}\n{data['settings']}"
        # send_email('MT new supplier', 'soheilravasani@gmail.com', message=message)
        send_pm(312145983, message='MT new supplier\n\n' + message)
        return create_object(request, User, serializer=SupplierESchema, error_null_category=False,
                             data=data, return_item=True)


class Tax(AdminView):
    permission_required = 'server.view_invoice_storage'

    def get(self, request):
        # todo
        params = get_params(request, date_key='invoice__payed_at')
        # params['aggregate'] = {'tax': Sum('tax')}
        return JsonResponse(serialized_objects(request, InvoiceStorage, InvoiceStorageASchema))


class UserView(TableView):
    permission_required = 'server.view_user'

    def get(self, request):
        return JsonResponse(serialized_objects(request, User, UserASchema, UserASchema, error_null_category=False))
