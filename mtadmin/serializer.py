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
        return {'fa': obj.name['fa']}

    def get_title(self, obj):
        return {'fa': obj.title['fa']}

    def get_box(self, obj):
        return {'id': obj.box_id, 'name': {'fa': obj.box.name['fa']}}

    def get_category(self, obj):
        return {'id': obj.category_id, 'name': {'fa': obj.category.name['fa']}}

    def get_storage(self, obj):
        storages = obj.storage_set.all()
        storage_list = []
        for index, storage in enumerate(storages):
            storage_list.append({'id': storage.pk, 'title': {'fa': storage.title['fa']},
                                 'count': storage.available_count_for_sale, 'disable': storage.disable})
        return storage_list

    def get_media(self, obj):
        medias = obj.media.all()
        media_list = []
        for index, media in enumerate(medias):
            media_list.append({'id': media.pk, 'title': {'fa': media.title['fa']},
                               'type': media.get_type_display()})
        return media_list

    def get_tag(self, obj):
        tags = obj.tag.all()
        tag_list = []
        for index, media in enumerate(tags):
            tag_list.append({'id': media.pk, 'name': {'fa': media.name['fa']}})
        return tag_list


class InvoiceASchema(Schema):
    class Meta:
        additional = ('id', 'basket_id', 'amount', 'status', 'final_price')

    user = fields.Function(lambda o: o.user.first_name + " " + o.user.last_name)
    created_at = fields.Function(lambda o: o.created_at.timestamp())
    payed_at = fields.Function(lambda o: o.payed_at.timestamp() if o.payed_at else None)


class InvoiceESchema(InvoiceASchema):
    class Meta:
        additional = ('id', 'basket_id', 'amount', 'status', 'final_price')

    user = fields.Function(lambda o: o.user.first_name + " " + o.user.last_name)
    created_at = fields.Function(lambda o: o.created_at.timestamp())
    payed_at = fields.Function(lambda o: o.payed_at.timestamp() if o.payed_at else None)


class InvoiceStorageSchema(BaseSchema):
    class Meta:
        additional = ('id', 'count', 'tax', 'final_price', 'discount_price', 'discount_percent',
                      'vip_discount_price', 'vip_discount_percent')

    storage = fields.Method("get_min_storage")


class ProductASchema(BaseAdminSchema):
    list_filter = [Box, Category]

    name = fields.Method("get_name")
    permalink = fields.Str()
    box = fields.Method("get_box")
    category = fields.Method("get_category")
    storages = fields.Method("get_storage")


class ProductESchema(ProductASchema, ProductSchema):
    class Meta:
        additional = ProductSchema.Meta.additional + ('disable', 'verify')

    media = fields.Method("get_media")
    tag = fields.Method("get_tag")
    brand = fields.Function(lambda o: o.brand.name)
    properties = fields.Function(lambda o: o.properties)
    details = fields.Function(lambda o: o.details)
    address = fields.Function(lambda o: o.address)
    short_address = fields.Function(lambda o: o.short_address)
    description = fields.Function(lambda o: o.description['fa'])
    short_description = fields.Function(lambda o: o.short_description['fa'])


class StorageASchema(BaseAdminSchema):
    class Meta:
        additional = ('sold_count', 'start_price', 'available_count_for_sale', 'start_time')

    title = fields.Method("get_title")


class StorageESchema(StorageASchema, StorageSchema):
    class Meta:
        additional = ('sold_count', 'start_price', 'available_count', 'available_count_for_sale', 'priority', 'start_time')


class CommentASchema(BaseAdminSchema):
    additional = ('approved', 'suspend')


class CommentESchema(CommentASchema, CommentSchema):
    additional = ('approved', 'suspend')


class MediaASchema(BaseAdminSchema):
    pass


class MediaESchema(MediaASchema, MediaSchema):
    pass


class CategoryASchema(BaseAdminSchema):
    pass


class CategoryESchema(CategoryASchema, CategorySchema):
    pass


class FeatureASchema(BaseAdminSchema):
    pass


class FeatureESchema(FeatureASchema, FeatureSchema):
    pass


class TagASchema(BaseAdminSchema):
    pass


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


tables = {'product': ProductASchema}
