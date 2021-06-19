import time
from datetime import date
from math import ceil

from jdatetime import date, timedelta
from marshmallow import Schema, fields

from mehr_takhfif.settings import SHORTLINK
from server.models import *


def get_tax(tax_type, discount_price, start_price=None):
    try:
        return {
            1: 0,
            2: ceil(discount_price - discount_price / 1.09),
            3: ceil((discount_price - start_price) - (discount_price - start_price) / 1.09)
        }[tax_type]
    except KeyError:
        return 0


# ManyToMany Relations

class MediaField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        media = ProductMedia.objects.filter(product=obj).select_related('media').order_by('priority')
        medias = ProductMediaSchema().dump(media, many=True)
        return [m['media'] for m in medias]


class FeatureField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        features = obj.features.all()
        return FeatureStorageSchema().dump(features, many=True)


class PackageItemsField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        items = Package.objects.filter(package_id=obj)
        return PackageItemSchema().dump(items, many=True)


class TagField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        # tags = list(ProductTag.objects.filter(product=obj).select_related('tag'))
        tags = list(ProductTag.objects.filter(product=obj))
        for tag_group in obj.tag_groups.all():
            tags += TagGroupTag.objects.filter(taggroup=tag_group)
        return TagSchema().dump(set(tags), many=True)


class CityField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        cities = value.all()
        return CitySchema().dump(cities, many=True)


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


class InvoiceStorageField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        invoice_storages = InvoiceStorage.objects.filter(invoice=obj)
        return InvoiceStorageSchema().dump(invoice_storages, many=True)


# Serializer


class BaseSchema(Schema):
    id = fields.Int()

    def __init__(self, language='fa', vip=False, user=None, is_mobile=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lang = language
        self.default_lang = 'fa'
        self.vip = vip
        self.user = user
        self.is_mobile = is_mobile

    def dump(self, *args, **kwargs):
        raw_data = super().dump(*args, **kwargs)
        if type(raw_data) is not list:
            return raw_data
        data = []
        for d in raw_data:
            if d not in data:
                data.append(d)
        try:
            data = sorted(data, key=lambda i: i['priority'])
        except (KeyError, TypeError):
            pass
        return data

    def get(self, name):
        try:
            if name.get(self.lang, None):
                return name[self.lang]
            return name[self.default_lang]
        except (KeyError, TypeError, AttributeError):
            return None

    def get_name(self, obj):
        return self.get(obj.name)

    def get_brand(self, obj):
        if obj.brand:
            return {"id": obj.brand_id, "name": self.get(obj.brand.name)}

    def get_value(self, obj):
        return self.get(obj.value)

    def get_title(self, obj):
        return self.get(obj.title)

    def get_address(self, obj):
        return self.get(obj.address)

    def get_short_address(self, obj):
        return self.get(obj.short_address)

    def get_short_description(self, obj):
        return self.get(obj.short_description)

    def get_description(self, obj):
        return self.get(obj.description['data'])

    def get_properties(self, obj):
        if obj.properties:
            return self.get(obj.properties)

    def get_details(self, obj):
        return self.get(obj.details)

    def get_box(self, obj):
        if obj.box_id is not None:
            return BoxSchema(self.lang, exclude=['media', 'children']).dump(obj.box)
        return None

    def get_parent(self, obj):
        if obj.parent is not None:
            return CategorySchema(self.lang, exclude=['media', 'box', 'children']).dump(obj.parent)
        return None

    def get_category(self, obj):
        categories = obj.categories.all()
        if categories:
            return CategorySchema(self.lang, exclude=['media', 'children']).dump(categories, many=True)
        return []

    def get_product(self, obj):
        if obj.product is not None:
            return ProductSchema(self.lang, self.user, exclude=['storages']).dump(obj.product)
        return None

    def get_house(self, obj):
        if hasattr(obj, 'house_id'):
            return HouseSchema(self.lang, self.user).dump(obj.house)
        return None

    def get_permalink(self, obj):
        if obj.product is not None:
            return obj.product.permalink
        return None

    def get_min_product(self, obj):
        try:
            return MinProductSchema(self.lang, self.user).dump(obj.product)
        except AttributeError:
            return MinProductSchema(self.lang, self.user).dump(obj.storage.product)
        except Exception:
            return None

    def get_storage(self, obj):
        if obj.storage is not None:
            return StorageSchema(self.lang, self.user).dump(obj.storage)
        return None

    def get_min_storage(self, obj):
        try:
            if hasattr(obj, 'house_id'):
                return {}
            if hasattr(obj, 'default_storage_id'):
                return MinStorageSchema(self.lang, vip=self.vip, user=self.user).dump(obj.default_storage)
            if hasattr(obj, 'storage_id'):
                return MinStorageSchema(self.lang, vip=self.vip, user=self.user).dump(obj.storage)
            return {}
        except Exception:
            return {}

    def get_comment(self, obj):
        if obj.reply_to is not None:
            return CommentSchema().dump(obj.reply_to)
        return None

    def get_comment_replies(self, obj):
        if hasattr(obj, 'replies'):
            return CommentSchema().dump(obj.replies, many=True)
        return None

    def get_media(self, obj):
        try:
            return MediaSchema(self.lang).dump(obj.media)
        except AttributeError:
            return None

    def get_media_link(self, obj):
        if obj.media is not None:
            return HOST + obj.media.image.url
        return None

    def get_thumbnail(self, obj):
        if obj.thumbnail is not None:
            return MediaSchema(self.lang).dump(obj.thumbnail)
        try:
            return MediaSchema(self.lang).dump(obj.storage.product.thumbnail)
        except Exception:
            return None

    def get_location(self, obj):
        try:
            if obj.location is not None:
                return {'lat': float(obj.location['lat']), 'lng': float(obj.location['lng'])}
        except (AttributeError, KeyError):
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
        if (obj.available_count_for_sale >= obj.max_count_for_sale) and (obj.max_count_for_sale != 0):
            return obj.max_count_for_sale
        if obj.available_count_for_sale > 1:
            return obj.available_count_for_sale - 1
        return obj.available_count_for_sale

    def get_vip_max_count_for_sale(self, obj):
        try:
            user_vip_prices = self.user.user_vip_prices.all().values_list('id', flat=True)
            if not user_vip_prices:
                return None
            storage_vip_prices = VipPrice.objects.filter(storage=obj)
            max_count_for_sale = obj.get_max_count()

            for vip_type in user_vip_prices:
                try:
                    vip = storage_vip_prices.get(vip_type=vip_type)
                    vip_max_count_for_sale = vip.max_count_for_sale
                    if vip_max_count_for_sale < max_count_for_sale:
                        max_count_for_sale = vip_max_count_for_sale
                except Exception:
                    continue
            return max_count_for_sale
        except AttributeError:
            return None

    def get_min_count_alert(self, obj):
        # if obj.available_count_for_sale <= obj.min_count_alert:
        #     return obj.available_count_for_sale
        return obj.min_count_alert

    def get_city(self, obj):
        try:
            return CitySchema().dump(obj.city)
        except AttributeError:
            pass

    def get_state(self, obj):
        try:
            return StateSchema().dump(obj.state)
        except AttributeError:
            pass

    def get_settings(self, obj):
        return obj.settings.get('ui', {})

    def get_date(self, obj, attr):
        try:
            return getattr(obj, attr).timestamp()
        except Exception as e:
            return None


class MinUserSchema(BaseSchema):
    class Meta:
        additional = ('first_name', 'last_name', 'username', 'meli_code')

    name = fields.Method("get_username")
    email = fields.Email()

    def get_username(self, obj):
        try:
            return obj.first_name + " " + obj.last_name
        except Exception:
            try:
                return obj.first_name
            except Exception:
                return None


class UserSchema(MinUserSchema):
    class Meta:
        additional = MinUserSchema.Meta.additional + ('gender', 'shaba')

    birthday = fields.Method("get_birthday")
    vip_type = fields.Method("get_vip_type")
    default_address = fields.Method('get_default_address')

    def get_default_address(self, obj):
        try:
            return AddressSchema().dump(obj.default_address)
        except Exception:
            return False

    def get_vip_type(self, obj):
        try:
            return obj.vip_types.all().value_List('name', flat=True)
        except Exception:
            return None

    def get_avatar(self, obj):
        try:
            return HOST + obj.avatar.image.url
        except Exception:
            pass

    def get_birthday(self, obj):
        try:
            # todo check
            return int(time.mktime(obj.birthday.timetuple()))
        except Exception:
            return None


class AddressSchema(BaseSchema):
    class Meta:
        additional = ('id', 'postal_code', 'address', 'location', 'name', 'phone')

    city = fields.Method("get_city")
    state = fields.Method('get_state')
    location = fields.Method('get_location')


class BoxSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink', 'priority')

    name = fields.Method("get_name")
    media = fields.Method('get_media')
    children = fields.Method('get_categories')

    def get_categories(self, obj):
        return CategorySchema(exclude=['box', 'media', 'parent']).dump(obj.prefetched_categories, many=True)


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
        additional = ('id', 'permalink', 'disable')

    name = fields.Method('get_name')
    parent = fields.Method('get_parent')
    media = fields.Method('get_media')
    box = fields.Method('get_box')
    children = fields.Method('get_children')

    def get_children(self, obj):
        try:
            return CategorySchema(exclude=['parent', 'media', 'box']).dump(obj.prefetched_children, many=True)
        except Exception:
            return []


class BoxCategoriesSchema(BaseSchema):
    class Meta:
        additional = ('id', 'permalink', 'disable', 'priority')

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
    name = fields.Method('get_name')
    settings = fields.Dict()


class FeatureGroupSchema(BaseSchema):
    priority = fields.Int()
    name = fields.Method('get_name')
    settings = fields.Method('get_settings')
    features = fields.Function(lambda o: [])

    def get_settings(self, obj):
        return obj.settings.get('ui', {})


class FeatureValueSchema(BaseSchema):
    name = fields.Method('get_value')
    settings = fields.Method("get_settings")
    priority = fields.Int()


class ProductFeatureSchema(BaseSchema):
    def __init__(self, list_of_values=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_of_values = list_of_values

    class Meta:
        additional = ('priority',)

    feature = fields.Method('get_feature')
    feature_value = fields.Method('get_feature_value')
    feature_settings = fields.Method('get_feature_settings')
    feature_groups = fields.Method("get_feature_groups")

    def get_feature_settings(self, obj):
        return obj.feature.settings.get('ui', {})

    def get_feature_groups(self, obj):
        try:
            return obj.feature_groups
        except Exception:
            return []

    def get_feature(self, obj):
        return self.get(obj.feature.name)

    def get_feature_value(self, obj):
        if self.list_of_values:
            return [FeatureValueSchema().dump(obj.feature_value)]
        return self.get(obj.feature_value.value)


class FeatureStorageSchema(BaseSchema):
    id = fields.Int()
    feature = fields.Method('get_feature')
    # value = fields.Function(lambda o: o.value)


class TagSchema(BaseSchema):
    id = fields.Function(lambda o: o.tag.pk)
    name = fields.Method('get_name')
    permalink = fields.Function(lambda o: o.tag.permalink)
    show = fields.Boolean()

    def get_name(self, obj):
        return self.get(obj.tag.name)


class BrandSchema(BaseSchema):
    id = fields.Int()
    name = fields.Method('get_name')
    permalink = fields.Str()


class AccessorySchema(BaseSchema):
    class Meta:
        # additional = ('id', 'name', 'price', 'thumbnail')
        additional = ('id', 'discount_price')

    storage_id = fields.Function(lambda o: o.accessory_storage_id)
    name = fields.Function(lambda o: o.accessory_storage.title['fa'])
    thumbnail = fields.Function(lambda o: HOST + o.accessory_product.thumbnail.image.url)
    final_price = fields.Method("get_final_price")

    def get_final_price(self, obj):
        return obj.accessory_storage.final_price


class MinProductSchema(BaseSchema):
    def __init__(self, colors=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if colors is None:
            colors = {}
        self.colors = colors

    class Meta:
        additional = ('id', 'permalink', 'rate', 'disable', 'available')

    name = fields.Method("get_name")
    thumbnail = fields.Method("get_thumbnail")
    default_storage = fields.Method("get_min_storage")
    colors = fields.Method('get_colors')

    def get_colors(self, obj):
        colors = []
        distinct = []
        for item in getattr(obj, 'colors', []):
            if item.feature_value_id not in distinct:
                try:
                    image = HOST + item.product_feature_storages.first().storage.media.image.url
                except AttributeError:
                    image = ''
                color = next((color for color in self.colors if color['id'] == item.feature_value_id), {})
                color_hex = color.get('color')
                color_name = color.get('name')
                colors.append({'id': item.feature_value_id, 'color': color_hex, 'name': color_name, 'image': image})
                distinct.append(item.feature_value_id)
        return colors


class ProductSchema(MinProductSchema):
    class Meta:
        additional = MinProductSchema.Meta.additional + ('gender', 'permalink')

    default_storage = fields.Function(lambda o: None)
    address = fields.Method("get_address")
    short_address = fields.Method("get_short_address")
    type = fields.Function(lambda o: o.get_type_display())
    brand = fields.Method("get_brand")
    box = fields.Method("get_box")
    categories = fields.Method("get_category")
    house = fields.Method("get_house")
    tags = fields.Method("get_tags")
    media = MediaField()
    short_description = fields.Method("get_short_description")
    description = fields.Method("get_description")
    properties = fields.Method("get_properties")
    details = fields.Method("get_details")
    location = fields.Method("get_location")
    cities = fields.Method("get_cities")
    states = fields.Method("get_states")
    # todo make it day for long hours
    max_shipping_time = fields.Int()
    review_count = fields.Method("get_review_count")
    storages = fields.Method("get_storages")
    shortlink = fields.Method("get_shortlink")

    def get_shortlink(self, obj):
        return f"{SHORTLINK}/p/{obj.pk}"

    def get_storages(self, obj):
        storages = StorageSchema(only=['id', 'discount_price', 'max_count_for_sale']).dump(obj.storages.all(),
                                                                                           many=True)
        return sorted(storages, key=lambda i: i['discount_price'])

    def get_tags(self, obj):
        # tags = list(ProductTag.objects.filter(product=obj))
        tags = list(obj.product_tags.all())
        for tag_group in obj.tag_groups.all():
            # tags += TagGroupTag.objects.filter(taggroup=tag_group)
            tags += tag_group.tag_group_tags.all()
        return TagSchema().dump(set(tags), many=True)

    def get_review_count(self, obj):
        try:
            return obj.review_count
        except AttributeError:
            return 0

    def get_cities(self, obj):
        cities = obj.cities.all()
        return CitySchema().dump(cities, many=True)

    def get_states(self, obj):
        states = obj.states.all()
        return StateSchema().dump(states, many=True)


class ProductMediaSchema(BaseSchema):
    media = fields.Method("get_media")


class MinStorageSchema(BaseSchema):
    discount_price = fields.Method("get_discount_price")
    final_price = fields.Method("get_final_price")
    discount_percent = fields.Method("get_discount_percent")
    title = fields.Method('get_title')
    deadline = fields.Method("get_deadline")
    max_count_for_sale = fields.Method("get_max_count_for_sale")
    min_count_alert = fields.Method("get_min_count_alert")
    vip_type = fields.Method("get_vip_type")
    vip_max_count_for_sale = fields.Method("get_vip_max_count_for_sale")
    max_shipping_time = fields.Int()

    def get_vip_type(self, obj):
        try:
            vip_prices = obj.vip_prices.all()
            return min(vip_prices, key=attrgetter('discount_price')).vip_type.name
            # return VipPrice.objects.filter(storage_id=obj.pk).order_by('discount_price').first().vip_type.name
        except Exception:
            return None

    def get_deadline(self, obj):
        try:
            return obj.deadline.timestamp()
        except Exception:
            pass

    def get_discount_price(self, obj):
        min_price = 0
        if obj.available_count_for_sale > 0:
            min_price = obj.discount_price
        if getattr(getattr(self, 'user', None), 'is_authenticated', None):
            user_groups = self.user.vip_types.all()
            prices = obj.vip_prices.all()
            prices = sorted(prices, key=lambda o: o.discount_price)
            for price in prices:
                if price.available_count_for_sale > 0 and price.storage_id == obj.pk and price.vip_type in user_groups:
                    min_price = price.discount_price
                    break
        return min_price

    def get_final_price(self, obj):
        if obj.available_count_for_sale > 0:
            return obj.final_price
        return 0

    def get_discount_percent(self, obj):
        # try:
        #     user_groups = self.user.vip_types.all()
        #     prices = VipPrice.objects.filter(storage_id=obj.pk, available_count_for_sale__gt=0,
        #                                      vip_type__in=user_groups).values_list('discount_percent', flat=True)
        #     return min(prices)
        # except Exception:
        #     if obj.available_count_for_sale > 0:
        #         return obj.discount_percent
        #     return 0
        min_percent = 0
        if obj.available_count_for_sale > 0:
            min_percent = obj.discount_percent
        if getattr(getattr(self, 'user', None), 'is_authenticated', None):
            user_groups = self.user.vip_types.all()
            prices = obj.vip_prices.all()
            prices = sorted(prices, key=lambda o: o.discount_percent)
            for price in prices:
                if price.available_count_for_sale > 0 and price.storage_id == obj.pk and price.vip_type in user_groups:
                    min_percent = price.discount_percent
                    break
        return min_percent


class StorageSchema(MinStorageSchema):
    class Meta:
        additional = ('shipping_cost', 'priority', 'gender', 'disable')

    # todo optimize
    default = fields.Function(lambda o: o == o.product.default_storage)
    features = FeatureField()
    least_booking_time = fields.Method("get_least_booking_time")
    booking_cost = fields.Method("get_booking_cost")
    invoice_title = fields.Method('get_invoice_title')
    accessories = fields.Method("get_accessories")

    def get_accessories(self, obj):
        try:
            return AccessorySchema().dump(obj.accessory, many=True)
        except AttributeError:
            return AccessorySchema().dump(obj.storage_accessories.all().select_related('accessory_product__thumbnail',
                                                                                       'accessory_storage'), many=True)

    def get_least_booking_time(self, obj):
        if obj.product.booking_type == 1:  # unbookable
            return -1
        return obj.least_booking_time

    def get_booking_cost(self, obj):
        if obj.product.booking_type == 1:  # unbookable
            return -1
        return obj.booking_cost

    def get_invoice_title(self, obj):
        return self.get(obj.invoice_title)


class PackageSchema(StorageSchema):
    items = PackageItemsField()
    discount_price = fields.Int()
    final_price = fields.Int()


class PackageItemSchema(BaseSchema):
    count = fields.Int()
    title = fields.Method("get_item_title")

    def get_item_title(self, obj):
        try:
            return obj.package_item.title[self.lang]
        except AttributeError:
            return None


class BasketProductSchema(BaseSchema):
    class Meta:
        additional = ('id', 'count', 'item_final_price', 'item_discount_price', 'final_price', 'discount_price',
                      'discount_percent', 'tax', 'amer')

    product = fields.Method("get_min_product")
    features = fields.Method("get_feature")
    accessories = fields.Method("get_accessories")

    def get_accessories(self, obj):
        if hasattr(obj, 'accessories'):
            return BasketProductSchema(exclude=['accessories']).dump(obj.accessories, many=True)
        return None

    def get_feature(self, obj):
        features = obj.storage.features.all()
        return ProductFeatureSchema().dump(features, many=True)

    def get_min_product(self, obj):
        return MinProductSchema(self.lang, self.user, exclude=['available']).dump(obj.storage.product)


class BasketSchema(BaseSchema):
    class Meta:
        additional = ('id', 'description')

    def __init__(self, nested_accessories=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nested_accessories = nested_accessories

    products = fields.Method("get_basket_products")

    def get_basket_products(self, obj):
        basket_products = list(obj.basket_products)
        if self.nested_accessories:
            for bp in basket_products:
                if bp.accessory_id:
                    storage = next((item for item in basket_products
                                    if item.storage_id == bp.accessory.storage_id
                                    and bp.storage_id == bp.accessory.accessory_storage_id), None)
                    if storage:
                        if hasattr(storage, 'accessories') is False:
                            storage.accessories = []
                        basket_products[basket_products.index(storage)].accessories.append(bp)
                        # storage.accessories.append(bp)
                        basket_products.remove(bp)

        return BasketProductSchema().dump(basket_products, many=True)


class InvoiceSchema(BaseSchema):
    def __init__(self, with_shipping_cost=False, invoice_storage_only_field=None,
                 storage_only_field=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.with_shipping_cost = with_shipping_cost
        self.invoice_storage_only_field = invoice_storage_only_field
        self.storage_only_field = storage_only_field

    class Meta:
        additional = ('id', 'final_price', 'invoice_discount', 'details')

    payed_at = fields.Method('get_payed_at')
    status = fields.Function(lambda o: o.get_status_display())
    address = fields.Dict()
    storages = fields.Method('get_invoice_storages')
    amount = fields.Method('get_amount')  # without tax
    created_at = fields.Method("get_created_at_date")
    expire = fields.Method("get_expire_date")
    start_date = fields.Method("get_start_date")
    end_date = fields.Method("get_end_date")
    invoice = fields.Method("get_invoice_file")
    booking_type = fields.Method("get_booking_type")
    payment_url = fields.Method("get_payment_url")

    def get_invoice_storages(self, obj):
        only = {}
        if self.invoice_storage_only_field:
            only = {'only': self.invoice_storage_only_field}
        invoice_storages = obj.invoice_storages.all()
        return InvoiceStorageSchema(**only, storage_only_field=self.storage_only_field).dump(invoice_storages,
                                                                                             many=True)

    def get_payment_url(self, obj):
        if self.only:
            if 'payment_url' in getattr(self, 'only', []):
                if obj.status == 1:
                    return f"{HOST}/repay/{obj.pk}"

    def get_booking_type(self, obj):
        if not obj.start_date:
            return 'unbookable'
        if obj.start_date == obj.end_date:
            return 'datetime'
        return 'range'

    def get_start_date(self, obj):
        return self.get_date(obj, 'start_date')

    def get_created_at_date(self, obj):
        return self.get_date(obj, 'created_at')

    def get_expire_date(self, obj):
        return self.get_date(obj, 'expire')

    def get_end_date(self, obj):
        return self.get_date(obj, 'end_date')

    def get_invoice_file(self, obj):
        try:
            if self.user.is_staff or obj.get_type_display == 'payed':
                return HOST + f'/invoice_detail/{obj.id}'
        except AttributeError:
            return None

    def get_amount(self, obj):
        # if InvoiceStorage.objects.filter(invoice=obj).exists():
        #     prices = InvoiceStorage.objects.filter(invoice=obj).values_list('discount_price', flat=True)
        #     return sum(prices)
        if self.with_shipping_cost:
            return obj.amount + getattr(getattr(obj, 'post_invoice', None), 'amount', 0)
        return obj.amount

    def get_payed_at(self, obj):
        return self.get_date(obj, 'payed_at')


class InvoiceStorageSchema(BaseSchema):
    def __init__(self, storage_only_field=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage_only_field = storage_only_field

    class Meta:
        additional = ('count', 'discount_price', 'final_price', 'discount_percent', 'discount_price_without_tax',
                      'invoice_id', 'invoice_description', 'details', 'tax', 'discount', 'total_price')

    storage = fields.Method("get_storage")
    unit_price = fields.Function(lambda o: int(o.discount_price / o.count))
    purchase_date = fields.Method('get_purchase_date')
    product = fields.Method("get_storage_product")
    features = fields.Dict()
    amer = fields.Method("get_amer")
    discount_file = fields.Method('get_discount_file')

    def get_discount_file(self, obj):
        if obj.key:
            return SHORTLINK + f"/{obj.key}"

    def get_amer(self, obj):
        return self.get_name(obj.storage.product.box)

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
        # storage = obj.storage
        # storage = {"id": storage.pk, "title": storage.title[self.lang],
        #            "invoice_description": storage.invoice_description[self.lang],
        #            "invoice_title": storage.invoice_title[self.lang]}
        #
        # return storage
        return StorageSchema(only=('id', 'title', 'invoice_title')).dump(obj.storage)

    def get_purchase_date(self, obj):
        try:
            return obj.invoice.payed_at.timestamp()
        except AttributeError:
            return None


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

    user = fields.Nested(MinUserSchema)
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
        except AttributeError:
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
        additional = ('id', 'url', 'box_id')

    name = fields.Method('get_name')
    default_storage = fields.Method('get_min_storage')
    # media = fields.Method('get_media')
    thumbnail = fields.Method("get_thumbnail")
    permalink = fields.Function(lambda o: o.storage.product.permalink)
    box = fields.Method("get_box")

    def get_name(self, obj):
        name = self.get(obj.name)
        if name:
            return name
        return self.get(obj.storage.title)


class AdSchema(BaseSchema):
    class Meta:
        additional = ('id', 'url', 'priority')

    title = fields.Method('get_title')
    media = fields.Method('get_media')
    product_permalink = fields.Method('get_permalink')

    def get_permalink(self, obj):
        try:
            return obj.storage.product.permalink
        except AttributeError:
            pass

    def get_media(self, obj):
        try:
            if self.is_mobile:
                return MediaSchema(self.lang).dump(obj.mobile_media)
            return MediaSchema(self.lang).dump(obj.media)
        except AttributeError:
            return None


class SliderSchema(BaseSchema):
    class Meta:
        additional = ('id', 'url', 'priority')

    title = fields.Method('get_title')
    product = fields.Method("get_permalink")
    media = fields.Method("get_media")

    def get_permalink(self, obj):
        try:
            return obj.storage.product.permalink
        except AttributeError:
            pass

    def get_media(self, obj):
        try:
            if self.is_mobile:
                return MediaSchema(self.lang).dump(obj.mobile_media)
            return MediaSchema(self.lang).dump(obj.media)
        except AttributeError:
            return None


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


class GCMDeviceSchema(Schema):
    class Meta:
        additional = ('id', 'name')

    # user = fields.Method('get_user')

    def get_user(self, obj):
        return obj.user.first_name + " " + obj.user.last_name
