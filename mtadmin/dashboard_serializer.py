from marshmallow import Schema, fields
from server.models import Product


class ProductCountSchema(Schema):
    id = fields.Int()
    name = fields.Dict()
    product_count = fields.Method('get_product_count')
    active_product_count = fields.Method('get_active_product_count')
    settings = fields.Function(lambda o: o.settings)

    def get_product_count(self, obj):
        return Product.objects.filter(parent_category=obj).count()

    def get_active_product_count(self, obj):
        return Product.objects.filter(parent_category=obj, disable=False).count()


class DateProductCountSchema(Schema):
    id = fields.Int()
    name = fields.Dict()
    product_count = fields.Method('get_product_count')
    active_product_count = fields.Method('get_active_product_count')
