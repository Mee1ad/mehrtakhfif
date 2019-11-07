from marshmallow import Schema, fields
from mehr_takhfif.settings import HOST, MEDIA_URL
import pysnooper
from secrets import token_hex

# ManyToMany Relations


class MediaField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        media = value.all()
        return MediaSchema().dump(media, many=True)


class TagField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        tag = value.all()
        return TagSchema().dump(tag, many=True)


class ProductField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        product = value.all()
        return StorageSchema().dump(product, many=True)

# Serializer


class BaseSchema(Schema):

    def __init__(self, language='persian'):
        super().__init__()
        self.lang = language

    def get_name(self, obj):
        return obj.name[self.lang]

    def get_title(self, obj):
        return obj.title[self.lang]

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

    def get_storage(self, obj):
        if obj.storage is not None:
            return StorageSchema(self.lang).dump(obj.storage)
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

    def get_short_description(self, obj):
        return obj.short_description[self.lang]

    def get_description(self, obj):
        return obj.description[self.lang]

    def get_usage_condition(self, obj):
        return obj.usage_condition[self.lang]

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
        additional = ('id', 'email', 'gender', 'username', 'meli_code', 'wallet_money', 'vip', 'active_address')

    full_name = fields.Function(lambda o: o.get_full_name())


class AddressSchema(BaseSchema):
    class Meta:
        additional = ('id', 'province', 'postal_code', 'address', 'location', 'name', 'phone')

    city = fields.Method("get_city")
    state = fields.Function(lambda o: o.state.id)
    location = fields.Method("get_location")

    def get_city(self, obj):
        return CitySchema().dump(obj.city)


class BoxSchema(BaseSchema):
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
        additional = ('parent_id',)

    id = fields.Int()
    name = fields.Method('get_name')
    parent = fields.Method('get_parent')
    box = fields.Function(lambda o: o.box_id)


class CategoryMinSchema(BaseSchema):

    id = fields.Int()
    name = fields.Method('get_name')
    child = fields.Method('get_child')

    def get_child(self, obj):
        if hasattr(obj, 'child'):
            childes = []
            for child in obj.child:
                childes.append(CategoryMinSchema().dump(child))
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
        additional = ('id', 'permalink', 'gender', 'location', 'type')
    name = fields.Method("get_name")
    box = fields.Function(lambda o: o.box_id)
    category = fields.Function(lambda o: o.category_id)
    tag = TagField()
    media = MediaField()
    thumbnail = fields.Function(lambda o: HOST + o.thumbnail.file.url)
    short_description = fields.Method("get_short_description")
    description = fields.Method("get_description")
    usage_condition = fields.Method("get_usage_condition")


class ProductBoxSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink', 'gender', 'location', 'type')
    name = fields.Method("get_name")
    box = fields.Function(lambda o: o.box_id)
    category = fields.Function(lambda o: o.category_id)
    tag = TagField()
    media = MediaField()
    thumbnail = fields.Function(lambda o: HOST + o.thumbnail.file.url)
    short_description = fields.Method("get_short_description")
    description = fields.Method("get_description")
    usage_condition = fields.Method("get_usage_condition")


class SliderSchema(BaseSchema):
    class Meta:
        additional = ('id', 'type', 'link')
    title = fields.Method('get_title')
    product = fields.Method("get_product")
    media = fields.Method("get_media")


class StorageSchema(BaseSchema):
    class Meta:
        additional = ('id', 'final_price', 'transportation_price',
                      'discount_price', 'discount_vip_price', 'discount_price_percent', 'discount_vip_price_percent')

    product = fields.Method("get_product")
    category = fields.Function(lambda o: o.category_id)


class BasketProductSchema(BaseSchema):
    class Meta:
        additional = ('count',)

    product = fields.Method("get_storage")


class BasketSchema(BaseSchema):
    class Meta:
        additional = ('id', 'description')

    products = ProductField()


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
class FactorSchema(BaseSchema):
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
    description = fields.Method('get_description')
    storage = fields.Method("get_storage")
    media = fields.Method('get_media')


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
