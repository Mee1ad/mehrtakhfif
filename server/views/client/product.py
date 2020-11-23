import collections

from django.http import JsonResponse

from server.serialize import *
from server.utils import View, get_pagination, load_data, get_preview_permission


class ProductView(View):
    def get(self, request, permalink):
        user = request.user
        product_preview = get_preview_permission(user)
        storage_preview = get_preview_permission(user, box_check=False, category_check=False)
        product_obj = Product.objects.filter(permalink=permalink, **product_preview).prefetch_related(
            *Product.prefetch).first()
        features = self.get_features(product_obj, request.lang)
        # features = []
        if product_obj is None:
            return JsonResponse({'message': 'محصول موقتا غیرفعال میباشد', 'variant': 'error'}, status=404)
        purchased = False
        product = ProductSchema(**request.schema_params).dump(product_obj)
        if product_obj.type < 3:
            storages = product_obj.storages.filter(Q(start_time__lte=timezone.now()) & Q(**storage_preview),
                                                   (Q(deadline__gte=timezone.now()) | Q(deadline__isnull=True)))
            product['storages'] = StorageSchema(**request.schema_params).dump(storages, many=True)
            if user.is_authenticated:
                purchased = self.purchase_status(user, storages)
        elif product_obj.type == 3:
            product['house'] = HouseSchema(**request.schema_params).dump(product_obj.house)
            # todo get purchased status
        elif product_obj.type == 4:
            storages = product_obj.storages.filter(Q(start_time__lte=timezone.now()) & Q(**storage_preview),
                                                   (Q(deadline__gte=timezone.now()) | Q(deadline__isnull=True)))
            product['storages'] = PackageSchema(**request.schema_params).dump(storages, many=True)
        # todo debug
        # product['categories'] = [self.get_category(c) for c in product['categories']]
        wish = WishList.objects.filter(product=product_obj, wish=True).exists()
        notify = WishList.objects.filter(product=product_obj, notify=True).exists()
        return JsonResponse({'product': product, 'purchased': purchased, 'features': features, 'wish': wish,
                             'notify': notify})

    def get_features(self, product, lang):
        if not product:
            return {'group_features': [], 'features': []}
        group_features = []
        features = []
        category_feature_groups = FeatureGroup.objects.filter(
            categories__in=product.categories.values_list('id', flat=True))
        product_feature_groups = product.feature_groups.all()
        feature_groups = category_feature_groups | product_feature_groups
        feature_groups_id = list(feature_groups.values_list('id', flat=True))
        # product_features = ProductFeature.objects.annotate(pfs=Count('product_feature_storages')).filter(Q(
        #     product=product), Q(feature__type__in=[1, 2]) | Q(pfs=1, feature__type=3)) \
        #     .select_related('feature', 'feature_value')
        product_features = ProductFeature.objects.filter(Q(product=product), Q(feature__type__in=[1, 2]) |
                                                         Q(product_feature_storages=None, feature__type=3)) \
            .select_related('feature', 'feature_value')

        for feature_group in feature_groups:
            # group features
            gf = product_features.filter(feature__groups__in=[feature_group.pk])
            gf = ProductFeatureSchema().dump(gf, many=True)
            group_features.append({'id': feature_group.pk, 'title': feature_group.name[lang], 'features': gf})
        f = product_features.exclude(feature__groups__in=feature_groups_id)
        features.append(ProductFeatureSchema().dump(f, many=True))
        return {'group_features': group_features, 'features': features[0]}

    def get_category(self, category):
        try:
            category['parent']['child'] = category
            if category['parent'] is not None:
                category['parent']['child']['parent_id'] = category['parent']['id']
            category = category['parent']
            del category['child']['parent']
            return self.get_category(category)
        except TypeError:
            category['parent_id'] = None
            del category['parent']
            return category

    def purchase_status(self, user, storages):
        return Invoice.objects.filter(user=user, status=2, storages__in=storages).exists()


class RelatedProduct(View):
    def get(self, request, permalink):
        product = Product.objects.get(permalink=permalink)
        tags = product.tags.all()
        products = Product.objects.filter(tags__in=tags, disable=False).order_by('-id').distinct('id')
        return JsonResponse(get_pagination(request, products, MinProductSchema))


class CommentView(View):
    def get(self, request):
        product_permalink = request.GET.get('prp', None)
        post_permalink = request.GET.get('pop', None)
        comment_id = request.GET.get('comment_id', None)
        comment_type = request.GET['type']
        if comment_id:
            comments = Comment.objects.filter(reply_to_id=comment_id)
            return JsonResponse(get_pagination(request, comments, CommentSchema))
        if product_permalink:
            try:
                product = Product.objects.get(permalink=product_permalink)
            except Product.DoesNotExist:
                return JsonResponse({}, status=404)
            filterby = {"product": product}
        elif post_permalink:
            try:
                post = BlogPost.objects.get(permalink=product_permalink)
            except BlogPost.DoesNotExist:
                return JsonResponse({}, status=404)
            filterby = {"blog_post": post}
        filterby = {"type": int(comment_type), **filterby}
        comments = Comment.objects.filter(**filterby, approved=True).exclude(reply_to__isnull=False)
        return JsonResponse(get_pagination(request, comments, CommentSchema))

    def post(self, request):
        data = load_data(request)
        reply_to_id = data.get('reply_to_id', None)
        rate = data.get('rate', None)
        satisfied = data.get('satisfied', None)
        cm_type = data['type']
        product_permalink = data.get('product_permalink')
        post = {}
        if product_permalink:
            product = Product.objects.get(permalink=product_permalink)
            post = {"product": product}
        blog_post_permalink = data.get('blog_post_permalink')
        if blog_post_permalink:
            blog_post = BlogPost.objects.get(permalink=blog_post_permalink)
            post = {"blog_post": blog_post}
        user = request.user
        res = {}
        res_code = 201
        res = {'message': 'نظر شما ثبت شد و پس از تایید نمایش داده میشود'}
        if user.first_name is None or user.last_name is None:
            try:
                user.first_name = data['first_name']
                user.last_name = data['last_name']
                user.save()
                res['user'] = UserSchema().dump(user)
            except KeyError:
                res = {'message': 'لطفا نام و نام خانوادگی را وارد نمایید', 'variant': 'error'}
                res_code = 400
        if reply_to_id:
            assert Comment.objects.filter(pk=reply_to_id).exists()
        assert post or reply_to_id
        Comment.objects.create(text=data['text'], user=request.user, reply_to_id=reply_to_id, type=cm_type,
                               rate=rate, satisfied=satisfied, created_by=user, updated_by=user, **post)
        return JsonResponse(res, status=res_code)

    def delete(self, request):
        pk = request.GET.get('id', None)
        Comment.objects.filter(pk=pk, user=request.user).delete()
        return JsonResponse({})


class FeatureView(View):

    def get(self, request, permalink):
        product = Product.objects.get(permalink=permalink)
        selected = request.GET.getlist('select[]')
        # todo temp solution
        try:
            selected = list(map(int, selected))
        except ValueError:
            selected = [int(selected[0]), selected[1][1:].split(',')[0]]
        # product = Product.objects.get(pk=513)
        product_features = ProductFeature.objects.filter(product=product, feature__type=3)  # selectable
        if not product_features:
            try:
                storage = StorageSchema(**request.schema_params).dump(product.default_storage)
                return JsonResponse({'features': [], 'storage': storage})
            except IndexError:
                return JsonResponse({'features': [], 'storage': {}})
        feature_count = collections.Counter(product_features.values_list('feature_id', flat=True)).items()
        multi_select_features = [item for item, count in feature_count if count > 1]
        product_features = product_features.filter(feature_id__in=multi_select_features)
        product_feature_storages = ProductFeatureStorage.objects.filter(product_feature__in=product_features,
                                                                        storage__available_count_for_sale__gt=0,
                                                                        storage__unavailable=False,
                                                                        storage__disable=False) \
            .order_by('product_feature_id')
        if selected:
            selected_pfs = product_feature_storages.filter(product_feature_id__in=selected)
            default_storage = selected_pfs.first().storage
            for pfs in selected_pfs.order_by('storage_id').distinct('storage_id'):
                if selected_pfs.filter(storage=pfs.storage).count() > selected_pfs.filter(
                        storage=default_storage).count():
                    default_storage = selected_pfs.filter(storage=pfs.storage).first().storage
        else:
            try:
                # default_storage = min(product_feature_storages, key=attrgetter('storage.discount_price')).storage
                default_storage = product.default_storage
            except ValueError:
                storage = StorageSchema(**request.schema_params).dump(product.default_storage)
                # return JsonResponse({'features': [], 'storage': storage})
                return JsonResponse({'features': [], 'storage': {}})
            selected = list(product_feature_storages.filter(storage=default_storage).values_list('product_feature_id',
                                                                                                 flat=True))
        features_list = self.get_features(product_features, product_feature_storages, default_storage, selected)
        return JsonResponse({'features': features_list, 'storage': StorageSchema().dump(default_storage)})

    def get_features(self, product_features, product_feature_storages, default_storage=None, selected=None):
        if not selected:
            selected = []
        features_list = []
        product_features_distinct = product_features.order_by('feature_id').distinct('feature_id')
        selected_feature = list(
            product_feature_storages.filter(storage=default_storage).values_list('product_feature_id', flat=True))
        available_combos = []
        for pf in product_feature_storages.order_by('storage_id').distinct('storage_id'):
            available_combos.append(
                list(product_feature_storages.filter(storage_id=pf.storage_id).values_list(
                    'product_feature_id', flat=True)))
        # print(available_combos)
        # print('first selected:', selected)
        # print(selected_feature)
        for product_f in product_features_distinct:
            values = []
            select = list(product_features.filter(
                feature=product_f.feature, pk__in=selected_feature).values_list('pk', flat=True))
            if len(select) == 0:
                continue
            # print(select)
            if len(select) < 2:
                select = select[0]
            for pf in product_features.filter(feature=product_f.feature):
                feature_dict = {}
                feature_dict['id'] = pf.id
                feature_dict['settings'] = pf.feature_value.settings.get('ui', {})
                feature_dict['name'] = pf.feature_value.value['fa']
                # feature_dict['selected'] = pf.id in selected_feature or pf.id in selected
                feature_dict['available'] = False
                feature_dict['selectable'] = True if {pf.pk}.issubset(set(sum(available_combos, []))) else False
                # feature_dict['available'] = pf.feature_id in product_features.filter(pk__in=selected).values_list(
                #     'feature_id', flat=True)
                try:
                    # print('feature:', pf.id)
                    # print('feature:', pf.feature)
                    # print('selected:', selected)
                    feature_combo = list(product_features.exclude(feature=pf.feature).filter(
                        pk__in=selected_feature).values_list('pk', flat=True))[0]
                except IndexError:
                    feature_combo = -1
                for l in available_combos:
                    if set(selected + [pf.pk]).issubset(l) or set([feature_combo] + [pf.pk]).issubset(l):
                        feature_dict['available'] = True
                values.append(feature_dict)
            features_list.append(
                {'id': product_f.feature_id, 'name': product_f.feature.name['fa'], 'values': values,
                 'selected': select})
        return features_list
