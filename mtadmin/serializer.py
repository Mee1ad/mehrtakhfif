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


class PackegeItemsField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        items = Package.objects.filter(package_id=obj)
        return PackageItemASchema().dump(items, many=True)


class ProductTagField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        items = ProductTag.objects.filter(product=obj)
        return ProductTagASchema().dump(items, many=True)


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
            medias = obj.media.all()
        except AttributeError:
            if obj.media is not None:
                return MediaSchema().dump(obj.media)
            return None
        return MediaASchema().dump(medias, many=True)

    def get_tag(self, obj):
        tags = ProductTag.objects.filter(product=obj)
        return TagASchema().dump(tags, many=True)


class SupplierESchema(BaseAdminSchema):
    class Meta:
        additional = ('id', 'username', 'first_name', 'last_name', 'shaba', 'is_verify')


class BoxASchema(BoxSchema):
    name = fields.Dict()
    disable = fields.Boolean()


class InvoiceASchema(BaseAdminSchema, InvoiceSchema):
    list_filter = [Box, Category]

    class Meta:
        additional = ('basket_id',)

    user = fields.Nested(MinUserSchema)
    product_count = fields.Method("get_product_count")

    def get_product_count(self, obj):
        product_counts = obj.invoice_storages.all().values_list('count', flat=True)
        return sum(product_counts)


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
    transportation_price = fields.Int()
    start_price = fields.Method('get_start_price')

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


class ProductASchema(BaseAdminSchema):
    list_filter = [Category]

    name = fields.Method("get_name")
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
        additional = ProductSchema.Meta.additional + ('verify',)

    media = fields.Method("get_media")
    tags = ProductTagField()
    brand = fields.Method("get_brand")
    name = fields.Dict()
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
    items = PackegeItemsField()
    tax = fields.Function(lambda o: o.get_tax_type_display())
    vip_discount_price = fields.Function(lambda o: None)
    vip_discount_percent = fields.Function(lambda o: None)
    vip_prices = VipPriceField()


class PackageASchema(StorageESchema):
    items = PackegeItemsField()
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

    parent = fields.Method("get_parent")

    def get_parent(self, obj):
        try:
            parent = obj.parent
            return {'id': parent.pk, 'name': parent.name, 'permalink': parent.permalink}
        except Exception:
            pass


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


class TagASchema(TagSchema):
    permalink = fields.Str()
    name = fields.Dict()


class InvoiceStorageASchema(InvoiceStorageSchema):
    class Meta:
        additional = ('id', 'count', 'final_price', 'discount_price', 'start_price', 'tax', 'details')

    mt_profit = fields.Method('get_mt_profit')
    hl_profit = fields.Method('get_hl_profit')
    start_price = fields.Function(lambda o: o.storage.start_price)
    features = fields.Dict()

    def get_hl_profit(self, obj):
        storage = obj.storage
        tax = get_tax(storage.tax_type, storage.discount_price, storage.start_price)
        hl_profit = (storage.discount_price - storage.start_price - tax) * 0.05
        return hl_profit

    def get_mt_profit(self, obj):
        storage = obj.storage
        tax = get_tax(storage.tax_type, storage.discount_price, storage.start_price)
        hl_profit = (storage.discount_price - storage.discount_price - tax) * 0.05
        return storage.discount_price - storage.start_price - hl_profit


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


tables = {'product': ProductASchema, 'media': MediaASchema, 'invoice': InvoiceASchema}