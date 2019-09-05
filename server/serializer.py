import json
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
import pysnooper
from mehr_takhfif.settings import HOST, MEDIA_URL
import traceback

res = []


def serialize(obj, fields, language='persian', array=False):
    try:
        len(obj)
    except TypeError:
        obj = [obj]
    except AttributeError:
        return ''
    string_repr_of_obj = serializers.serialize("json", obj, fields=fields)
    json_repr_of_obj = json.loads(string_repr_of_obj)
    for item, index in zip(json_repr_of_obj, range(len(json_repr_of_obj))):
        item['fields']['id'] = item['pk']
        for field, i in zip(item['fields'], range(len(item['fields']))):
            try:
                item['fields'][field] = item['fields'][field][language]
            except Exception:
                try:
                    if type(item['fields'][field]) is list:
                        for j in range(len(item['fields'][field])):
                            price = item['fields'][field][j]['price']
                            item['fields'][field][j] = {'name': item['fields'][field][j][language]}
                            item['fields'][field][j]['price'] = price
                except Exception:
                    pass
        json_repr_of_obj[index] = item['fields']
    if 0 < len(json_repr_of_obj) < 2 and not array:
        json_repr_of_obj = json_repr_of_obj[0]
    return json_repr_of_obj


def get_media(obj, serialized_data):
    try:
        for s, o in zip(serialized_data, obj):
            s['media'] = None
            if o.media:
                s['media'] = media(o.media)
    except Exception:
        try:
            obj.media = media(obj.media)
        except Exception:
            pass
    return serialized_data


def get_product(obj, fields, array=False):
    serialized_data = serialize(obj, fields)
    try:
        for item, index in zip(serialized_data, range(len(serialized_data))):
            item['product'] = product(obj[index].product)
            item['product']['media'] = media(obj[index].product.media.all(), array=array)
    except TypeError:
        try:
            serialized_data['product'] = product(obj.product)
            serialized_data['product']['media'] = media(obj.product.media.all(), array=array)
        except AttributeError:
            serialized_data['product'] = product(obj[0].product)
            serialized_data['product']['media'] = media(obj[0].product.media.all(), array=array)
    return serialized_data


def product(obj, array=False):
    fields = ('id', 'category', 'test', 'media', 'name', 'permalink', 'gender', 'short_description', 'description',
              'location', 'usage_condition', 'type')
    serialized_data = serialize(obj, fields, array=array)
    return get_media(obj, serialized_data)


def user(obj, array=False):
    fields = ('id', 'first_name', 'last_name', 'language', 'email', 'sex',
              'phone', 'national_code', 'wallet_money', 'vip', 'access_token')
    return serialize(obj, fields, array=array)


def address(obj, array=False):
    fields = ('id', 'province', 'city', 'postal_code', 'address', 'location', 'user')
    return serialize(obj, fields, array=array)


def box(obj, array=False):
    fields = ('id', 'name', 'admin')
    return serialize(obj, fields, array=array)


def media(obj, array=False):
    fields = ('id', 'file', 'type', 'box')
    serialized_data = serialize(obj, fields, array=array)
    try:
        for item in serialized_data:
                item['file'] = HOST + MEDIA_URL + item['file']
    except TypeError:
        serialized_data['file'] = HOST + MEDIA_URL + serialized_data['file']
    except AttributeError:
        serialized_data['file'] = ''

    return serialized_data


def category(obj, array=False):
    fields = ('id', 'parent', 'name', 'box')
    serialize_data = serialize(obj, fields, array=array)
    return get_media(obj, serialize_data)


def feature_data(obj, array=False):
    fields = ('id', 'price', 'name')
    return serialize(obj, fields, array=array)


def feature(obj, array=False):
    fields = ('id', 'value', 'name')
    return serialize(obj, fields, array=array)


def storage(obj, array=False):
    fields = ('id', 'product', 'category', 'available_count_for_sale', 'start_price', 'final_price',
              'transportation_price', 'discount_price', 'discount_vip_price')
    return get_product(obj, fields, array=array)


def basket(obj, array=False):
    fields = ('id', 'product', 'user', 'count', 'description')
    return serialize(obj, fields, array=array)


def comment(obj, array=False):
    fields = ('id', 'text', 'user', 'reply', 'suspend', 'type')
    return serialize(obj, fields, array=array)


def factor(obj, array=False):
    fields = ('id', 'price', 'product', 'user', 'payed_at', 'successful', 'type', 'special_offer_id', 'address',
              'description', 'final_price', 'discount_price', 'count', 'tax', 'start_price')
    return serialize(obj, fields, array=array)


def menu(obj, array=False):
    fields = ('id', 'type', 'media', 'url', 'name', 'value', 'parent', 'priority')
    serialized_data = serialize(obj, fields, array=array)
    return get_media(obj, serialized_data)


def tag(obj, array=False):
    fields = ('id', 'box', 'name', 'product')
    return serialize(obj, fields, array=array)


def rate(obj, array=False):
    fields = ('id', 'user', 'rate', 'product')
    return serialize(obj, fields, array=array)


def slider(obj, array=False):
    fields = ('id', 'title', 'link', 'product', 'media', 'type')
    serialized_data = serialize(obj, fields, array=array)
    return get_media(obj, serialized_data)


def special_offer(obj, array=False):
    fields = ('id', 'name', 'code', 'user', 'product', 'not_accepted_products', 'box', 'category', 'end_date',
              'discount_price', 'discount_percent', 'vip_discount_price', 'vip_discount_percent', 'start_date',
              'least_count', 'peak_price', 'media')
    serialized_offer = serialize(obj, fields, array=array)
    return get_media(obj, serialized_offer)


def special_product(obj, array=False):
    fields = ('id', 'title', 'url', 'media', 'type', 'description')
    serialized_data = serialize(obj, fields, array=array)
    try:
        for item, index in zip(obj, range(len(obj))):
            serialized_data[index]['storage'] = storage(item.storage)
    except KeyError:
        serialized_data['storage'] = storage(obj[0].storage)
    return get_media(obj, serialized_data)


def wallet(obj, array=False):
    fields = ('id', 'credit', 'user')
    return serialize(obj, fields, array=array)


def blog(obj, array=False):
    fields = ('id', 'box', 'title', 'description', 'media')
    serialized_data = serialize(obj, fields, array=array)
    return get_media(obj, serialized_data)


def blog_post(obj, array=False):
    fields = ('id', 'blog', 'body', 'permalink', 'media')
    serialized_data = serialize(obj, fields, array=array)
    return get_media(obj, serialized_data)


def wishlist(obj, array=False):
    fields = ('id', 'user', 'type', 'notify', 'product')
    return serialize(obj, fields, array=array)


def notify(obj, array=False):
    fields = ('id', 'user', 'type', 'category', 'box')
    return serialize(obj, fields, array=array)


def tourism(obj, array=False):
    fields = ('id', 'date', 'date', 'price')
    return serialize(obj, fields, array=array)


def related_objects(objects):
    for item in objects:
        if type(item) == list:
            related_objects(item)
            continue
        item = {'model': item.__class__.__name__, 'data': item}
        res.append(item)
    return res
