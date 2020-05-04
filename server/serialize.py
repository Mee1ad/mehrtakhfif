from marshmallow import Schema, fields
from mehr_takhfif.settings import HOST, MEDIA_URL
import pysnooper
from secrets import token_hex
from datetime import date
from django.utils import timezone
from server.models import BasketProduct, FeatureStorage, Booking, Comment, Invoice, Feature, \
    ProductMedia, Holiday
from jdatetime import date, timedelta
from django.db.models import F


# ManyToMany Relations

class MediaField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        media = ProductMedia.objects.filter(product=obj).order_by('priority')
        medias = ProductMediaSchema().dump(media, many=True)
        return [m['media'] for m in medias]


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

    def __init__(self, language='fa', vip=False):
        super().__init__()
        self.lang = language
        self.default_lang = 'fa'
        self.vip = vip

    def get(self, name):
        try:
            if name[self.lang] != "":
                return name[self.lang]
            return name[self.default_lang]
        except ValueError:
            return name[self.default_lang]
        except KeyError:
            return None

    def get_name(self, obj):
        return self.get(obj.name)

    def get_brand(self, obj):
        if obj.brand:
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
        if obj.properties:
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
        if obj.category.all():
            return CategorySchema(self.lang).dump(obj.category.all(), many=True)
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
        try:
            if hasattr(obj, 'house'):
                return None
            if hasattr(obj, 'default_storage'):
                return MinStorageSchema(self.lang, vip=self.vip).dump(obj.default_storage)
            if hasattr(obj, 'storage'):
                return MinStorageSchema(self.lang, vip=self.vip).dump(obj.storage)
            return None
        except Exception:
            pass

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
            return HOST + obj.media.image.url
        return None

    def get_thumbnail(self, obj):
        if obj.thumbnail is not None:
            return MediaSchema(self.lang).dump(obj.thumbnail)
        return None

    def get_location(self, obj):
        try:
            if obj.location is not None:
                return {'lat': float(obj.location['lat']), 'lng': float(obj.location['lng'])}
        except AttributeError:
            return None

    def get_feature(self, obj):
        return FeatureSchema(language=self.lang).dump(obj.feature)

    def get_feature_name(self, obj):
        return obj.name[self.lang]

    def get_feature_value(self, obj):
        new_value = []
        for item, index in zip(obj.value, range(len(obj.value))):
            new_value.append({'name': item['name'][self.lang], 'id': item['id']})
        return new_value

    def get_max_count_for_sale(self, obj):
        if obj.available_count_for_sale >= obj.max_count_for_sale:
            return obj.max_count_for_sale
        return obj.available_count_for_sale

    def get_min_count_alert(self, obj):
        if obj.available_count_for_sale <= obj.min_count_alert:
            return obj.available_count_for_sale
        return None

    def get_city(self, obj):
        try:
            return CitySchema().dump(obj.city)
        except AttributeError:
            pass

    def get_state(self, obj):
        try:
            return CitySchema().dump(obj.state)
        except AttributeError:
            pass


class UserSchema(BaseSchema):
    class Meta:
        additional = (
            'id', 'email', 'first_name', 'last_name', 'gender', 'username', 'meli_code', 'vip',
            'active_address', 'shaba')

    avatar = fields.Method("get_avatar")
    birthday = fields.Method("get_birthday")

    def get_avatar(self, obj):
        try:
            return HOST + obj.avatar.image.url
        except Exception:
            pass

    def get_birthday(self, obj):
        try:
            return obj.birthday.timestamp()
        except AttributeError:
            return None

class AddressSchema(BaseSchema):
    class Meta:
        additional = ('id', 'province', 'postal_code', 'address', 'location', 'name', 'phone')

    city = fields.Method("get_city")
    state = fields.Method('get_state')
    location = fields.Method('get_location')


class BoxSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink')

    id = fields.Int()
    name = fields.Method("get_name")
    media = fields.Method('get_media')


class MediaSchema(BaseSchema):
    def __init__(self, language='fa'):
        super().__init__()
        self.lang = language

    id = fields.Int()
    type = fields.Function(lambda o: o.get_type_display())
    image = fields.Method("get_image")
    title = fields.Method("get_title")
    box = fields.Function(lambda o: o.box_id)

    def get_image(self, obj):
        return HOST + obj.image.url


class CategorySchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink')

    name = fields.Method('get_name')
    parent = fields.Method('get_parent')
    media = fields.Method('get_media')


class BoxCategoriesSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink')

    name = fields.Method('resolve_name_type')
    child = fields.Method('get_child')
    media = fields.Method("get_media")
    parent = fields.Function(lambda o: o.parent_id)

    def resolve_name_type(self, obj):
        try:
            return obj.name if obj.is_admin else obj.name[self.lang]
        except KeyError:
            return obj.name['fa']

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
    permalink = fields.Str()


class BrandSchema(BaseSchema):
    id = fields.Int()
    name = fields.Method('get_name')
    permalink = fields.Str()


class ProductSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink', 'gender', 'rate', 'disable')

    name = fields.Method("get_name")
    address = fields.Method("get_address")
    short_address = fields.Method("get_short_address")
    type = fields.Function(lambda o: o.get_type_display())
    brand = fields.Method("get_brand")
    box = fields.Method("get_box")
    categories = fields.Method("get_category")
    house = fields.Method("get_house")
    tag = TagField()
    media = MediaField()
    thumbnail = fields.Method("get_thumbnail")
    short_description = fields.Method("get_short_description")
    description = fields.Method("get_description")
    properties = fields.Method("get_properties")
    details = fields.Method("get_details")
    location = fields.Method("get_location")


class ProductMediaSchema(BaseSchema):
    media = fields.Method("get_media")


class MinProductSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink', 'rate')

    name = fields.Method("get_name")
    thumbnail = fields.Method("get_thumbnail")
    default_storage = fields.Method("get_min_storage")


class SliderSchema(BaseSchema):
    class Meta:
        additional = ('id', 'link')

    title = fields.Method('get_title')
    type = fields.Function(lambda o: o.get_type_display())
    product = fields.Method("get_permalink")
    media = fields.Method("get_media")


class MinStorageSchema(BaseSchema):
    class Meta:
        additional = ('id', 'final_price', 'vip_discount_price', 'vip_discount_percent')

    discount_price = fields.Method("get_discount_price")
    discount_percent = fields.Method("get_discount_percent")
    title = fields.Method('get_title')
    deadline = fields.Method("get_deadline")
    max_count_for_sale = fields.Method("get_max_count_for_sale")
    min_count_alert = fields.Method("get_min_count_alert")
    has_vip = fields.Method("check_has_vip")
    vip = fields.Method("is_vip")

    def check_has_vip(self, obj):
        if obj.discount_price > obj.vip_discount_price:
            return True
        return False

    def is_vip(self, obj):
        if self.vip:
            return self.vip
        return False

    def get_deadline(self, obj):
        try:
            return obj.deadline.timestamp()
        except Exception:
            pass

    def get_discount_price(self, obj):
        if self.vip:
            return obj.vip_discount_price
        return obj.discount_price

    def get_discount_percent(self, obj):
        if self.vip:
            return obj.vip_discount_percent
        return obj.discount_percent


class StorageSchema(MinStorageSchema):
    class Meta:
        additional = MinStorageSchema.Meta.additional + ('transportation_price', 'priority', 'gender', 'disable')

    default = fields.Function(lambda o: o == o.product.default_storage)
    features = FeatureField()


class BasketProductSchema(BaseSchema):
    class Meta:
        additional = ('id', 'count', 'item_final_price', 'item_discount_price', 'final_price', 'discount_price',
                      'discount_percent', 'tax', 'amer')

    product = fields.Method("get_min_product")
    features = fields.Method("get_feature")

    def get_feature(self, obj):
        res = []
        for feature in obj.features:
            feature_storage_id = feature['fsid']
            fvid_list = feature['fvid']
            fs = FeatureStorage.objects.get(storage=obj.storage, id=feature_storage_id)
            f = Feature.objects.get(pk=fs.feature.pk)
            feature_list = []
            for fvid in fvid_list:
                feature_name = next(i['name'][self.lang] for i in f.value if i['id'] == fvid)
                feature_price = next(i['price'] for i in fs.value if i['fvid'] == fvid)
                feature_list.append({'id': fs.pk, 'fvid': fvid, 'name': feature_name, 'price': feature_price})
            res.append({'id': f.pk, 'name': f.name[self.lang], "type": f.get_type_display(), "value": feature_list})

        return res


class BasketSchema(BaseSchema):
    class Meta:
        additional = ('id', 'description')

    products = fields.Function(lambda o: BasketProductSchema().dump(o.basket_products, many=True))


class InvoiceSchema(BaseSchema):
    class Meta:
        additional = ('id', 'amount', 'final_price')

    created_at = fields.Function(lambda o: o.created_at.timestamp())
    status = fields.Function(lambda o: o.get_status_display())


class InvoiceStorageSchema(BaseSchema):
    class Meta:
        additional = ('count', 'discount_price', 'final_price', 'discount_percent', 'vip_discount_price',
                      'vip_discount_percent', 'invoice_id', 'invoice_description')

    storage = fields.Method("get_storage")
    box = fields.Method("get_box")
    unit_price = fields.Function(lambda o: int(o.discount_price / o.count))
    purchase_date = fields.Function(lambda o: o.invoice.payed_at.timestamp())
    product = fields.Method("get_storage_product")
    user = fields.Function(lambda o: {"id": o.invoice.user_id, "first_name": o.invoice.user.first_name,
                                      "last_name": o.invoice.user.last_name})

    def get_storage_product(self, obj):
        p = obj.storage.product
        product = MinProductSchema(self.lang).dump(p)
        product['type'] = p.get_type_display()
        del product['rate'], product["default_storage"]
        try:
            product['invoice_description'] = p.invoice_description[self.lang]
        except AttributeError:
            product['invoice_description'] = p.invoice_description['fa']
        return product

    def get_storage(self, obj):
        storage = obj.storage
        storage = {"id": storage.pk, "title": storage.title[self.lang],
                   "invoice_description": storage.invoice_description[self.lang],
                   "invoice_title": storage.invoice_title[self.lang]}

        return storage


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
                                      "avatar": HOST + o.user.avatar.image.url if o.user.avatar else None})
    type = fields.Function(lambda o: o.get_type_display())
    reply_count = fields.Method('get_reply_count')
    created_at = fields.Function(lambda o: o.created_at.timestamp())
    purchase_at = fields.Method("get_purchase_time")
    satisfied = fields.Method("get_satisfied")
    first_reply = fields.Method("get_first_reply")

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
            return Invoice.objects.filter(user=obj.user, status=2,
                                          storages__product=obj.product).order_by('id').first().payed_at.timestamp()
        except Invoice.DoesNotExist:
            return None

    def get_reply_count(self, obj):
        comments = Comment.objects.filter(product=obj.product, type=obj.type, reply_to=obj)
        return comments.count()

    def get_first_reply(self, obj):
        if obj.type == 1 and self.get_reply_count(obj) >= 1:
            comment = obj.replys.order_by('id').first()
            return CommentSchema().dump(comment)
        return None


class UserCommentSchema(CommentSchema):
    product = fields.Method("get_min_product")


class MenuSchema(BaseSchema):
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
    thumbnail = fields.Method("get_thumbnail")
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
    product_permalink = fields.Method('get_min_product2')

    def get_min_product2(self, obj):
        try:
            return obj.storage.product.permalink
        except AttributeError:
            pass


class WalletDetailSchema(BaseSchema):
    class Meta:
        additional = ('id', 'credit', 'user')


class WishListSchema(BaseSchema):
    class Meta:
        additional = ('id', 'notify')

    product = fields.Method("get_min_product")
    # type = fields.Function(lambda o: o.get_type_display())


class NotifyUserSchema(BaseSchema):
    class Meta:
        additional = ('id', 'user', 'notify')

    product = fields.Method("get_product")
    type = fields.Function(lambda o: o.get_type_display())
    category = fields.Method("get_category")
    box = fields.Method("get_box")


class StateSchema(BaseSchema):
    class Meta:
        additional = ('id', 'name')


class CitySchema(Schema):
    class Meta:
        additional = ('id', 'name')

    state = fields.Function(lambda o: o.state_id)


class ResidenceTypeSchema(BaseSchema):
    cancel_rules = fields.Method("get_name")


class HousePriceSchema(BaseSchema):
    price = fields.Method("get_prices")

    @staticmethod
    def get_prices(obj):
        def add_days(days):
            return timezone.now() + timezone.timedelta(days=days)

        today = date.today()
        weekend = [5, 6]
        days_name = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه شنبه', 'چهارشنبه', 'پنجنشبه', 'جمعه']
        months_name = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن',
                       'اسفند']
        index = -1
        months = {'months': [], 'prev_month_days': (today.replace(day=1) - timedelta(days=1)).day,
                  'first_day': today.weekday(), 'guest_price': obj.price.guest}
        # costume_prices = CostumeHousePrice.objects.filter(house=obj)
        bookings = Booking.objects.filter(house=obj, confirm=True).values('start_date', 'end_date')
        holidays = Holiday.objects.filter(date__gte=add_days(0), date__lte=add_days(obj.future_booking_time))
        for day in range(obj.future_booking_time):
            price = dict()
            price['day_off'] = False
            price['date'] = today + timedelta(days=day)
            price['day'] = price['date'].day
            weekday = price['date'].weekday()
            price['weekday'] = days_name[weekday]
            if price['date'].day == 1 or not months['months']:
                index += 1
                prices = []
                months['months'].append({'month_name': months_name[price['date'].month - 1],
                                         'month': price['date'].month,
                                         'year': price['date'].year,
                                         'days': prices})
                if price['date'].day > 1:
                    for d in range(price['date'].day - 1)[::-1]:
                        old_date = today + timedelta(days=(d + 1) * -1)
                        weekday = old_date.weekday()
                        old_date = old_date.strftime("%Y-%m-%d")
                        months['months'][index]['days'].append(
                            {"date": old_date, "day": price['date'].day - d - 1,
                             "weekday": days_name[weekday], "available": False})

            for booking in bookings:
                price['available'] = True
                if booking['start_date'] <= price['date'] <= booking['end_date']:
                    price['available'] = False
                    break
            else:
                if holidays.filter(date=price['date'].togregorian(), day_off=True).exists():
                    price['price'] = obj.price.peak
                    price['day_off'] = True
                elif weekday in weekend:
                    price['price'] = obj.price.weekend
                else:
                    price['price'] = obj.price.weekday
                # for costume_price in costume_prices:
                #     if costume_price.start_date <= price['date'] <= costume_price.end_date:
                #         price['price'] = costume_price.price
                #         break
            price['date'] = price['date'].strftime("%Y-%m-%d")
            months['months'][index]['days'].append(price)
        last_date = today + timedelta(days=obj.future_booking_time)
        last_day_of_month = (last_date.replace(month=last_date.month + 1, day=1) - timedelta(days=1)).day
        for d in range(last_day_of_month - last_date.day + 1):
            today = last_date + timedelta(days=d)
            weekday = today.weekday()
            today = today.strftime("%Y-%m-%d")
            months['months'][index]['days'].append(
                {"date": today, "day": last_date.day + d,
                 "weekday": days_name[weekday], "available": False})
        return months


class HouseSchema(BaseSchema):
    class Meta:
        additional = ('notify_before_arrival', 'future_booking_time', 'meals')

    cancel_rules = fields.Method("get_cancel_rules")
    rules = fields.Method("get_rules")
    state = fields.Function(lambda o: o.state.name)
    city = fields.Function(lambda o: o.city.name)
    facilities = fields.Function(lambda o: o.facilities)
    capacity = fields.Function(lambda o: o.capacity)
    rent_type = fields.Method('get_rent_type')
    residence_area = fields.Method('get_residence_area')
    bedroom = fields.Function(lambda o: o.bedroom)
    safety = fields.Function(lambda o: o.safety)
    calender = fields.Function(lambda o: o.calender)
    residence_type = ResidenceTypeField()
    price = fields.Function(lambda o: HousePriceSchema().dump(o)['price'])

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
