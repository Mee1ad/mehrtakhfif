from server.models import *
from server.serialize import *
from marshmallow import INCLUDE, EXCLUDE
import pysnooper
from server.views.payment import ipg
from server.utils import *


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

class FeatureField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        features = FeatureStorage.objects.filter(storage=obj)
        return FeatureStorageASchema().dump(features, many=True)


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
    created_at = fields.Function(lambda o: o.created_at.timestamp())
    created_by = fields.Method("get_created_by")
    updated_at = fields.Function(lambda o: o.updated_at.timestamp())
    updated_by = fields.Method("get_updated_by")

    def get_created_by(self, obj):
        try:
            user = obj.created_by
            return {'id': obj.pk, 'name': f"{user.first_name} {user.last_name}"}
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
        for cat in obj.categories.all():
            cats.append({'id': cat.pk, 'name': cat.name})
        return cats

    def get_product(self, obj):
        try:
            return {'id': obj.product_id, 'name': obj.product.name}
        except AttributeError:
            return None

    def get_features(self, obj):
        features = obj.feature.all()
        storage_list = []
        for index, feature in enumerate(features):
            storage_list.append({'id': feature.pk, 'name': feature.name,
                                 'count': feature.available_count_for_sale, 'disable': feature.disable})
        return storage_list

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


class UserASchema(UserSchema):
    class Meta:
        additional = UserSchema.Meta.additional + ('avatar', )


class SupplierESchema(BaseAdminSchema):
    class Meta:
        additional = ('id', 'username', 'first_name', 'last_name', 'shaba', 'is_verify', 'settings', 'deposit_id')


class BoxASchema(BoxSchema):
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
        return f'{ready_product_counts} / {product_counts}'


class InvoiceESchema(InvoiceASchema):
    class Meta:
        additional = InvoiceASchema.Meta.additional + (
            'id', 'basket_id', 'amount', 'status', 'final_price', 'special_offer_id',
            'address', 'description', 'reference_id', 'sale_order_id', 'sale_reference_id',
            'card_holder', 'post_tracking_code', 'mt_profit', 'ha_profit')

    ipg = fields.Method('get_ipg')
    suspended_by = fields.Function(lambda o: o.suspended_by.first_name + " "
                                             + o.suspended_by.last_name if o.suspended_by else None)
    suspended_at = fields.Function(lambda o: o.suspended_at.timestamp() if o.suspended_at else None)
    invoice_products = fields.Method("get_invoice_products")
    tax = fields.Method("calculate_invoice_tax")
    shipping_cost = fields.Int()
    start_price = fields.Method('get_start_price')
    post_invoice = fields.Nested("InvoiceASchema")
    recipient_info_a5 = fields.Method("get_recipient_info_a5")
    recipient_info_a6 = fields.Method("get_recipient_info_a6")
    max_shipping_time = fields.Method('get_max_shipping_time')

    def get_max_shipping_time(self, obj):
        success_status = Invoice.success_status
        if obj.status in success_status:
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
        return InvoiceStorageASchema().dump(storages, many=True)

    def calculate_invoice_tax(self, obj):
        taxes = obj.invoice_storages.all().values_list('tax', flat=True)
        return sum(taxes)

    def get_ipg(self, obj):
        return [ip for ip in ipg['data'] if ip['id'] == obj.ipg][0]


class InvoiceStorageASchema(InvoiceStorageSchema):
    class Meta:
        additional = ('id', 'count', 'invoice_id', 'discount_price')

    storage = fields.Method("get_storage")
    deliver_status = fields.Function(lambda o: o.get_deliver_status_display())

    def get_storage(self, obj):
        return StorageESchema().dump(obj.storage)


class ProductASchema(BaseAdminSchema):
    class Meta:
        additional = ('review', 'check_review', 'name')

    list_filter = [Category]

    permalink = fields.Str()
    settings = fields.Dict()
    box = fields.Method("get_box")
    categories = fields.Method("get_category")
    storages = StorageField()
    thumbnail = fields.Nested("MediaASchema")
    disable = fields.Boolean()
    type = fields.Function(lambda o: o.get_type_display())


class BrandASchema(BrandSchema, BaseAdminSchema):
    name = fields.Dict()


class ProductTagASchema(Schema):
    id = fields.Function(lambda o: o.tag_id)
    permalink = fields.Function(lambda o: o.tag.permalink)
    name = fields.Function(lambda o: o.tag.name)
    show = fields.Boolean()


class ProductESchema(ProductASchema, ProductSchema):
    class Meta:
        unknown = EXCLUDE
        additional = ProductSchema.Meta.additional + ProductASchema.Meta.additional + ('verify',)

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


class StorageASchema(BaseAdminSchema, StorageSchema):
    class Meta:
        additional = ('sold_count', 'start_price', 'available_count_for_sale', 'tax')

    title = fields.Method("get_title")
    start_time = fields.Function(lambda o: o.start_time.timestamp())
    vip_max_count_for_sale = fields.Function(lambda o: None)
    discount_price = fields.Int()
    final_price = fields.Int()
    discount_percent = fields.Int()


class StorageESchema(StorageASchema):
    class Meta:
        additional = StorageASchema.Meta.additional + StorageSchema.Meta.additional + \
                     ('features_percent', 'available_count', 'invoice_description',
                      'invoice_title', 'dimensions', 'package_discount_price')

    supplier = fields.Function(lambda o: UserSchema().dump(o.supplier))
    features = FeatureField()
    items = PackageItemsField()
    tax = fields.Function(lambda o: o.get_tax_type_display())
    vip_discount_price = fields.Function(lambda o: None)
    vip_discount_percent = fields.Function(lambda o: None)
    vip_prices = VipPriceField()


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


class CategoryESchema(CategoryASchema):
    class Meta:
        additional = CategoryASchema.Meta.additional + ('box_id',)


class FeatureASchema(BaseAdminSchema):
    class Meta:
        additional = ('icon', 'name', 'value')

    type = fields.Function(lambda o: o.get_type_display())


class FeatureStorageASchema(Schema):
    id = fields.Int()
    feature = fields.Nested(FeatureASchema)
    value = fields.Function(lambda o: o.value)


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
