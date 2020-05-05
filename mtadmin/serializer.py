from server.models import *
from server.serialize import *


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
        for cat in obj.category.all():
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
        tags = obj.tags.all()
        tag_list = []
        for index, media in enumerate(tags):
            tag_list.append({'id': media.pk, 'name': {'fa': media.name['fa']}})
        return tag_list


class SupplierESchema(BaseAdminSchema):
    class Meta:
        additional = ('id', 'username', 'first_name', 'last_name', 'shaba', 'is_verify')





class BoxASchema(BoxSchema):
    name = fields.Dict()
    disable = fields.Boolean()


class InvoiceASchema(Schema):
    class Meta:
        additional = ('id', 'basket_id', 'amount', 'status', 'final_price')

    user = fields.Function(lambda o: o.user.first_name + " " + o.user.last_name)
    created_at = fields.Function(lambda o: o.created_at.timestamp())
    payed_at = fields.Function(lambda o: o.payed_at.timestamp() if o.payed_at else None)


class InvoiceESchema(InvoiceASchema):
    class Meta:
        additional = InvoiceASchema.Meta.additional + (
            'id', 'basket_id', 'amount', 'status', 'final_price', 'special_offer_id',
            'address', 'description', 'tax', 'ipg')

    suspended_by = fields.Function(lambda o: o.suspended_by.first_name + " "
                                             + o.suspended_by.last_name if o.suspended_by else None)
    suspended_at = fields.Function(lambda o: o.suspended_at.timestamp() if o.suspended_at else None)


class ProductASchema(BaseAdminSchema):
    list_filter = [Category]

    name = fields.Method("get_name")
    permalink = fields.Str()
    settings = fields.Dict()
    box = fields.Method("get_box")
    categories = fields.Method("get_category")
    storages = fields.Method("get_storage")
    city = fields.Nested(CitySchema)
    thumbnail = fields.Nested("MediaASchema")
    disable = fields.Boolean()


class BrandASchema(BrandSchema, BaseAdminSchema):
    name = fields.Dict()


class ProductESchema(ProductASchema, ProductSchema):
    class Meta:
        additional = ProductSchema.Meta.additional + ('verify', )

    # media = fields.Method("get_media")
    tag = fields.Method("get_tag")
    brand = fields.Method("get_brand")
    default_storage_id = fields.Int()
    name = fields.Dict()
    properties = fields.Dict()
    details = fields.Dict()
    address = fields.Dict()
    short_address = fields.Dict()
    description = fields.Dict()
    short_description = fields.Dict()


class PriceSchema(Schema):
    class Meta:
        additional = ('weekday', 'weekend', 'guest', 'weekly_discount_percent', 'monthly_discount_percent',
                      'eyd', 'peak', 'custom_price')


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


class StorageESchema(StorageASchema):
    class Meta:
        additional = StorageASchema.Meta.additional + StorageSchema.Meta.additional + \
                     ('features_percent', 'available_count', 'invoice_description',
                      'invoice_title')

    supplier = fields.Function(lambda o: UserSchema().dump(o.supplier))
    features = FeatureField()
    tax = fields.Function(lambda o: o.get_tax_type_display())


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
    id = fields.Int()
    name = fields.Dict()


class InvoiceProductSchema(Schema):
    class Meta:
        additional = ('id', 'count', 'final_price', 'discount_price', 'tax')


class MenuASchema(BaseAdminSchema):
    pass


class MenuESchema(MenuASchema, MenuSchema):
    pass


class SpecialOfferASchema(BaseAdminSchema):
    pass


class SpecialOfferESchema(SpecialOfferASchema, SpecialOfferSchema):
    pass


class SpecialProductASchema(BaseAdminSchema):
    pass


class SpecialProductESchema(SpecialProductASchema, SpecialProductSchema):
    pass


tables = {'product': ProductASchema, 'media': MediaASchema}
