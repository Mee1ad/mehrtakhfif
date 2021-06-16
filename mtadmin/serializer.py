from django.contrib.postgres.aggregates import ArrayAgg
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


def dump(raw_data):
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
        items = ProductTag.objects.filter(product=obj).select_related(*ProductTag.select)
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
class AdminSchema(Schema):
    id = fields.Int()
    name = fields.Method("get_name")

    def get_name(self, obj):
        return obj.first_name + ' ' + obj.last_name


class BaseAdminSchema(Schema):
    """
    E = Edit
    S = Schema
    """

    # def __init__(self, **kwargs):
    #     super().__init__()

    id = fields.Int()
    created_at = fields.Method("get_created_at")
    # created_by = fields.Nested("AdminSchema")
    updated_at = fields.Method("get_updated_at")

    # updated_by = fields.Nested("AdminSchema")

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
            # medias = ProductMedia.objects.filter(product=obj).select_related(*ProductMedia.select).order_by('priority')
            medias = obj.product_media.all().select_related('media')
            new_medias = []
            for media in medias:
                media.media.priority = media.priority
                new_medias.append(media.media)
            return MediaASchema().dump(new_medias, many=True)
        except AttributeError:
            if obj.media is not None:
                return MediaSchema().dump(obj.media)
            return None
        except ValueError:
            if obj.media:
                return MediaASchema().dump(obj.media)
            return None

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

    def get_product_features(self, product_features, model):  # tiny extra query problem, not finding problem
        features_distinct = []
        for product_feature in product_features:
            included_features_id = [pf.feature_id for pf in features_distinct]
            if product_feature.feature_id not in included_features_id:
                features_distinct.append(product_feature)
                continue
            pf = next(pf for pf in features_distinct if pf.feature_id == product_feature.feature_id)
            try:
                product_feature.values.append(pf.feature_value)
            except AttributeError:
                product_feature.values = []
                product_feature.values.append(pf.feature_value)

        return ProductFeatureASchema(model=model).dump(features_distinct, many=True)  # 107 extra query

    def get_product_features_new(self, obj):
        type_filter = {}
        if obj.__class__.__name__ == 'Storage' or getattr(self, 'only_selectable'):
            try:
                obj = obj.product
            except AttributeError:
                pass
            type_filter = {'feature__type': 3}
        product_features = obj.product_features.filter(**type_filter).annotate(
            storage_id=ArrayAgg('product_feature_storages__storage')).select_related('feature_value', 'feature')

        features_distinct = []
        for product_feature in product_features:
            product_feature.feature_value.product_feature_id = product_feature.id
            included_features_id = [pf.feature_id for pf in features_distinct]
            product_feature.used = type(next(iter(product_feature.storage_id), None)) == int
            product_feature.feature_value.storage_id = product_feature.storage_id
            if product_feature.feature_id not in included_features_id:
                product_feature.values = []
                product_feature.values.append(product_feature.feature_value)
                features_distinct.append(product_feature)
                continue
            pf = next(pf for pf in features_distinct if pf.feature_id == product_feature.feature_id)
            pf.values.append(product_feature.feature_value)

        features = []
        for pf in features_distinct:
            features.append({'feature': FeatureASchema(only=['id', 'name', 'type']).dump(pf.feature),
                             'priority': pf.priority, 'id': pf.id, 'used': pf.used,
                             'values': FeatureValueASchema(exclude=['created_at', 'updated_at'])
                            .dump(pf.values, many=True)})
        features = sorted(features, key=lambda i: i['priority'])
        return features

    def get_date(self, obj, time_attr):
        try:
            return getattr(obj, time_attr).timestamp()
        except AttributeError:
            pass


class BookingASchema(BaseAdminSchema):
    start_date = fields.Function(lambda o: o.start_time.timestamp())
    end_date = fields.Function(lambda o: o.end_time.timestamp())
    product = fields.Nested("ProductASchema")
    user = fields.Nested("MinUserSchema")
    status = fields.Method("get_status")

    def get_status(self, obj):
        try:
            return obj.invoice.get_status_display()
        except AttributeError:
            return 'pending'


class BookingESchema(BookingASchema):
    class Meta:
        additional = ('invoice_id', 'least_reserve_time')

    storage = fields.Nested("StorageASchema")
    address = fields.Nested("AddressSchema")
    location = fields.Dict()
    cart_postal_text = fields.Dict()
    type = fields.Function(lambda o: o.get_type_display())
    confirmed_at = fields.Method("get_confirmed_at")
    cancel_at = fields.Method("get_cancel_at")
    reject_at = fields.Method("get_reject_at")
    confirmed_by = fields.Nested("AdminSchema")
    cancel_by = fields.Nested("AdminSchema")
    reject_by = fields.Nested("AdminSchema")

    def get_confirmed_at(self, obj):
        return self.get_date(obj, 'confirmed_at')

    def get_cancel_at(self, obj):
        return self.get_date(obj, 'cancel_at')

    def get_reject_at(self, obj):
        return self.get_date(obj, 'reject_at')


class DiscountASchema(BaseAdminSchema):
    class Meta:
        additional = ('code', 'invoice_id')


class UserASchema(UserSchema):
    class Meta:
        additional = UserSchema.Meta.additional + ('avatar', 'settings')

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
    children = None

    def get_categories(self, obj):  # for overwrite parent attribute
        pass

    def get_is_owner(self, obj):
        if obj.owner == self.user:
            return True
        return False


class InvoiceASchema(BaseAdminSchema):
    list_filter = [Category]

    class Meta:
        additional = ('start_date', 'end_date', 'details', 'amount')

    user = fields.Nested(MinUserSchema)
    deliver_status = fields.Method("get_deliver_status")
    products_count = fields.Method("get_products_count")
    start_date = fields.Method("get_end_date")
    end_date = fields.Method("get_start_date")
    payed_at = fields.Method("get_payed_at")
    status = fields.Function(lambda o: o.get_status_display())

    def get_payed_at(self, obj):
        return self.get_date(obj, 'payed_at')

    def get_end_date(self, obj):
        return self.get_date(obj, 'end_date')

    def get_start_date(self, obj):
        return self.get_date(obj, 'start_date')

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


class InvoiceESchema(InvoiceASchema, InvoiceSchema):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    class Meta:
        additional = InvoiceASchema.Meta.additional + (
            'id', 'basket_id', 'amount', 'status', 'final_price', 'special_offer_id',
            'address', 'description', 'reference_id', 'sale_order_id', 'sale_reference_id',
            'card_holder', 'post_tracking_code')

    ipg = fields.Method('get_ipg')
    invoice_products = fields.Method("get_invoice_products")
    tax = fields.Method("get_tax")
    invoice = fields.Method("get_invoice_file")
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
    suspended_by = fields.Nested(AdminSchema)
    cancel_by = fields.Nested(AdminSchema)
    reject_by = fields.Nested(AdminSchema)
    confirmed_by = fields.Nested(AdminSchema)
    suspended_at = fields.Method("get_suspended_at")
    cancel_at = fields.Method("get_cancel_at")
    reject_at = fields.Method("get_reject_at")
    confirmed_at = fields.Method("get_confirmed_at")

    def get_invoice_file(self, obj):
        try:
            if self.user.is_staff or obj.get_type_display == 'payed':
                return HOST + f'/invoice_detail/{obj.id}'
        except AttributeError:
            return None

    def get_suspended_at(self, obj):
        return self.get_date(obj, 'suspended_at')

    def get_cancel_at(self, obj):
        return self.get_date(obj, 'cancel_at')

    def get_reject_at(self, obj):
        return self.get_date(obj, 'reject_at')

    def get_confirmed_at(self, obj):
        return self.get_date(obj, 'confirmed_at')

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


class InvoiceStorageASchema(BaseAdminSchema):
    class Meta:
        additional = ('id', 'count', 'invoice_id', 'discount_price')

    storage = fields.Method("get_storage")
    product = fields.Method("get_product")
    deliver_status = fields.Function(lambda o: o.get_deliver_status_display())
    user = fields.Method("get_user")
    purchase_date = fields.Method('get_purchase_date')

    def get_purchase_date(self, obj):
        try:
            return obj.invoice.payed_at.timestamp()
        except AttributeError:
            return None

    def get_user(self, obj):
        return MinUserSchema(only=('id', 'first_name', 'last_name', 'username')).dump(obj.invoice.user)

    def get_storage(self, obj):
        return StorageESchema(only=('id', 'title', 'supplier')).dump(obj.storage)

    def get_product(self, obj):
        return ProductASchema(only=('id', 'thumbnail',)).dump(obj.storage.product)


class InvoiceStorageFDSchema(InvoiceStorageASchema):
    class Meta:
        additional = InvoiceStorageASchema.Meta.additional + ('dev', 'admin', 'mt_profit', 'tax', 'charity',
                                                              'start_price')


class ProductASchema(BaseAdminSchema):
    class Meta:
        additional = ('review', 'check_review', 'name', 'storages_count', 'active_storages_count', 'unavailable')

    list_filter = [Category]

    permalink = fields.Str()
    settings = fields.Dict()
    # box = fields.Method("get_box")
    categories = fields.Method("get_category")
    thumbnail = fields.Nested("MediaASchema")
    disable = fields.Boolean()
    # has_selectable_feature = fields.Method("get_has_selectable_feature")
    type = fields.Function(lambda o: o.get_type_display())
    booking_type = fields.Function(lambda o: o.get_booking_type_display())

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
    def __init__(self, include_storage=False, only_selectable=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.include_storage = include_storage
        self.only_selectable = only_selectable

    class Meta:
        unknown = EXCLUDE
        additional = ('verify', 'manage', 'review') + ProductSchema.Meta.additional + ProductASchema.Meta.additional

    media = fields.Method("get_media")
    tags = ProductTagField()
    box = fields.Nested(BoxASchema(only=['id', 'name', 'settings']))
    tag_groups = fields.Method("get_tag_groups")
    brand = fields.Nested(BrandASchema)
    properties = fields.Dict()
    details = fields.Dict()
    address = fields.Dict()
    short_address = fields.Dict()
    description = fields.Dict()
    short_description = fields.Dict()
    # default_storage = fields.Function(lambda o: None)
    # available = fields.Function(lambda o: None)
    default_storage_id = fields.Int()
    has_selectable_feature = fields.Function(lambda o: True)
    # features = fields.Method("get_features")  # 38 + 19(selected) => 64
    features = fields.Method("get_product_features_new")
    feature_groups = fields.Method("get_feature_groups")  # 2
    booking_type = fields.Function(lambda o: o.get_booking_type_display())
    storages = fields.Method("get_storages", load_only=True, dump_only=False)
    accessory_type = fields.Function(lambda o: o.get_accessory_type_display())

    def get_storages(self, obj):
        if self.include_storage:
            return StorageASchema(only=('id', 'title', 'start_price', 'discount_price', 'available_count_for_sale')) \
                .dump(obj.storages.all(), many=True)
        return []

    def get_feature_groups(self, obj):
        feature_groups = FeatureGroup.objects.filter(categories__in=obj.categories.all()). \
            prefetch_related('feature_group_features__feature__values')
        # return FeatureGroupASchema(product=obj, exclude=['box']).dump(feature_groups, many=True)
        return FeatureGroupASchema(product=obj).dump(feature_groups, many=True)

    def get_features(self, obj):
        type_filter = {}
        if self.include_storage:
            type_filter = {'feature__type': 3}
        features = obj.product_features.filter(**type_filter).select_related('feature_value', 'feature')
        # features = ProductFeature.objects.filter(product=obj, **type_filter).select_related('feature_value')
        return self.get_product_features(features, model='product')

    def get_features_new(self, obj):
        type_filter = {}
        if obj.__class__.__name__ == 'Storage':
            type_filter = {'feature__type': 3}
        product_features = obj.product_features.filter(**type_filter).annotate(
            storage_id=ArrayAgg('product_feature_storages')).select_related('feature_value', 'feature')

        features_distinct = []
        for product_feature in product_features:
            included_features_id = [pf.feature_id for pf in features_distinct]
            product_feature.used = type(next(iter(product_feature.storage_id), None)) == int
            product_feature.feature_value.storage_id = product_feature.storage_id
            if product_feature.feature_id not in included_features_id:
                product_feature.values = []
                product_feature.values.append(product_feature.feature_value)
                features_distinct.append(product_feature)
                continue
            pf = next(pf for pf in features_distinct if pf.feature_id == product_feature.feature_id)
            pf.values.append(product_feature.feature_value)

        features = []
        for pf in features_distinct:
            features.append({'feature': FeatureASchema(only=['id', 'name', 'type']).dump(pf.feature),
                             'priority': pf.priority, 'id': pf.id, 'used': pf.used,
                             'values': FeatureValueASchema(exclude=['created_at', 'updated_at'])
                            .dump(pf.values, many=True)})
        return features

    def get_tag_groups(self, obj):
        tag_groups = obj.tag_groups.all()
        return TagGroupASchema(exclude=['tags']).dump(tag_groups, many=True)


class ProductFeatureASchema(Schema):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model

    def dump(self, *args, **kwargs):
        raw_data = super().dump(*args, **kwargs)
        return dump(raw_data)

    id = fields.Int()
    feature = fields.Nested("FeatureASchema")  # 66 + 19(selected) extra query
    # feature = fields.Method("get_feature")  # 18 + 19(selected) extra query, solved
    values = fields.Method('get_values')  # 23 extra query
    priority = fields.Int()

    def get_feature(self, obj):  # 0 extra query
        return {'id': obj.feature_id, 'name': obj.feature.name}

    def get_values(self, obj):
        product_features = ProductFeature.objects.filter(feature=obj.feature, product=obj.product) \
            .select_related('feature_value').prefetch_related('product_feature_storages')

        values = []
        for pf in product_features:
            selected = 'type(pf.selected) == int'
            # storages_id = list(product_feature_storage.values_list('storage_id', flat=True))
            storages_id = 'pf.storages_id'
            # print(storages_id)
            pk = pf.id
            if self.model == 'product':
                pk = pf.feature_value_id
            values.append({'id': pk, 'name': pf.feature_value.value, 'selected': selected, 'storage_id': storages_id,
                           'settings': pf.feature_value.settings.get('ui', {})})
        return values


class NewProductFeatureASchema(Schema):
    id = fields.Int()
    feature = fields.Method("get_feature")

    def get_feature(self, obj):
        pass


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


class AccessoryASchema(BaseSchema):
    class Meta:
        additional = ('id', 'discount_price')

    storage_id = fields.Function(lambda o: o.accessory_storage_id)
    product_id = fields.Function(lambda o: o.accessory_product_id)
    title = fields.Function(lambda o: o.accessory_storage.title['fa'])
    thumbnail = fields.Function(lambda o: HOST + o.accessory_product.thumbnail.image.url)


class StorageASchema(BaseAdminSchema):
    class Meta:
        additional = ('title', 'start_price', 'final_price', 'discount_price', 'discount_percent',
                      'available_count_for_sale', 'tax', 'product_id', 'settings', 'max_count_for_sale',
                      'min_count_alert', 'disable', 'unavailable', 'priority')

    least_booking_time = fields.Method("get_least_booking_time")
    booking_cost = fields.Method("get_booking_cost")
    media = fields.Nested("MediaASchema")
    accessory = fields.Method("get_accessory")

    def get_accessory(self, obj):
        accessories = obj.storage_accessories.all()
        return AccessoryASchema().dump(accessories, many=True)

    def get_least_booking_time(self, obj):
        if obj.product.booking_type == 1:  # unbookable
            return -1
        return obj.least_booking_time

    def get_booking_cost(self, obj):
        if obj.product.booking_type == 1:  # unbookable
            return -1
        return obj.booking_cost


class StorageESchema(StorageASchema):
    class Meta:
        additional = StorageASchema.Meta.additional + StorageSchema.Meta.additional + \
                     ('features_percent', 'available_count', 'invoice_description', 'max_shipping_time',
                      'invoice_title', 'dimensions', 'package_discount_price', 'sold_count')

    supplier = fields.Nested(MinUserSchema)
    # features = fields.Method('get_features')
    features = fields.Method('get_product_features_new')
    items = fields.Method("get_items")
    tax = fields.Function(lambda o: o.get_tax_type_display())
    vip_discount_price = fields.Function(lambda o: None)
    vip_discount_percent = fields.Function(lambda o: None)
    vip_prices = VipPriceField()
    start_time = fields.Function(lambda o: o.start_time.timestamp())
    vip_max_count_for_sale = fields.Function(lambda o: None)
    deadline = fields.Method("get_deadline")

    def get_deadline(self, obj):
        try:
            return obj.deadline.timestamp()
        except Exception:
            pass

    def get_items(self, obj):
        # items = Package.objects.filter(package_id=obj)
        items = obj.packages.all().select_related('package_item__product').prefetch_related('package_item__vip_prices')
        return PackageItemASchema().dump(items, many=True)

    def get_features_new(self, obj):
        product_features = ProductFeature.objects.filter(product=obj.product, feature__type=3)
        res = []
        for pf in product_features:
            res.append({'feature': FeatureASchema(only=['id', 'name']).dump(pf.feature),
                        'priority': pf.priority, 'id': pf.id,
                        'values': FeatureValueASchema(exclude=['created_at', 'updated_at']).dump(pf.feature_value,
                                                                                                 many=True)})
        return []

    def get_features(self, obj):
        # product_feature_storages = ProductFeatureStorage.objects.filter(storage=obj).values_list('product_feature_id',
        #                                                                                          flat=True)
        # features = ProductFeature.objects.filter(pk__in=product_feature_storages)
        features = ProductFeature.objects.filter(product=obj.product, feature__type=3). \
            select_related(*ProductFeature.select)  # selectable
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
            storage = obj.package_item
            product = storage.product
            product.default_storage = storage
            return ProductESchema(only=['id', 'name', 'default_storage']).dump(product)
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
        additional = ('title', 'priority')

    image = fields.Function(lambda o: HOST + o.image.url if o.image else None)
    type = fields.Function(lambda o: o.get_type_display())


class ProductMediaASchema(Schema):
    id = fields.Int()
    priority = fields.Int()
    media = fields.Nested(MediaASchema)


class MediaESchema(MediaASchema, MediaSchema):
    pass


class CategoryASchema(BaseAdminSchema, CategorySchema):
    class Meta:
        additional = CategorySchema.Meta.additional + ('child_count', 'category_child_product_count', 'product_count',
                                                       'disable')

    parent = fields.Nested("CategoryASchema")
    box = fields.Nested(BoxASchema)
    children = None


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
    settings = fields.Dict()
    type = fields.Function(lambda o: o.get_type_display())
    values = fields.Method("get_values")  # 7 + 19 (selected)
    groups = fields.Method("get_feature_groups")  # 8

    def get_values(self, obj):
        # product_feature = ProductFeature.objects.filter(feature=obj, product=self.product)
        # if product_feature.exists():
        #     return [FeatureValueASchema(product=self.product).dump(product_feature.first().feature_value)]
        values = obj.values.all()
        if getattr(obj, 'get_type_display')() == "text":
            # fv = values.order_by('id').first()
            fv = min(values, key=attrgetter('id'), default={"fa": "اطلاعاتی برای نمایش وجود ندارد"})
            if fv:
                return [FeatureValueASchema(product=self.product).dump(fv)]
            return []
        if self.only_used_value:
            values = FeatureValue.objects.filter(feature=obj, product=self.product)
        return FeatureValueASchema(product=self.product).dump(values, many=True)


class FeatureValueASchema(BaseAdminSchema):
    def __init__(self, product=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product

    class Meta:
        additional = ('settings', 'priority')

    name = fields.Function(lambda o: getattr(o, 'value', None))
    storage_id = fields.Method('get_storage_id')
    product_feature_id = fields.Method('get_product_feature_id')

    def get_storage_id(self, obj):
        try:
            if type(next(iter(obj.storage_id), None)) == int:
                return obj.storage_id
            return []
        except Exception:
            return []

    def get_product_feature_id(self, obj):
        try:
            return obj.product_feature_id
        except Exception:
            return None

    # selected = fields.Method("get_selected")  # 19 extra query, get worse with prefetch

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
    settings = fields.Dict()
    # features = fields.Method("get_features_old")
    features = fields.Method("get_features")

    # features = fields.Nested('FeatureGroupFeatureASchema')
    box = fields.Method('get_box')

    def get_box(self, obj):
        return BoxASchema(only=['id']).dump(obj.box)

    def get_features(self, obj):
        # product_features = ProductFeature.objects.filter(product=self.product, feature__groups__in=[obj.id])
        # return ProductFeatureASchema(model='product').dump(product_features, many=True)

        features = obj.feature_group_features.all()
        return FeatureGroupFeatureASchema(product=self.product).dump(features, many=True)

    def get_features_old(self, obj):
        if obj.__class__.__name__ == 'CategoryGroupFeature':
            feature_ids = FeatureGroupFeature.objects.filter(featuregroup=obj.featuregroup).order_by('priority', 'id') \
                .distinct('priority', 'id').values_list('feature', flat=True)
        else:
            feature_ids = FeatureGroupFeature.objects.filter(featuregroup=obj).order_by('priority', 'id') \
                .distinct('priority', 'id').values_list('feature', flat=True)
        features = sort_by_list_of_id(Feature, feature_ids)
        return FeatureASchema(exclude=['groups'], product=self.product).dump(features, many=True)


class FeatureGroupFeatureASchema(BaseAdminSchema):
    def __init__(self, product=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product

    feature = fields.Method("get_feature")
    # features = fields.Nested(FeatureASchema)
    priority = fields.Int()

    def get_feature(self, obj):
        return FeatureASchema(exclude=['groups'], product=self.product).dump(obj.feature)


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
    tags = fields.Method("get_tags")

    def get_tags(self, obj):
        tags = TagGroupTag.objects.filter(taggroup=obj).select_related('tag')
        return TagGroupTagASchema().dump(tags, many=True)


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
