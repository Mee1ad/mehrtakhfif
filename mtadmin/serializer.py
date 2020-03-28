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
    id = fields.Int()
    created_at = fields.Function(lambda o: o.created_at.timestamp())
    created_by = fields.Function(lambda o:
                                 {'id': o.created_by_id, 'name': f"{o.created_by.first_name} {o.created_by.last_name}"})
    updated_at = fields.Function(lambda o: o.updated_at.timestamp())
    updated_by = fields.Function(lambda o:
                                 {'id': o.updated_by_id, 'name': f"{o.updated_by.first_name} {o.updated_by.last_name}"})

    def get_name(self, obj):
        return obj.name

    def get_title(self, obj):
        return obj.title

    def get_box(self, obj):
        return {'id': obj.box_id, 'name': obj.box.name}

    def get_category(self, obj):
        return {'id': obj.category_id, 'name': obj.category.name}

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
        storages = obj.storage_set.all()
        storage_list = []
        for index, storage in enumerate(storages):
            storage_list.append({'id': storage.pk, 'title': {'fa': storage.title['fa']},
                                 'count': storage.available_count_for_sale, 'disable': storage.disable})
        return storage_list

    def get_media(self, obj):
        medias = obj.media.all()
        return MediaASchema().dump(medias, many=True)

    def get_tag(self, obj):
        tags = obj.tag.all()
        tag_list = []
        for index, media in enumerate(tags):
            tag_list.append({'id': media.pk, 'name': {'fa': media.name['fa']}})
        return tag_list


class BoxASchema(Schema):
    class Meta:
        additional = ('id', 'permalink')

    name = fields.Dict()


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


class InvoiceStorageSchema(BaseSchema):
    class Meta:
        additional = ('id', 'count', 'tax', 'final_price', 'discount_price', 'discount_percent',
                      'vip_discount_price', 'vip_discount_percent', 'invoice_id')

    storage = fields.Method("get_min_storage")
    box = fields.Method("get_box")


class ProductASchema(BaseAdminSchema):
    list_filter = [Category]

    name = fields.Method("get_name")
    permalink = fields.Str()
    box = fields.Method("get_box")
    category = fields.Method("get_category")
    # storages = fields.Method("get_storage")
    city = fields.Nested(CitySchema)


class ProductESchema(ProductASchema, ProductSchema):
    class Meta:
        additional = ProductSchema.Meta.additional + ('disable', 'verify', 'brand')

    media = fields.Method("get_media")
    tag = fields.Method("get_tag")
    thumbnail = fields.Nested("MediaASchema")
    default_storage_id = fields.Int()
    name = fields.Dict()
    properties = fields.Dict()
    details = fields.Dict()
    address = fields.Dict()
    short_address = fields.Dict()
    description = fields.Dict()
    short_description = fields.Dict()


class StorageASchema(BaseAdminSchema):
    class Meta:
        additional = ('sold_count', 'start_price', 'available_count_for_sale')

    title = fields.Method("get_title")
    start_time = fields.Function(lambda o: o.start_time.timestamp())


class StorageESchema(StorageASchema, StorageSchema):
    class Meta:
        additional = StorageSchema.Meta.additional + StorageASchema.Meta.additional + ('gender', 'disable')

    features = FeatureField()


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

    image = fields.Function(lambda o: HOST + o.image.url)
    type = fields.Function(lambda o: o.get_type_display())


class MediaESchema(MediaASchema, MediaSchema):
    pass


class CategoryASchema(BaseAdminSchema):
    pass


class CategoryESchema(CategoryASchema, CategorySchema):
    pass


class FeatureASchema(BaseAdminSchema):
    name = fields.Dict()
    value = fields.Dict()
    type = fields.Function(lambda o: o.get_type_display())


class FeatureStorageASchema(Schema):
    id = fields.Int()
    feature = fields.Nested(FeatureASchema)
    value = fields.Function(lambda o: o.value)


class TagASchema(Schema):
    id = fields.Int()
    name = fields.Dict()


class TagESchema(TagASchema, TagSchema):
    pass


class BrandASchema(BaseAdminSchema, BrandSchema):
    pass


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
