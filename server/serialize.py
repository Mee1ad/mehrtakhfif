from marshmallow import Schema, fields
from mehr_takhfif.settings import HOST, MEDIA_URL
import pysnooper
from secrets import token_hex
from server.models import BasketProduct


# ManyToMany Relations


class MediaField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        media = value.all()
        return MediaSchema().dump(media, many=True)


class FeatureField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        feature = value.all()
        return FeatureSchema().dump(feature, many=True)


class TagField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        tags = value.all()
        return TagSchema().dump(tags, many=True)


class ProductField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        product = value.all()
        return StorageSchema().dump(product, many=True)


class BasketProductField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        basket_product = BasketProduct.objects.filter(basket_id=obj.pk).select_related(*BasketProduct.related)
        return BasketProductSchema().dump(basket_product, many=True)


# Serializer


class BaseSchema(Schema):

    def __init__(self, language='persian'):
        super().__init__()
        self.lang = language
        self.default_lang = 'persian'

    def get(self, obj):
        if obj[self.lang] != "":
            return obj[self.lang]
        return obj[self.default_lang]

    def get_name(self, obj):
        return self.get(obj.name)

    def get_title(self, obj):
        return self.get(obj.title)

    def get_short_description(self, obj):
        return self.get(obj.short_description)

    def get_description(self, obj):
        return self.get(obj.description)

    def get_properties(self, obj):
        return self.get(obj.properties)

    def get_details(self, obj):
        return self.get(obj.details)

    def get_box(self, obj):
        if obj.box is not None:
            return BoxSchema(self.lang).dump(obj.box)
        return None

    def get_parent(self, obj):
        if obj.parent is not None:
            return CategorySchema(self.lang).dump(obj.parent)
        return None

    def get_category(self, obj):
        if obj.category is not None:
            return CategorySchema(self.lang).dump(obj.category)
        return None

    def get_product(self, obj):
        if obj.product is not None:
            return ProductSchema(self.lang).dump(obj.product)
        return None

    def get_permalink(self, obj):
        if obj.product is not None:
            return obj.product.permalink
        return None

    def get_min_product(self, obj):
        if obj.product is not None:
            return MinProductSchema(self.lang).dump(obj.product)
        return None

    def get_storage(self, obj):
        if obj.storage is not None:
            return StorageSchema(self.lang).dump(obj.storage)
        return None

    def get_min_storage(self, obj):
        if obj.default_storage is not None:
            return MinStorageSchema(self.lang).dump(obj.default_storage)
        return None

    def get_comment(self, obj):
        if obj.reply is not None:
            return CommentSchema().dump(obj.reply)
        return None

    def get_media(self, obj):
        if obj.media is not None:
            return MediaSchema(self.lang).dump(obj.media)
        return None

    def get_thumbnail(self, obj):
        if obj.thumbnail is not None:
            return MediaSchema(self.lang).dump(obj.thumbnail)
        return None

    def get_location(self, obj):
        if obj.location is not None:
            return {'lat': float(obj.location[0]), 'lng': float(obj.location[1])}
        return None

    def get_value(self, obj):
        new_value = {}
        new_values = []
        for item in obj.value:
            new_value['price'] = item['price']
            new_value['name'] = item[self.lang]
            new_values.append(new_value)
        return new_values


class UserSchema(BaseSchema):
    class Meta:
        additional = (
        'id', 'email', 'full_name', 'gender', 'username', 'meli_code', 'wallet_money', 'vip', 'active_address')


class AddressSchema(BaseSchema):
    class Meta:
        additional = ('id', 'province', 'postal_code', 'address', 'location', 'name', 'phone')

    city = fields.Method("get_city")
    state = fields.Function(lambda o: o.state.id)
    location = fields.Function(lambda o: {"lat": o.location['lat'], 'lng': o.location['lng']} if o.location else {})

    def get_city(self, obj):
        return CitySchema().dump(obj.city)


class BoxSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink')

    id = fields.Int()
    name = fields.Method("get_name")


class MediaSchema(Schema):
    def __init__(self, language='persian'):
        super().__init__()
        self.lang = language

    id = fields.Int()
    type = fields.Str()
    file = fields.Method("get_file")
    title = fields.Method("get_title")
    box = fields.Function(lambda o: o.box_id)

    def get_file(self, obj):
        return HOST + obj.file.url

    def get_title(self, obj):
        return obj.title[self.lang]


class CategorySchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink')

    name = fields.Method('get_name')
    parent = fields.Method('get_parent')


class BoxCategoriesSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink')

    name = fields.Method('get_name')
    child = fields.Method('get_child')

    def get_child(self, obj):
        if hasattr(obj, 'child'):
            childes = []
            for child in obj.child:
                childes.append(BoxCategoriesSchema(self.lang).dump(child))
            return childes
        return None


class ParentSchema(BaseSchema):
    id = fields.Int()
    name = fields.Method('get_name')


class FeatureSchema(BaseSchema):
    id = fields.Int()
    name = fields.Method('get_name')
    value = fields.Method('get_value')


class TagSchema(BaseSchema):
    id = fields.Int()
    name = fields.Method('get_name')
    box = fields.Method('get_box')


class ProductSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink', 'gender', 'type', 'address', 'short_address')

    name = fields.Method("get_name")
    box = fields.Method("get_box")
    # category = fields.Method("get_category")
    category = fields.Nested(CategorySchema())
    tag = TagField()
    media = MediaField()
    thumbnail = fields.Function(lambda o: HOST + o.thumbnail.file.url)
    deadline = fields.Function(lambda o: o.deadline.timestamp())
    short_description = fields.Method("get_short_description")
    description = fields.Method("get_description")
    properties = fields.Method("get_properties")
    details = fields.Method("get_details")
    location = fields.Function(lambda o: {"lat": o.location['lat'], 'lng': o.location['lng']} if o.location else {})


class MinProductSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink',)

    name = fields.Method("get_name")
    thumbnail = fields.Function(lambda o: HOST + o.thumbnail.file.url)
    default_storage = fields.Method("get_min_storage")


class SliderSchema(BaseSchema):
    class Meta:
        additional = ('id', 'type', 'link')

    title = fields.Method('get_title')
    product = fields.Method("get_permalink")
    media = fields.Method("get_media")


class StorageSchema(BaseSchema):
    class Meta:
        additional = ('id', 'final_price', 'transportation_price', 'max_count_for_sale', 'default',
                      'discount_price', 'discount_vip_price', 'discount_percent', 'discount_vip_percent')

    title = fields.Method('get_title')
    deadline = fields.Function(lambda o: o.deadline.timestamp())
    # product = fields.Method('get_product')
    feature = FeatureField()


class MinStorageSchema(BaseSchema):
    class Meta:
        additional = ('id', 'final_price', 'discount_price', 'discount_percent')


class BasketProductSchemaOld(BaseSchema):
    class Meta:
        additional = ('count',)

    storage = fields.Method("get_storage")


class BasketProductSchema(BaseSchema):
    class Meta:
        additional = ('count',)

    product = fields.Nested(MinProductSchema())


class BasketSchema(BaseSchema):
    class Meta:
        additional = ('id', 'description')


class BlogSchema(BaseSchema):
    id = fields.Int()
    title = fields.Method('get_title')
    name = fields.Method("get_name")
    description = fields.Method("get_description")
    media = MediaField()


class BlogPostSchema(BaseSchema):
    id = fields.Int()
    title = fields.Method('get_title')
    description = fields.Method("get_description")
    media = MediaField()


class CommentSchema(BaseSchema):
    class Meta:
        additional = ('id', 'text', 'reply_id', 'type', 'created_at')

    user = fields.Function(lambda obj: obj.user_id)
    reply = fields.Method("get_comment")


# todo
class InvoiceSchema(BaseSchema):
    class Meta:
        additional = ('id', 'price', 'product', 'user', 'payed_at', 'successful', 'type', 'special_offer_id', 'address',
                      'description', 'final_price', 'discount_price', 'count', 'tax')

    product = fields.Int()


class MenuSchema(BasketSchema):
    class Meta:
        additional = ('id', 'type', 'url', 'value', 'priority')

    name = fields.Method('get_name')
    parent = fields.Function(lambda o: o.parent_id)
    media = fields.Method('get_media')


class RateSchema(BaseSchema):
    class Meta:
        additional = ('id', 'rate')

    user = fields.Function(lambda obj: obj.user_id)
    product = fields.Function(lambda obj: obj.product_id)


class SpecialOfferSchema(BaseSchema):
    class Meta:
        additional = ('id', 'code', 'user_id', 'end_date', 'discount_price', 'discount_percent', 'least_count',
                      'vip_discount_price', 'vip_discount_percent', 'start_date', 'peak_price')

    name = fields.Method('get_name')
    # user = fields.Pluck(UserSchema, "id", many=True)
    # product = fields.Method("get_product")
    # not_accepted_products = fields.Method("get_product")
    category = fields.Function(lambda o: o.category_id)
    box = fields.Function(lambda o: o.box_id)
    media = fields.Method('get_media')


class SpecialProductSchema(BaseSchema):
    class Meta:
        additional = ('id', 'type', 'link', 'url')

    title = fields.Method('get_title')
    thumbnail = fields.Function(lambda o: HOST + o.thumbnail.file.url)
    description = fields.Method('get_description')
    storage = fields.Method("get_storage")
    media = fields.Method('get_media')


class MinSpecialProductSchema(BaseSchema):
    class Meta:
        additional = ('id', 'url')

    title = fields.Method('get_title')
    product = fields.Function(lambda o: o.product.permalink)
    thumbnail = fields.Function(lambda o: HOST + o.thumbnail.file.url)


class AdSchema(BaseSchema):
    class Meta:
        additional = ('id', 'url')

    title = fields.Method('get_title')
    media = fields.Method('get_media')
    product = fields.Method('get_storage')


class WalletDetailSchema(Schema):
    class Meta:
        additional = ('id', 'credit', 'user')


# todo user view
class WishListSchema(BaseSchema):
    class Meta:
        additional = ('id', 'type', 'notify')

    product = fields.Method("get_product")


class NotifyUserSchema(Schema):
    class Meta:
        additional = ('id', 'user', 'type', 'notify')

    product = fields.Method("get_product")
    category = fields.Method("get_category")
    box = fields.Method("get_box")


class TourismSchema(Schema):
    class Meta:
        additional = ('id', 'date', 'price')


class StateSchema(Schema):
    class Meta:
        additional = ('id', 'name')


class CitySchema(Schema):
    class Meta:
        additional = ('id', 'name')

    state = fields.Function(lambda o: o.state_id)
