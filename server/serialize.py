from marshmallow import Schema, fields
from mehr_takhfif.settings import HOST, MEDIA_URL
import pysnooper
from secrets import token_hex
from datetime import date
from django.utils import timezone
from server.models import BasketProduct, FeatureStorage, CostumeHousePrice, Book, Comment, Invoice
import time


# ManyToMany Relations


class MediaField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        media = value.all()
        return MediaSchema().dump(media, many=True)


class FeatureField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        features = FeatureStorage.objects.filter(storage=obj)
        return FeatureStorageSchema().dump(features, many=True)


class TagField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        tags = value.all()
        return TagSchema().dump(tags, many=True)


class ProductField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        product = value.all()
        return StorageSchema().dump(product, many=True)


class ResidenceTypeField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        types = value.all()
        return ResidenceTypeSchema().dump(types, many=True)


class BasketProductField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        basket_product = BasketProduct.objects.filter(basket_id=obj.pk).select_related(*BasketProduct.related)
        return BasketProductSchema().dump(basket_product, many=True)


# Serializer


class BaseSchema(Schema):
    id = fields.Int()

    def __init__(self, language='fa'):
        super().__init__()
        self.lang = language
        self.default_lang = 'fa'

    def get(self, name):
        try:
            if name[self.lang] != "":
                return name[self.lang]
            return name[self.default_lang]
        except ValueError:
            return name[self.default_lang]

    def get_name(self, obj):
        return self.get(obj.name)

    def get_brand(self, obj):
        return {"id": obj.brand_id, "name": self.get(obj.brand.name)}

    def get_title(self, obj):
        return self.get(obj.title)

    def get_address(self, obj):
        return self.get(obj.address)

    def get_short_address(self, obj):
        return self.get(obj.short_address)

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

    def get_house(self, obj):
        if hasattr(obj, 'house'):
            return HouseSchema(self.lang).dump(obj.house)
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
        if hasattr(obj, 'house'):
            return None
        if hasattr(obj, 'default_storage'):
            return MinStorageSchema(self.lang).dump(obj.default_storage)
        if hasattr(obj, 'storage'):
            return MinStorageSchema(self.lang).dump(obj.storage)
        return None

    def get_comment(self, obj):
        if obj.reply_to is not None:
            return CommentSchema().dump(obj.reply_to)
        return None

    def get_comment_replies(self, obj):
        if hasattr(obj, 'replies'):
            return CommentSchema().dump(obj.replies, many=True)
        return None

    def get_media(self, obj):
        if obj.media is not None:
            return MediaSchema(self.lang).dump(obj.media)
        return None

    def get_media_link(self, obj):
        if obj.media is not None:
            return HOST + obj.media.file.url
        return None

    def get_thumbnail(self, obj):
        if obj.thumbnail is not None:
            return MediaSchema(self.lang).dump(obj.thumbnail)
        return None

    def get_location(self, obj):
        if obj.location is not None:
            return {'lat': float(obj.location[0]), 'lng': float(obj.location[1])}
        return None

    def get_feature(self, obj):
        return FeatureSchema(language=self.lang).dump(obj.feature)

    def get_feature_name(self, obj):
        return obj.name[self.lang]

    def get_feature_value(self, obj):
        new_value = []
        for item, index in zip(obj.value, range(len(obj.value))):
            new_value.append({'name': item[self.lang], 'id': item['id']})
        return new_value


class UserSchema(BaseSchema):
    class Meta:
        additional = (
            'id', 'email', 'first_name', 'last_name', 'gender', 'username', 'meli_code', 'wallet_money', 'vip',
            'active_address', 'shaba', 'birthday', 'is_staff')

    avatar = fields.Function(lambda o: HOST + o.avatar.file.url if hasattr(o.avatar, 'file') else "")


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
    def __init__(self, language='fa'):
        super().__init__()
        self.lang = language

    id = fields.Int()
    type = fields.Function(lambda o: o.get_type_display())
    file = fields.Method("get_file")
    title = fields.Method("get_title")
    box = fields.Function(lambda o: o.box_id)

    def get_file(self, obj):
        return HOST + obj.file.url

    def get_title(self, obj):
        try:
            return obj.title[self.lang]
        except KeyError:
            return obj.title


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
    media = fields.Method("get_media_link")
    parent = fields.Function(lambda o: o.parent_id)

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
    name = fields.Method('get_feature_name')
    type = fields.Function(lambda o: o.get_type_display())
    value = fields.Method('get_feature_value')


class FeatureStorageSchema(BaseSchema):
    id = fields.Int()
    feature = fields.Method('get_feature')
    value = fields.Function(lambda o: o.value)


class TagSchema(BaseSchema):
    id = fields.Int()
    name = fields.Method('get_name')


class BrandSchema(BaseSchema):
    id = fields.Int()
    name = fields.Method('get_name')


class ProductSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink', 'gender', 'rate')

    name = fields.Method("get_name")
    address = fields.Method("get_address")
    short_address = fields.Method("get_short_address")
    type = fields.Function(lambda o: o.get_type_display())
    brand = fields.Method("get_brand")
    box = fields.Method("get_box")
    category = fields.Method("get_category")
    house = fields.Method("get_house")
    tag = TagField()
    media = MediaField()
    thumbnail = fields.Function(lambda o: HOST + o.thumbnail.file.url)
    short_description = fields.Method("get_short_description")
    description = fields.Method("get_description")
    properties = fields.Method("get_properties")
    details = fields.Method("get_details")
    location = fields.Function(lambda o: {"lat": o.location['lat'], 'lng': o.location['lng']} if o.location else {})


class MinProductSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink', 'rate')

    name = fields.Method("get_name")
    thumbnail = fields.Function(lambda o: HOST + o.thumbnail.file.url)
    default_storage = fields.Method("get_min_storage")


class SliderSchema(BaseSchema):
    class Meta:
        additional = ('id', 'link')

    title = fields.Method('get_title')
    type = fields.Function(lambda o: o.get_type_display())
    product = fields.Method("get_permalink")
    media = fields.Method("get_media")


class StorageSchema(BaseSchema):
    class Meta:
        additional = ('id', 'final_price', 'transportation_price', 'max_count_for_sale', 'priority',
                      'discount_price', 'vip_discount_price', 'discount_percent', 'vip_discount_percent')

    title = fields.Method('get_title')
    deadline = fields.Function(lambda o: o.deadline.timestamp())
    default = fields.Function(lambda o: o == o.product.default_storage)
    feature = FeatureField()


class MinStorageSchema(BaseSchema):
    class Meta:
        additional = ('id', 'final_price', 'discount_price', 'discount_percent', 'max_count_for_sale')

    title = fields.Method('get_title')


class BasketProductSchemaOld(BaseSchema):
    class Meta:
        additional = ('count',)

    storage = fields.Method("get_storage")


class BasketProductSchema(BaseSchema):
    class Meta:
        additional = ('count',)

    product = fields.Method("get_min_product")
    feature = fields.Method("get_basket_feature")

    def get_basket_feature(self, obj):
        features = []
        for feature in obj.feature:
            fs = obj.storage.featurestorage_set.get(feature_id=feature['fid'])
            fname = obj.storage.feature.get(pk=feature['fid']).name[self.lang]
            price = next(item['price'] for item in fs.value if item['fvid'] == feature['fvid'])
            features.append({"name": fname, "price": price})
        return features


class InvoiceSchema(BaseSchema):
    class Meta:
        additional = ('id', 'amount', 'final_price')

    created_at = fields.Function(lambda o: o.created_at.timestamp())
    status = fields.Function(lambda o: o.get_status_display())


class InvoiceStorageSchema(BaseSchema):
    class Meta:
        additional = ('count', 'discount_price', 'final_price', 'discount_percent', 'vip_discount_price',
                      'vip_discount_percent', 'invoice_id')

    storage = fields.Function(lambda o: {"id": o.storage.pk, "title": o.storage.title})
    permalink = fields.Function(lambda o: o.storage.product.permalink)
    box = fields.Function(lambda o: {"permalink": o.storage.product.box.permalink,
                                     "name": o.storage.product.box.name})
    thumbnail = fields.Function(lambda o: HOST + o.storage.product.thumbnail.file.url)
    unit_price = fields.Function(lambda o: int(o.discount_price / o.count))
    type = fields.Function(lambda o: o.storage.product.get_type_display())


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
        additional = ('id', 'text', 'approved', 'rate')

    user = fields.Function(lambda o: {"name": o.user.first_name + " " + o.user.last_name,
                                      "avatar": HOST + o.user.avatar.file.url})
    type = fields.Function(lambda o: o.get_type_display())
    reply_count = fields.Method('get_reply_count')
    created_at = fields.Function(lambda o: o.created_at.timestamp())
    purchase_at = fields.Method("get_purchase_time")
    satisfied = fields.Method("get_satisfied")

    def is_rate(self, obj):
        if obj.get_type_display() == 'rate':
            return True
        return False

    def get_satisfied(self, obj):
        if self.is_rate(obj):
            return obj.satisfied
        return None

    def get_purchase_time(self, obj):
        if not self.is_rate(obj):
            return None
        try:
            return Invoice.objects.get(user=obj.user, status='payed',
                                       storages__product=obj.product).payed_at.timestamp()
        except Invoice.DoesNotExist:
            return None

    def get_reply_count(self, obj):
        comments = Comment.objects.filter(product=obj.product, type=obj.type, reply_to=obj)
        return comments.count()


class MenuSchema(BasketSchema):
    class Meta:
        additional = ('id', 'url', 'value', 'priority')

    name = fields.Method('get_name')
    type = fields.Function(lambda o: o.get_type_display())
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
        additional = ('id', 'url')

    name = fields.Method('get_name')
    label_name = fields.Method('get_label_name')
    product_name = fields.Method('get_product_name')
    default_storage = fields.Method('get_min_storage')
    # media = fields.Method('get_media')
    description = fields.Method('get_description')
    thumbnail = fields.Function(lambda o: HOST + o.thumbnail.file.url)
    permalink = fields.Function(lambda o: o.storage.product.permalink)

    def get_label_name(self, obj):
        return self.get(obj.label_name)

    def get_product_name(self, obj):
        return self.get(obj.storage.product.name)


class AdSchema(BaseSchema):
    class Meta:
        additional = ('id', 'url')

    title = fields.Method('get_title')
    media = fields.Method('get_media')
    product = fields.Method('get_storage')


class WalletDetailSchema(Schema):
    class Meta:
        additional = ('id', 'credit', 'user')


class WishListSchema(BaseSchema):
    class Meta:
        additional = ('id', 'notify')

    product = fields.Method("get_min_product")
    type = fields.Function(lambda o: o.get_type_display())


class NotifyUserSchema(Schema):
    class Meta:
        additional = ('id', 'user', 'notify')

    product = fields.Method("get_product")
    type = fields.Function(lambda o: o.get_type_display())
    category = fields.Method("get_category")
    box = fields.Method("get_box")


class StateSchema(Schema):
    class Meta:
        additional = ('id', 'name')


class CitySchema(Schema):
    class Meta:
        additional = ('id', 'name')

    state = fields.Function(lambda o: o.state_id)


class ResidenceTypeSchema(BaseSchema):
    cancel_rules = fields.Method("get_name")


class PriceSchema(Schema):
    class Meta:
        additional = ('weekday', 'weekend', 'person_price', 'weekly_discount_percent', 'monthly_discount_percent')


class CostumeHousePriceSchema(Schema):
    class Meta:
        additional = ('start_date', 'end_date', 'price')


class HouseSchema(BaseSchema):
    class Meta:
        additional = ('notify_before_arrival', 'future_booking_time')

    cancel_rules = fields.Method("get_cancel_rules")
    rules = fields.Method("get_rules")
    state = fields.Function(lambda o: o.state.name)
    city = fields.Function(lambda o: o.city.name)
    house_feature = fields.Function(lambda o: o.house_feature)
    capacity = fields.Function(lambda o: o.capacity)
    rent_type = fields.Method('get_rent_type')
    residence_area = fields.Method('get_residence_area')
    bedroom = fields.Function(lambda o: o.bedroom)
    safety = fields.Function(lambda o: o.safety)
    calender = fields.Function(lambda o: o.calender)
    residence_type = ResidenceTypeField()
    prices = fields.Method("get_prices")

    @staticmethod
    def get_prices(obj):
        today = date.today()
        weekend = [3, 4]
        prices = []
        costume_prices = CostumeHousePrice.objects.filter(house=obj)
        bookings = Book.objects.filter(house=obj, confirm=True).values('start_date', 'end_date')
        for day in range(obj.future_booking_time):
            price = dict()
            price['date'] = today + timezone.timedelta(days=day)
            weekday = price['date'].weekday()
            if weekday not in weekend:
                price['price'] = obj.price.weekday
            else:
                price['price'] = obj.price.weekend
            for costume_price in costume_prices:
                if costume_price.start_date <= price['date'] <= costume_price.end_date:
                    price['price'] = costume_price.price
                    break
            for booking in bookings:
                price['available'] = True
                if booking['start_date'] <= price['date'] <= booking['end_date']:
                    price['available'] = False
                    break
            prices.append(price)
        return prices

    def get_rules(self, obj):
        return self.get(obj.rules)

    def get_cancel_rules(self, obj):
        return self.get(obj.cancel_rules)

    def get_rent_type(self, obj):
        return self.get(obj.rent_type)

    def get_residence_area(self, obj):
        return self.get(obj.residence_area)


class BooksSchema(BaseSchema):
    class Meta:
        additional = ('id',)

    product = fields.Method("get_min_product")
    status = fields.Method("get_status")
    amount = fields.Method("get_amount")
    start_date = fields.Function(lambda o: o.start_date)
    end_date = fields.Function(lambda o: o.end_date)

    def get_status(self, obj):
        invoice = obj.invoice
        if invoice:
            return invoice.status
        return None

    def get_amount(self, obj):
        invoice = obj.invoice
        if invoice:
            return invoice.amount
        return None

    def get_min_product(self, obj):
        return MinProductSchema().dump(obj.house.product)
