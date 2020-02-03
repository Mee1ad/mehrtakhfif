from marshmallow import Schema, fields
from mehr_takhfif.settings import HOST, MEDIA_URL
import pysnooper
from secrets import token_hex
from datetime import date
from django.utils import timezone
from server.models import BasketProduct, FeatureStorage, CostumeHousePrice, Book
import time
from server.serialize import *

lst = []


def list_view(obj_list):
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
    created_at = fields.Function(lambda o: o.created_at.timestamp())
    updated_at = fields.Function(lambda o: o.updated_at.timestamp())


class InvoiceAdminSchema(Schema):
    class Meta:
        additional = ('id', 'basket_id', 'amount', 'status', 'final_price')

    user = fields.Function(lambda o: o.user.first_name + " " + o.user.last_name)
    created_at = fields.Function(lambda o: o.created_at.timestamp())
    payed_at = fields.Function(lambda o: o.payed_at.timestamp() if o.payed_at else None)


class InvoiceStorageAdminSchema(BaseSchema):
    class Meta:
        additional = ('id', 'count', 'tax', 'final_price', 'discount_price', 'discount_percent',
                      'vip_discount_price', 'vip_discount_percent')

    storage = fields.Method("get_min_storage")


class ProductAdminSchema(BaseAdminSchema, ProductSchema):
    additional = ('income', 'profit', 'disable', 'verify')


class StorageAdminSchema(BaseAdminSchema, StorageSchema):
    additional = ('sold_count', 'start_price', 'available_count', 'available_count_for_sale', 'priority', 'start_time')


class CommentAdminSchema(BaseAdminSchema, CommentSchema):
    additional = ('approved', 'suspend')


class MediaAdminSchema(BaseAdminSchema, MediaSchema):
    pass


class CategoryAdminSchema(BaseAdminSchema, CategorySchema):
    pass


class FeatureAdminSchema(BaseAdminSchema, FeatureSchema):
    pass


class TagAdminSchema(BaseAdminSchema, TagSchema):
    pass


class BrandAdminSchema(BaseAdminSchema, BrandSchema):
    pass


class MenuAdminSchema(BaseAdminSchema, MenuSchema):
    pass


class SpecialOfferAdminSchema(BaseAdminSchema, SpecialOfferSchema):
    pass


class SpecialProductAdminSchema(BaseAdminSchema, SpecialProductSchema):
    pass


class BlogAdminSchema(BaseAdminSchema, BlogSchema):
    pass


class BlogPostAdminSchema(BaseAdminSchema, BlogPostSchema):
    pass
