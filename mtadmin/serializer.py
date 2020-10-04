from django.db.models import Sum
from marshmallow import EXCLUDE

from server.serialize import *
from server.utils import *
from server.views.payment import ipg


def list_view(obj_list):
    lst = []
    for obj in obj_list:
        if type(obj) == list:
            lst.append([list_view(obj)])
        else:
            try:
                lst.append(obj.name)
            except AttributeError:
                lst.append(obj.title)


def related_objects(objects):
    res = []
    for item in objects:
        if type(item) == list:
            related_objects(item)
            continue
        item = {'model': item.__class__.__name__, 'data': item}
        res.append(item)
    return res


# ManyToMany Relations

class ProductFeatureField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        features = ProductFeature.objects.filter(product=obj)
        return ProductFeatureASchema().dump(features, many=True)


class VipPriceField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        vip_prices = VipPrice.objects.filter(storage=obj)
        return VipPriceASchema().dump(vip_prices, many=True)


class StorageField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        storages = Storage.objects.filter(product=obj)
        return StorageESchema().dump(storages, many=True)


class PackageItemsField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        items = Package.objects.filter(package_id=obj)
        return PackageItemASchema().dump(items, many=True)


class ProductTagField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        items = ProductTag.objects.filter(product=obj)
        return ProductTagASchema().dump(items, many=True)


class TagGroupField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        items = TagGroupTag.objects.filter(taggroup=obj)
        return TagGroupTagASchema().dump(items, many=True)


class ProductTagGroupField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        items = obj.tag_groups.all()
        return TagGroupASchema().dump(items, many=True)


# Serializer
class BaseAdminSchema(Schema):
    """
    E = Edit
    S = Schema
    """

    # def __init__(self, **kwargs):
    #     super().__init__()

    id = fields.Int()
    created_at = fields.Method("get_created_at")
    # created_by = fields.Method("get_created_by")
    updated_at = fields.Method("get_updated_at")

    # updated_by = fields.Method("get_updated_by")

    # noinspection DuplicatedCode
    def dump(self, *args, **kwargs):
        raw_data = super().dump(*args, **kwargs)
        if type(raw_data) is not list:
            return raw_data
        data = []
        for d in raw_data:
            if d not in data:
                data.append(d)
        try:
            data = sorted(data, key=lambda i: i['priority'])
        except (KeyError, TypeError):
            pass
        return data

    def get_created_at(self, obj):
        try:
            return obj.created_at.timestamp()
        except AttributeError:
            return None

    def get_created_by(self, obj):
        try:
            user = obj.created_by
            return {'id': obj.pk, 'name': f"{user.first_name} {user.last_name}"}
        except AttributeError:
            return None

    def get_updated_at(self, obj):
        try:
            return obj.updated_at.timestamp()
        except AttributeError:
            return None

    def get_updated_by(self, obj):
        try:
            user = obj.updated_by
            return {'id': obj.pk, 'name': f"{user.first_name} {user.last_name}"}
        except AttributeError:
            return None

    def get_name(self, obj):
        return obj.name

    def get_brand(self, obj):
        try:
            return BrandASchema().dump(obj.brand)
        except Exception:
            return None

    def get_title(self, obj):
        return obj.title

    def get_box(self, obj):
        try:
            return {'id': obj.box_id, 'name': obj.box.name, 'settings': obj.box.settings}
        except AttributeError:
            obj = obj.product
            return {'id': obj.box_id, 'name': obj.box.name, 'settings': obj.box.settings}

    def get_category(self, obj):
        cats = []
        # categories = Category.objects
        for cat in obj.categories.all():
            cats.append({'id': cat.pk, 'name': cat.name})
        return cats

    def get_product(self, obj):
        try:
            return {'id': obj.product_id, 'name': obj.product.name}
        except AttributeError:
            return None

    def get_features(self, obj):
        return FeatureASchema(exclude=['groups']).dump(obj.features.all(), many=True)

    # def get_features(self, obj):
    #     features = obj.feature.all()
    #     storage_list = []
    #     for index, feature in enumerate(features):
    #         storage_list.append({'id': feature.pk, 'name': feature.name,
    #                              'count': feature.available_count_for_sale, 'disable': feature.disable})
    #     return storage_list

    def get_storage(self, obj):
        storages = obj.storages.all()
        storage_list = []
        for index, storage in enumerate(storages):
            storage_list.append({'id': storage.pk, 'title': {'fa': storage.title['fa']},
                                 'count': storage.available_count_for_sale, 'disable': storage.disable})
        return storage_list

    def get_media(self, obj):
        try:
            medias = ProductMedia.objects.filter(product=obj).order_by('priority')
            medias = [media.media for media in medias]
        except AttributeError:
            if obj.media is not None:
                return MediaSchema().dump(obj.media)
            return None
        except ValueError:
            if obj.media:
                return MediaASchema().dump(obj.media)
            return
        return MediaASchema().dump(medias, many=True)

    def get_tag(self, obj):
        tags = ProductTag.objects.filter(product=obj)
        return TagASchema().dump(tags, many=True)

    def get_feature_groups(self, obj, product=None):
        # features = ProductFeature.objects.filter(product=obj)
        # return self.get_product_features(features, model='product')

        if obj.__class__ == Feature:
            # return FeatureGroupASchema(exclude=['features']).dump(obj.groups.all(), many=True)
            return FeatureGroupASchema().dump(obj.groups.all(), many=True)
        if obj.__class__ == Category:
            # return FeatureGroupASchema(exclude=['features']).dump(obj.feature_groups.all(), many=True)
            return FeatureGroupASchema().dump(obj.feature_groups.all(), many=True)
        if obj.__class__ == Product:
            # return FeatureGroupASchema(exclude=['features']).dump(obj.feature_groups.all(), many=True)
            return FeatureGroupASchema().dump(obj.feature_groups.all(), many=True)

    def get_product_features(self, features, model):
        features_distinct = features.order_by('feature_id').distinct('feature_id')
        for product_feature in features_distinct:
            for pf in features.filter(feature=product_feature.feature):
                try:
                    product_feature.values.append(pf.feature_value)
                except AttributeError:
                    product_feature.values = []
                    product_feature.values.append(pf.feature_value)
        return ProductFeatureASchema(model=model).dump(features_distinct, many=True)


class DiscountASchema(BaseAdminSchema):
    class Meta:
        additional = ('code', 'invoice_id')


class UserASchema(UserSchema):
    class Meta:
        additional = UserSchema.Meta.additional + ('avatar',)

    telegram_username = fields.Method('get_telegram_username')

    def get_telegram_username(self, obj):
        if obj.tg_id:
            if obj.tg_username:
                return obj.tg_username
            return obj.tg_id
        return None


class SupplierESchema(BaseAdminSchema):
    class Meta:
        additional = ('id', 'username', 'first_name', 'last_name', 'shaba', 'is_verify', 'settings', 'deposit_id')


class BoxASchema(BoxSchema):
    class Meta:
        additional = ('settings',)

    name = fields.Dict()
    disable = fields.Boolean()
    is_owner = fields.Method("get_is_owner")

    def get_is_owner(self, obj):
        if obj.owner == self.user:
            return True
        return False


class InvoiceASchema(BaseAdminSchema, InvoiceSchema):
    list_filter = [Category]

    class Meta:
        additional = ('basket_id',)

    user = fields.Nested(MinUserSchema)
    deliver_status = fields.Method("get_deliver_status")
    products_count = fields.Method("get_products_count")

    def get_products_count(self, obj):
        return sum(obj.invoice_storages.all().values_list('count', flat=True))

    def get_deliver_status(self, obj):
        product_counts = obj.invoice_storages.all().count()
        ready_product_counts = InvoiceStorage.objects.filter(invoice=obj, deliver_status=2).count()  # packing
        try:
            if ready_product_counts / product_counts == 1:
                Invoice.objects.filter(pk=obj.pk).update()
        except ZeroDivisionError:
            pass
        return f'{ready_product_counts} / {product_counts}'


class InvoiceESchema(InvoiceASchema):
    class Meta:
        additional = InvoiceASchema.Meta.additional + (
            'id', 'basket_id', 'amount', 'status', 'final_price', 'special_offer_id',
            'address', 'description', 'reference_id', 'sale_order_id', 'sale_reference_id',
            'card_holder', 'post_tracking_code')

    ipg = fields.Method('get_ipg')
    suspended_by = fields.Function(lambda o: o.suspended_by.first_name + " "
                                             + o.suspended_by.last_name if o.suspended_by else None)
    suspended_at = fields.Function(lambda o: o.suspended_at.timestamp() if o.suspended_at else None)
    invoice_products = fields.Method("get_invoice_products")
    tax = fields.Method("get_tax")
    shipping_cost = fields.Int()
    start_price = fields.Method('get_start_price')
    post_invoice = fields.Nested("InvoiceASchema")
    recipient_info_a5 = fields.Method("get_recipient_info_a5")
    recipient_info_a6 = fields.Method("get_recipient_info_a6")
    max_shipping_time = fields.Method('get_max_shipping_time')
    mt_profit = fields.Method("get_mt_profit")
    charity = fields.Method("get_charity")
    dev = fields.Method("get_dev")
    admin = fields.Method("get_admin_profit")

    def get_admin_profit(self, obj):
        return InvoiceStorage.objects.filter(invoice=obj).aggregate(admin=Sum('admin'))['admin'] or 0

    def get_mt_profit(self, obj):
        return InvoiceStorage.objects.filter(invoice=obj).aggregate(mt_profit=Sum('mt_profit'))['mt_profit'] or 0

    def get_dev(self, obj):
        return InvoiceStorage.objects.filter(invoice=obj).aggregate(dev=Sum('dev'))['dev'] or 0

    def get_charity(self, obj):
        return InvoiceStorage.objects.filter(invoice=obj).aggregate(charity=Sum('charity'))['charity'] or 0

    def get_max_shipping_time(self, obj):
        if obj.status in Invoice.success_status:
            return add_minutes(obj.max_shipping_time * 60, obj.payed_at).timestamp()
        return None

    def get_recipient_info_a5(self, obj):
        return HOST + f'/admin/recipient_info?i={obj.pk}'

    def get_recipient_info_a6(self, obj):
        return HOST + f'/admin/recipient_info?i={obj.pk}&s=6'

    def get_start_price(self, obj):
        invoice_storages = InvoiceStorage.objects.filter(invoice=obj).values_list('start_price', flat=True)
        return sum(invoice_storages)

    def get_invoice_products(self, obj):
        storages = InvoiceStorage.objects.filter(invoice=obj)
        return InvoiceStorageFDSchema().dump(storages, many=True)

    def get_tax(self, obj):
        return InvoiceStorage.objects.filter(invoice=obj).aggregate(tax=Sum('tax'))['tax'] or 0

    def get_ipg(self, obj):
        return [ip for ip in ipg['data'] if ip['id'] == obj.ipg][0]


class InvoiceStorageASchema(InvoiceStorageSchema):
    class Meta:
        additional = InvoiceStorageSchema.Meta.additional + ('id', 'count', 'invoice_id', 'discount_price')

    storage = fields.Method("get_storage")
    deliver_status = fields.Function(lambda o: o.get_deliver_status_display())
    user = fields.Method("get_user")

    def get_user(self, obj):
        return MinUserSchema().dump(obj.invoice.user)

    def get_storage(self, obj):
        return StorageESchema().dump(obj.storage)


class InvoiceStorageFDSchema(InvoiceStorageASchema):
    class Meta:
        additional = InvoiceStorageASchema.Meta.additional + ('dev', 'admin', 'mt_profit', 'tax', 'charity',
                                                              'start_price')


class ProductASchema(BaseAdminSchema):
    class Meta:
        additional = ('review', 'check_review', 'name', 'storages_count', 'active_storages_count')

    list_filter = [Category]

    permalink = fields.Str()
    settings = fields.Dict()
    # box = fields.Method("get_box")
    categories = fields.Method("get_category")
    thumbnail = fields.Nested("MediaASchema")
    disable = fields.Boolean()
    has_selectable_feature = fields.Method("get_has_selectable_feature")
    type = fields.Function(lambda o: o.get_type_display())

    def get_has_selectable_feature(self, obj):
        return obj.features.filter(type=3).exists()


class BrandASchema(BrandSchema, BaseAdminSchema):
    name = fields.Dict()


class ProductTagASchema(Schema):
    id = fields.Function(lambda o: o.tag_id)
    permalink = fields.Function(lambda o: o.tag.permalink)
    name = fields.Function(lambda o: o.tag.name)
    show = fields.Boolean()


class ProductESchema(ProductASchema, ProductSchema):
    # class ProductESchema(BaseSchema):
    class Meta:
        unknown = EXCLUDE
        additional = ProductSchema.Meta.additional + ProductASchema.Meta.additional + ('verify', 'manage')

    media = fields.Method("get_media")
    tags = ProductTagField()
    tag_groups = ProductTagGroupField()
    brand = fields.Method("get_brand")
    properties = fields.Dict()
    details = fields.Dict()
    address = fields.Dict()
    short_address = fields.Dict()
    description = fields.Dict()
    short_description = fields.Dict()
    default_storage_id = fields.Int()
    features = fields.Method("get_features")
    feature_groups = fields.Method("get_feature_groups")

    def get_feature_groups(self, obj):
        categories = obj.categories.all()
        feature_groups = obj.feature_groups.all()
        for category in categories:
            feature_groups |= category.feature_groups.all()
        return FeatureGroupASchema(product=obj).dump(feature_groups, many=True)

    def get_features(self, obj):
        features = ProductFeature.objects.filter(product=obj)
        return self.get_product_features(features, model='product')


class ProductFeatureASchema(Schema):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

    feature = fields.Nested("FeatureASchema")
    values = fields.Method('get_values')

    def get_feature(self, obj):
        return {'id': obj.feature_id, 'name': obj.feature.name}

    def get_values(self, obj):
        product_features = ProductFeature.objects.filter(feature=obj.feature, product=obj.product)
        values = []
        for pf in product_features:
            product_feature_storage = ProductFeatureStorage.objects.filter(storage__product=pf.product,
                                                                           product_feature=pf)
            selected = product_feature_storage.exists()
            storages_id = list(product_feature_storage.values_list('storage_id', flat=True))
            pk = pf.id
            if self.model == 'product':
                pk = pf.feature_value_id
            values.append({'id': pk, 'name': pf.feature_value.value, 'selected': selected, 'storage_id': storages_id,
                           'settings': pf.feature_value.settings.get('ui', {})})
        return values


class ProductFeatureStorageASchema(Schema):
    id = fields.Int()
    feature = fields.Nested("FeatureASchema")
    feature_value = fields.Nested("FeatureValueASchema")
    value = fields.Dict()


class PriceSchema(Schema):
    class Meta:
        additional = ('weekday', 'weekend', 'guest', 'weekly_discount_percent', 'monthly_discount_percent',
                      'eyd', 'peak', 'custom_price')


class VipPriceASchema(Schema):
    class Meta:
        additional = ('storage_id', 'discount_price', 'discount_percent', 'max_count_for_sale',
                      'available_count_for_sale')

    # vip_type = fields.Function(lambda o: o.vip_type.name)
    vip_type = fields.Nested("VipTypeASchema")


class HouseESchema(BaseAdminSchema, HouseSchema):
    rules = fields.Dict()
    cancel_rules = fields.Dict()
    rent_type = fields.Dict()
    # price = fields.Function(lambda o: PriceSchema().dump(o.price))
    price = fields.Nested(PriceSchema)


class StorageASchema(BaseAdminSchema):
    class Meta:
        additional = ('title', 'start_price', 'final_price', 'discount_price', 'discount_percent',
                      'available_count_for_sale', 'tax', 'product_id', 'settings', 'max_count_for_sale',
                      'min_count_alert', 'disable')


class StorageESchema(StorageASchema):
    class Meta:
        additional = StorageASchema.Meta.additional + StorageSchema.Meta.additional + \
                     ('features_percent', 'available_count', 'invoice_description',
                      'invoice_title', 'dimensions', 'package_discount_price', 'sold_count')

    supplier = fields.Function(lambda o: UserSchema().dump(o.supplier))
    features = fields.Method('get_features')
    items = PackageItemsField()
    tax = fields.Function(lambda o: o.get_tax_type_display())
    vip_discount_price = fields.Function(lambda o: None)
    vip_discount_percent = fields.Function(lambda o: None)
    vip_prices = VipPriceField()
    start_time = fields.Function(lambda o: o.start_time.timestamp())
    vip_max_count_for_sale = fields.Function(lambda o: None)

    def get_features(self, obj):
        # product_feature_storages = ProductFeatureStorage.objects.filter(storage=obj).values_list('product_feature_id',
        #                                                                                          flat=True)
        # features = ProductFeature.objects.filter(pk__in=product_feature_storages)
        features = ProductFeature.objects.filter(product=obj.product, feature__type=3)  # selectable
        return self.get_product_features(features, model='storage')


class PackageASchema(StorageESchema):
    items = PackageItemsField()
    discount_price = fields.Int()
    final_price = fields.Int()


class PackageItemASchema(BaseAdminSchema):
    count = fields.Int()
    # title = fields.Method("get_item_title")
    product = fields.Method('get_package_item')

    def get_package_item(self, obj):
        try:
            storage = Storage.objects.get(pk=obj.package_item_id)
            product = storage.product
            product.default_storage = storage
            return ProductESchema().dump(product)
        except Exception:
            return None

    def get_item_title(self, obj):
        try:
            return obj.package_item.title
        except AttributeError:
            return None


class VipTypeASchema(Schema):
    id = fields.Int()
    name = fields.Dict()
    media = fields.Str()


class CommentASchema(BaseAdminSchema):
    class Meta:
        additional = ('approved', 'suspend', 'text')


class CommentESchema(CommentASchema, CommentSchema):
    class Meta:
        additional = CommentSchema.Meta.additional + CommentASchema.Meta.additional

    product = fields.Method("get_product")


class MediaASchema(BaseAdminSchema):
    list_filter = [Box, Category]

    class Meta:
        additional = ('title',)

    image = fields.Function(lambda o: HOST + o.image.url if o.image else None)
    type = fields.Function(lambda o: o.get_type_display())


class MediaESchema(MediaASchema, MediaSchema):
    pass


class CategoryASchema(BaseAdminSchema, CategorySchema):
    class Meta:
        additional = CategorySchema.Meta.additional + ('child_count', 'category_child_product_count', 'product_count',
                                                       'disable')

    parent = fields.Nested("CategoryASchema")
    box = fields.Nested(BoxASchema)


class CategoryESchema(CategoryASchema, BaseAdminSchema):
    class Meta:
        additional = CategoryASchema.Meta.additional + ('box_id',)

    feature_groups = fields.Method("get_feature_groups")


class FeatureASchema(BaseAdminSchema):
    def __init__(self, only_used_value=False, product=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.only_used_value = only_used_value
        self.product = product

    list_filter = [FeatureGroup]

    name = fields.Dict()
    type = fields.Function(lambda o: o.get_type_display())
    values = fields.Method("get_values")
    groups = fields.Method("get_feature_groups")

    def get_values(self, obj):
        # product_feature = ProductFeature.objects.filter(feature=obj, product=self.product)
        # if product_feature.exists():
        #     return [FeatureValueASchema(product=self.product).dump(product_feature.first().feature_value)]
        if getattr(obj, 'get_type_display')() == "text":
            fv = FeatureValue.objects.filter(feature=obj).order_by('id').first()
            if fv:
                return [FeatureValueASchema(product=self.product).dump(fv)]
            return []
        product = {}
        if self.only_used_value:
            product = {'product': self.product}
        values = FeatureValue.objects.filter(feature=obj, **product)
        return FeatureValueASchema(product=self.product).dump(values, many=True)


class FeatureValueASchema(BaseAdminSchema):
    def __init__(self, product=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product

    class Meta:
        additional = ('settings', 'priority')

    name = fields.Function(lambda o: getattr(o, 'value', None))
    selected = fields.Method("get_selected")

    def get_selected(self, obj):
        # if self.product:
        # print(self.product.pk, obj.pk)
        return ProductFeatureStorage.objects.filter(storage__product=self.product,
                                                    product_feature__feature_value=obj).exists()


class FeatureGroupASchema(BaseAdminSchema):
    def __init__(self, product=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product

    name = fields.Dict()
    features = fields.Method("get_features")
    box = fields.Nested(BoxASchema)

    def get_features(self, obj):
        if obj.__class__.__name__ == 'CategoryGroupFeature':
            feature_ids = FeatureGroupFeature.objects.filter(featuregroup=obj.featuregroup).order_by('priority', 'id') \
                .distinct('priority', 'id').values_list('feature', flat=True)
        else:
            feature_ids = FeatureGroupFeature.objects.filter(featuregroup=obj).order_by('priority', 'id') \
                .distinct('priority', 'id').values_list('feature', flat=True)
        features = sort_by_list_of_id(Feature, feature_ids)
        return FeatureASchema(exclude=['groups'], product=self.product).dump(features, many=True)


class TagASchema(Schema):
    id = fields.Int()
    permalink = fields.Str()
    name = fields.Dict()


class TagGroupTagASchema(Schema):
    name = fields.Function(lambda o: o.tag.name)
    permalink = fields.Function(lambda o: o.tag.permalink)
    id = fields.Function(lambda o: o.tag.pk)
    show = fields.Boolean()


class TagGroupASchema(BaseAdminSchema):
    name = fields.Dict()
    tags = TagGroupField()


class MenuASchema(BaseAdminSchema):
    pass


class MenuESchema(MenuASchema, MenuSchema):
    pass


class SpecialOfferASchema(BaseAdminSchema):
    pass


class SpecialOfferESchema(SpecialOfferASchema, SpecialOfferSchema):
    pass


class SpecialProductASchema(SpecialProductSchema):
    product = fields.Method("get_product")
    name = fields.Method("get_name")

    def get_name(self, obj):
        if obj.name:
            return obj.name
        return obj.storage.title

    def get_product(self, obj):
        return ProductASchema().dump(obj.storage.product)


class SpecialProductESchema(SpecialProductASchema, SpecialProductSchema):
    pass


class DashboardSchema(Schema):
    id = fields.Int()
    name = fields.Dict()
    product_count = fields.Method('get_product_count')
    active_product_count = fields.Method('get_active_product_count')

    def get_product_count(self, obj):
        return Product.objects.filter(box=obj).count()

    def get_active_product_count(self, obj):
        return Product.objects.filter(box=obj, disable=False, default_storage__disable=False).count()


class AdASchema(BaseSchema):
    class Meta:
        additional = ('id', 'url', 'priority', 'type')

    def __init__(self, is_mobile=True):
        super().__init__()
        self.is_mobile = is_mobile

    title = fields.Dict()
    media = fields.Method('get_media')
    mobile_media = fields.Method('get_mobile_media')
    product_permalink = fields.Method('get_permalink')

    def get_permalink(self, obj):
        try:
            return obj.storage.product.permalink
        except AttributeError:
            pass

    def get_mobile_media(self, obj):
        try:
            return MediaASchema().dump(obj.mobile_media)
        except AttributeError:
            return None

    def get_media(self, obj):
        try:
            return MediaASchema().dump(obj.media)
        except AttributeError:
            return None


class SliderASchema(BaseSchema):
    class Meta:
        additional = ('id', 'url', 'priority', 'type')

    def __init__(self, is_mobile=True):
        super().__init__()
        self.is_mobile = is_mobile

    title = fields.Dict()
    media = fields.Method('get_media')
    mobile_media = fields.Method('get_mobile_media')
    product_permalink = fields.Method('get_permalink')

    def get_permalink(self, obj):
        try:
            return obj.product.permalink
        except AttributeError:
            pass

    def get_mobile_media(self, obj):
        try:
            return MediaASchema().dump(obj.mobile_media)
        except AttributeError:
            return None

    def get_media(self, obj):
        try:
            return MediaASchema().dump(obj.media)
        except AttributeError:
            return None


tables = {'product': ProductASchema, 'media': MediaASchema, 'invoice': InvoiceASchema, 'feature': FeatureASchema}
