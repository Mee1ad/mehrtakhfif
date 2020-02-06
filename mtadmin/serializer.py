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
    created_at = fields.Function(lambda o: o.created_at.timestamp())
    created_by = fields.Function(lambda o:
                                 {'id': o.created_by_id, 'name': f"{o.created_by.first_name} {o.created_by.last_name}"})
    updated_at = fields.Function(lambda o: o.updated_at.timestamp())
    updated_by = fields.Function(lambda o:
                                 {'id': o.updated_by_id, 'name': f"{o.updated_by.first_name} {o.updated_by.last_name}"})

    def get_name(self, obj):
        return obj.name['fa']

    def get_box(self, obj):
        return {'id': obj.box_id, 'name': obj.box.name['fa']}

    def get_category(self, obj):
        return {'id': obj.category_id, 'name': obj.category.name['fa']}

    def get_storage(self, obj):
        storages = obj.storage_set.all()
        storage_list = []
        for index, storage in enumerate(storages):
            storage_list.append({'id': storage.pk, 'title': storage.title['fa'],
                                 'count': storage.available_count_for_sale, 'disable': storage.disable})
        return storage_list


class InvoiceSchema(Schema):
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


class ProductESchema(BaseAdminSchema, ProductSchema):
    class Meta:
        additional = ('income', 'profit', 'disable', 'verify')


class ProductSchema(BaseAdminSchema):
    list_filter = [Box, Category]

    id = fields.Int()
    name = fields.Method("get_name")
    box = fields.Method("get_box")
    category = fields.Method("get_category")
    storages = fields.Method("get_storage")


class StorageSchema(BaseAdminSchema, StorageSchema):
    additional = ('sold_count', 'start_price', 'available_count', 'available_count_for_sale', 'priority', 'start_time')


class CommentSchema(BaseAdminSchema, CommentSchema):
    additional = ('approved', 'suspend')


class MediaSchema(BaseAdminSchema, MediaSchema):
    pass


class CategorySchema(BaseAdminSchema, CategorySchema):
    pass


class FeatureSchema(BaseAdminSchema, FeatureSchema):
    pass


class TagSchema(BaseAdminSchema, TagSchema):
    pass


class BrandSchema(BaseAdminSchema, BrandSchema):
    pass


class MenuSchema(BaseAdminSchema, MenuSchema):
    pass


class SpecialOfferSchema(BaseAdminSchema, SpecialOfferSchema):
    pass


class SpecialProductSchema(BaseAdminSchema, SpecialProductSchema):
    pass


class BlogSchema(BaseAdminSchema, BlogSchema):
    pass


class BlogPostSchema(BaseAdminSchema, BlogPostSchema):
    pass


tables = {'product': ProductSchema}