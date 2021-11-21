import collections
from collections import Counter
from itertools import groupby
from operator import attrgetter as ga
from operator import itemgetter

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Exists
from django.db.models import Prefetch
from django.http import JsonResponse
from toolz import unique

from server.serialize import *
from server.utils import LoginRequired
from server.utils import View, get_pagination, load_data, get_preview_permission


class ProductView(View):
    def get(self, request, permalink):
        identifier = {'permalink': permalink}
        product_identifier = {'product__permalink': permalink}
        storage_product_identifier = {'storages__product__permalink': permalink}
        if F"{permalink}".isdecimal():
            identifier = {'id': permalink}
            product_identifier = {'product_id': permalink}
            storage_product_identifier = {'storages__product_id': permalink}
        # user = User.objects.get(pk=1)
        # login(request, user)
        params = request.GET
        storages = params.get('include_storages')
        exclude = ['category.media', 'storages']
        if storages:
            exclude = ['category.media']
        user = request.user
        product_preview = get_preview_permission(user)
        storage_preview = get_preview_permission(user, box_check=False, category_check=False)
        try:
            product_obj = Product.objects.filter(**identifier, **product_preview). \
                annotate(review_count=Count('reviews'),
                         wish=Exists(WishList.objects.filter(user=user, wish=True, **product_identifier)),
                         notify=Exists(WishList.objects.filter(user=user, notify=True, **product_identifier)),
                         purchased=Exists(
                             Invoice.objects.filter(user=user, status=2, **storage_product_identifier))). \
                select_related('thumbnail', 'category', 'brand'). \
                prefetch_related('product_tags__tag', 'tag_groups__tag_group_tags__tag', 'categories__parent').first()
        except TypeError:
            product_obj = Product.objects.filter(**identifier, **product_preview). \
                annotate(review_count=Count('reviews')). \
                select_related('thumbnail', 'category', 'brand'). \
                prefetch_related('product_tags__tag', 'tag_groups__tag_group_tags__tag', 'categories__parent').first()
            if product_obj is None:
                return JsonResponse({'message': 'محصول موقتا غیرفعال میباشد', 'variant': 'error'}, status=404)
            product_obj.purchased = False
            product_obj.notify = False
            product_obj.wish = False
        features = self.get_features(product_obj, request.lang)
        # features = []
        if product_obj is None:
            return JsonResponse({'message': 'محصول موقتا غیرفعال میباشد', 'variant': 'error'}, status=404)
        # purchased = False
        product = ProductSchema(**request.schema_params, exclude=exclude).dump(product_obj)
        # if product_obj.type < 3:
        #     storages = product_obj.storages.filter(Q(start_time__lte=timezone.now()) & Q(**storage_preview),
        #                                            (Q(deadline__gte=timezone.now()) | Q(deadline__isnull=True)))
        # product['storages'] = StorageSchema(**request.schema_params).dump(storages, many=True)
        # if user.is_authenticated:
        #     purchased = self.purchase_status(user, storages)
        if product_obj.type == 3:
            product['house'] = HouseSchema(**request.schema_params).dump(product_obj.house)
        elif product_obj.type == 4:
            storages = product_obj.storages.filter(Q(start_time__lte=timezone.now()) & Q(**storage_preview),
                                                   (Q(deadline__gte=timezone.now()) | Q(deadline__isnull=True)))
            product['storages'] = PackageSchema(**request.schema_params).dump(storages, many=True)
        # product['categories'] = [self.get_category(c) for c in product['categories']]
        # wish = WishList.objects.filter(product=product_obj, wish=True).exists()
        # notify = WishList.objects.filter(product=product_obj, notify=True).exists()
        return JsonResponse({'product': product, 'purchased': product_obj.purchased, 'features': features,
                             'wish': product_obj.wish, 'notify': product_obj.notify})

    def get_features(self, product, lang):
        if not product:
            return {'group_features': [], 'features': []}
        category_feature_groups = FeatureGroup.objects.filter(
            categories__in=list(product.categories.values_list('id', flat=True)), settings__ui__show_title=True)
        category_feature_groups = FeatureGroupSchema().dump(category_feature_groups, many=True)
        product_features = ProductFeature.objects.filter(Q(product=product), Q(feature__type__in=[1, 2]) |
                                                         Q(feature__type=3)) \
            .select_related('feature', 'feature_value'). \
            annotate(feature_groups=ArrayAgg('feature__groups'), test=F('product_feature_storages'))
        used_features = [pf.feature_id for pf in product_features if pf.test]
        product_features = [pf for pf in product_features if pf.feature_id not in used_features]
        product_features = ProductFeatureSchema(list_of_values=True).dump(product_features, many=True)
        unique_product_features = list(unique(product_features, key=lambda o: o['feature']))
        if len(product_features) != len(unique_product_features):
            features = [pf['feature'] for pf in product_features]
            features_count = dict(collections.Counter(features))
            duplicate_features = [feature for feature, count in features_count.items() if count > 1]
            for df in duplicate_features:
                dfs = [pf for pf in product_features if pf['feature'] == df]
                for feature in dfs[1:]:
                    dfs[0]['feature_value'] += feature['feature_value']
                    product_features.pop(product_features.index(feature))

        product_features_copy = product_features.copy()  # cant remove item from "list in for"
        for pf in product_features:
            is_grouped_pf = False
            for cfg in category_feature_groups:
                if cfg['id'] in pf['feature_groups']:
                    cfg['features'].append(pf)
                    is_grouped_pf = True
            if is_grouped_pf:
                product_features_copy.pop(product_features_copy.index(pf))
        return {'group_features': category_feature_groups, 'features': product_features_copy}

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


class ProductWishlist(LoginRequired):
    def get(self, request, product_id):
        user = request.user
        wishlist = WishList.objects.filter(user=user, product_id=product_id).values('wish', 'notify')
        wishlist = list(wishlist)[0]
        purchased = Invoice.objects.filter(user=user, status=2, storages__product_id=product_id).exists()
        return JsonResponse({"purchased": purchased, **wishlist})


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
        comment_type = request.GET.get('type', None)
        filterby = {}
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
        identifier = {'permalink': permalink}
        if permalink.isdecimal():
            identifier = {'id': permalink}
        storage_preview = get_preview_permission(request.user, box_check=False, product_check=True)
        product_preview = get_preview_permission(request.user, box_check=False)
        product = Product.objects.filter(**identifier, **product_preview).first()
        if product.unavailable:
            storages = product.storages.filter(**storage_preview)
            storages = MinStorageSchema(only=['name']).dump(storages, many=True)
            return JsonResponse({'storage': storages})
        if product.type == 1:
            all_storages = product.storages.filter(**storage_preview)
            storages = all_storages.prefetch_related('vip_prices', Prefetch('storage_accessories',
                                                                            queryset=StorageAccessories.objects.filter(
                                                                                storage__in=all_storages)
                                                                            .select_related(
                                                                                'accessory_product__thumbnail',
                                                                                'accessory_storage'),
                                                                            to_attr='accessory'))
            storages = StorageSchema(exclude=['features']).dump(storages, many=True)
            return JsonResponse({'storage': storages})
        product = Product.objects.filter(**identifier, **product_preview).select_related('default_storage'). \
            annotate(storages_count=Count('storages'),
                     active_storages_count=Count('storages', filter=Q(storages__unavailable=False,
                                                                      storages__disable=False,
                                                                      storages__available_count_for_sale__gt=0))). \
            prefetch_related('product_features__product_feature_storages__storage__vip_prices__vip_type',
                             'product_features__feature', 'default_storage__vip_prices__vip_type',
                             'product_features__feature_value').first()
        selected = request.GET.getlist('select[]')
        # todo temp solution
        try:
            selected = list(map(int, selected))
        except ValueError:
            selected = [int(selected[0]), selected[1][1:].split(',')[0]]
        # product = Product.objects.get(pk=513)
        # product_features = ProductFeature.objects.filter(product=product, feature__type=3)  # selectable
        product_features = product.product_features.all()  # selectable
        product_features = [pf for pf in product_features if pf.feature.type == 3]
        if product.active_storages_count == 0:
            return JsonResponse({'features': [], 'storage': {}})
        if not product_features or product.storages_count == 1:
            try:
                storage = StorageSchema(**request.schema_params).dump(product.default_storage)
                return JsonResponse({'features': [], 'storage': storage})
            except IndexError:
                return JsonResponse({'features': [], 'storage': {}})
        # feature_count = collections.Counter(product_features.values_list('feature_id', flat=True)).items()
        feature_count = collections.Counter([pf.feature_id for pf in product_features]).items()
        multi_select_features = [item for item, count in feature_count if count > 1]
        # product_features = product_features.filter(feature_id__in=multi_select_features)
        product_features = [pf for pf in product_features if pf.feature_id in multi_select_features]
        all_pfs = ProductFeatureStorage.objects.filter(product_feature__in=product_features,
                                                       # storage__available_count_for_sale__gt=0,
                                                       # storage__unavailable=False,
                                                       storage__disable=False) \
            .select_related('storage', 'product_feature').order_by('product_feature_id')
        product_feature_storages = [pfs for pfs in all_pfs
                                    if pfs.storage.available_count_for_sale > 0 and pfs.storage.unavailable is False]

        if selected:
            # selected_pfs = product_feature_storages.filter(product_feature_id__in=selected)
            selected_pfs = [pfs for pfs in product_feature_storages if pfs.product_feature_id in selected]
            # default_storage = selected_pfs.first().storage
            default_storage = next(iter(collections.Counter(selected_pfs).most_common()))[0].storage
            # for pfs in selected_pfs.order_by('storage_id').distinct('storage_id'):
            # for pfs in selected_pfs:
            #     if selected_pfs.filter(storage=pfs.storage).count() > selected_pfs.filter(storage=default_storage).count():
            #         default_storage = selected_pfs.filter(storage=pfs.storage).first().storage

        else:
            try:
                # default_storage = min(product_feature_storages, key=attrgetter('storage.discount_price')).storage
                default_storage = product.default_storage
            except ValueError:
                # storage = StorageSchema(**request.schema_params).dump(product.default_storage)
                # return JsonResponse({'features': [], 'storage': storage})
                return JsonResponse({'features': [], 'storage': {}})
            # selected = list(product_feature_storages.filter(storage=default_storage).values_list('product_feature_id',
            #                                                                                      flat=True))
            selected = [pfs.product_feature_id for pfs in product_feature_storages if pfs.storage == default_storage]
        features_list = self.get_features(product_features, product_feature_storages, all_pfs, default_storage,
                                          selected)
        return JsonResponse({'features': features_list,
                             'storage': StorageSchema(exclude=['features']).dump(default_storage)})

    def get_features(self, product_features, product_feature_storages, all_pfs, default_storage=None, selected=None):
        if not selected:
            selected = []
        features_list = []
        # product_features_distinct = product_features.order_by('feature_id').distinct('feature_id')
        # product_features_distinct = [next(g) for k, g in groupby(product_features, key=ga('feature_id'))]
        product_features_distinct = []
        for product_feature in product_features:
            if not next((pf for pf in product_features_distinct if pf.feature_id == product_feature.feature_id), None):
                product_features_distinct.append(product_feature)
        all_pfs_distinct = [next(g) for k, g in groupby(all_pfs, key=ga('storage_id'))]
        # selected_feature = list(
        #     product_feature_storages.filter(storage=default_storage).values_list('product_feature_id', flat=True))
        selected_feature = [pfs.product_feature_id for pfs in all_pfs if pfs.storage ==
                            default_storage]
        available_combos = []
        all_combos = []
        feature_value_combo = []
        # for pf in product_feature_storages.order_by('storage_id').distinct('storage_id'):
        for pf in all_pfs_distinct:
            # available_combos.append(
            #     list(product_feature_storages.filter(storage_id=pf.storage_id).values_list(
            #         'product_feature_id', flat=True)))

            available_combos.append([pfs.product_feature_id for pfs in all_pfs
                                     if pfs.storage_id == pf.storage_id and pfs.storage.unavailable is False
                                     and pfs.storage.available_count_for_sale > 0])
            all_combos.append([pfs.product_feature_id for pfs in all_pfs
                               if pfs.storage_id == pf.storage_id])

            # combo = []
            # for pfs in all_pfs:
            #     if pfs.storage_id == pf.storage_id:
            #         if pfs.storage.unavailable is False and pfs.storage.available_count_for_sale > 0:
            #             combo.append(pfs.product_feature_id)
            #             continue
            #         all_combos.append(pfs.product_feature_id)
            #     available_combos.append(pfs.product_feature_id)
            # used_values_combo.append([(pfs.product_feature.feature_id, pfs.product_feature.feature_value_id) for pfs in
            #                           product_feature_storages if pfs.storage_id == pf.storage_id])
            for pfs in all_pfs:
                if pfs.storage_id == pf.storage_id:
                    feature_value_combo.append((pfs.product_feature.feature_id, pfs.product_feature.feature_value_id))
        # print(available_combos)
        # print('first selected:', selected)
        # print(selected_feature)
        feature_count = Counter(map(itemgetter(0), list(set(feature_value_combo))))
        selectable_feature = [k for k, v in feature_count.items() if v > 1]
        product_features_distinct = [pfd for pfd in product_features_distinct if pfd.feature_id in selectable_feature]
        for product_f in product_features_distinct:
            values = []
            # select = list(product_features.filter(
            #     feature=product_f.feature, pk__in=selected_feature).values_list('pk', flat=True))
            select = [pf.id for pf in product_features if pf.feature_id == product_f.feature_id and
                      pf.id in selected_feature]
            if len(select) == 0:
                continue
            # print(select)
            if len(select) < 2:
                select = select[0]
            # for pf in product_features.filter(feature=product_f.feature):
            for pf in [pf for pf in product_features if pf.feature_id == product_f.feature_id]:
                feature_dict = {}
                feature_dict['id'] = pf.id
                feature_dict['settings'] = pf.feature_value.settings.get('ui', {})
                feature_dict['name'] = pf.feature_value.value['fa']
                feature_dict['priority'] = pf.feature_value.priority
                # feature_dict['selected'] = pf.id in selected_feature or pf.id in selected
                feature_dict['available'] = False
                feature_dict['selectable'] = True if {pf.pk}.issubset(set(sum(available_combos, []))) else False
                # feature_dict['available'] = pf.feature_id in product_features.filter(pk__in=selected).values_list(
                #     'feature_id', flat=True)
                try:
                    # print('feature:', pf.id)
                    # print('feature:', pf.feature)
                    # print('selected:', selected)
                    # feature_combo = list(product_features.exclude(feature=pf.feature).filter(
                    #     pk__in=selected_feature).values_list('pk', flat=True))[0]
                    feature_combo = [pff.id for pff in product_features
                                     if pff.id in selected_feature and pff.feature_id != pf.feature_id]
                except IndexError:
                    feature_combo = -1
                for l in available_combos:
                    # if set(selected + [pf.pk]).issubset(l) or set([feature_combo] + [pf.pk]).issubset(l):
                    if set(selected + [pf.pk]).issubset(l) or set(feature_combo + [pf.pk]).issubset(l):
                        feature_dict['available'] = True
                values.append(feature_dict)
            values = sorted(values, key=lambda i: i['priority'])
            features_list.append(
                {'id': product_f.feature_id, 'name': product_f.feature.name['fa'], 'values': values,
                 'selected': select, 'settings': product_f.feature.settings})
        return features_list
