import difflib
import json
import math

import jwt
import magic
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.db.models import F
from django.views import View
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from datetime import datetime
import pysnooper

from mehr_takhfif import settings
from mehr_takhfif.settings import TOKEN_SECRET, SECRET_KEY
from server.models import *
from server.serialize import BoxCategoriesSchema, BasketSchema, BasketProductSchema, MinProductSchema

default_step = 12
default_page = 1
default_response = {'ok': {'message': 'ok'}, 'bad': {'message': 'bad request'}}
pattern = {'phone': r'^(09[0-9]{9})$', 'email': r'^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\
           [[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$',
           'postal_code': r'^\d{5}[ -]?\d{5}$', 'fullname': r'^[آ-یA-z]{2,}( [آ-یA-z]{2,})+([آ-یA-z]|[ ]?)$',
           'address': r'(([^ -_]+)[\n -]+){2}.+', 'location': '', 'bool': r'^(true|false)$', 'name': r'^[ آ-یA-z]+$',
           'id': r'^\d+$', 'language': r'^\w{2}$', 'type': r'^[A-z]+$'}
ids = ['id', 'city_id', 'state_id', 'product_id']
bools = ['gender', 'set_default', 'notify']


def validation(data):
    try:
        for key in data:
            if key in ids:
                assert re.search(pattern['id'], data[key])
                continue
            if key in bools:
                assert type(data[key]) == bool
                continue
            assert re.search(pattern[key], data[key])
    except (AssertionError, KeyError):
        raise ValidationError(message='validation error')


def load_data(request):
    data = json.loads(request.body)
    validation(data)
    return data


# def validation_old(data, allow_null=False):
#     try:
#         for key in args:
#             if key in ids:
#                 assert re.search(pattern['id'], data[key])
#                 continue
#             assert re.search(pattern[key], data[key])
#     except AssertionError:
#         raise ValidationError(message='validation error')
#     except KeyError:
#         if not allow_null:
#             raise ValidationError(message='validation error')
#         pass


def safe_delete(obj, user_id):
    obj.deleted_by_id = user_id
    obj.delete()


def to_json(obj=None, string=None):
    if obj is not list:
        obj = [obj]
    if obj:
        string = serializers.serialize("json", obj)
    return json.loads(string[1:-1])['fields']


def add_minutes(minutes, time=None):
    return (time or timezone.now()) + timezone.timedelta(minutes=minutes)


def add_days(days):
    return timezone.now() + timezone.timedelta(days=days)


def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(timestamp)


def generate_token(user):
    expire = add_days(30).timestamp()
    data = {'username': user.phone, 'expire': expire}
    return {'token': hsencode(data, SECRET_KEY), 'expire': expire}


def generate_token_old(request, user):
    data = {'user': f'{user.last_login}'}
    first_encrypt = jwt.encode(data, TOKEN_SECRET, algorithm='HS256')
    secret = token_hex(10)
    second_encrypt = jwt.encode({'data': first_encrypt.decode()}, secret, algorithm='HS256')
    access_token = f'{second_encrypt.decode()}{secret}'
    request.session['counter'] = 0
    return access_token


def hsencode(data, secret=SECRET_KEY):
    return jwt.encode(data, secret, algorithm='HS256').decode()


def hsdecode(token, secret=SECRET_KEY):
    return jwt.decode(token, secret, algorithms=['HS256'])


def get_token_data(token):
    first_decrypt = jwt.decode(token[7:-52], token[-52:-32], algorithms=['HS256'])
    return jwt.decode(first_decrypt['data'].encode(), TOKEN_SECRET, algorithms=['HS256'])


def upload(request, title=None, box=None, avatar=False):
    image_formats = ['.jpeg', '.jpg', '.gif', '.png']
    video_formats = ['.avi', '.mp4', '.mkv', '.flv', '.mov', '.webm', '.wmv']
    for file in request.FILES.getlist('file'):
        if file is not None:
            file_format = os.path.splitext(file.name)[-1]
            mimetype = get_mimetype(file).split('/')[0]
            if mimetype == 'image':
                if file_format not in image_formats:
                    return False
            if mimetype == 'video' and file_format not in video_formats:
                return False
            if avatar and title:
                file.name = f"{title['user_id']} {datetime.now().strftime('%Y-%m-%d, %H-%M-%S')}{file_format}"
            else:
                data = json.loads(request.POST.get('data'))
                title = data['title']
            media = Media(file=file, box_id=box, created_by_id=1, type='avatar' if avatar else mimetype,
                          title=title, updated_by=request.user)
            media.save()
            return media


def get_mimetype(image):
    mime = magic.Magic(mime=True)
    mimetype = mime.from_buffer(image.read(1024))
    image.seek(0)
    return mimetype


def move(obj, folder):
    old_path = obj.file.path
    new_path = settings.MEDIA_ROOT + f'\\{folder}\\' + obj.file.name
    try:
        os.rename(old_path, new_path)
    except FileNotFoundError:
        os.makedirs(settings.MEDIA_ROOT + f'\\{folder}\\')
        os.rename(old_path, new_path)
    finally:
        obj.save()


def filter_params(params):
    if not params:
        return {'filter': {}, 'order': {}}
    ds = 'default_storage__'
    dis = 'discount'
    filters = (f'{ds}{dis}_price', f'{ds}{dis}_vip_price', f'{ds}{dis}_percent', f'{ds}{dis}_vip_percent',
               'product__sold_count')
    valid_orders = {'cheap': f'-{ds}{dis}_price', 'expensive': f'{ds}{dis}_price',
                    'best_seller': f'{ds}sold_count', 'popular': '-created_at', 'discount': f'-{ds}{dis}discount_percent'}
    filters_op = ('__gt', '__gte', '__lt', '__lte')
    valid_filters = [x + y for y in filters_op for x in filters]
    filter_by = {}
    orderby = '-created_at'
    try:
        keys = params.keys()
        for key in keys:
            if len(key) < 3:
                continue
            if key == 'orderby':
                valid_key = valid_orders[f'{params[key]}']
                orderby = valid_key
            value = params.getlist(key)
            if len(value) == 1:
                valid_key = difflib.get_close_matches(key, valid_filters)[0]
                filter_by[valid_key] = value[0]
                continue
            filter_by[key + '__in'] = value
    except Exception:
        pass
    return {'filter': filter_by, 'order': orderby}


def get_categories(language, box_id=None, category=None):
    if category is None:
        try:  # todo delete assert
            assert True is False
            category = Category.objects.filter(box_id=box_id)
        except Exception as e:
            category = Category.objects.all()
    new_cats = [*category]
    remove_index = []
    for cat, index in zip(category, range(len(category))):
        if cat.parent is None:
            continue
        parent_index = new_cats.index(category.filter(pk=cat.parent_id).first())
        if not hasattr(new_cats[parent_index], 'child'):
            new_cats[parent_index].child = []
        new_cats[parent_index].child.append(cat)
        remove_index.append(cat)
    new_cats = [x for x in new_cats if x not in remove_index]
    return BoxCategoriesSchema(language=language).dump(new_cats, many=True)


def last_page(query, step):
    items = query.count()
    return {'pagination': {'last_page': math.ceil(items / step), 'items': items}}


def user_data_with_pagination(model, serializer, request):
    objects = model.objects.filter(user=request.user)
    last_page_info = last_page(objects, request.step)
    objects = objects[(request.page - 1) * request.step:request.step * request.page]
    objects = serializer().dump(objects, many=True)
    return {'data': objects, **last_page_info}


def des_encrypt(data='test', key=os.urandom(16)):
    backend = default_backend()
    text = data.encode()
    padder = padding.PKCS7(algorithms.TripleDES.block_size).padder()
    cipher = Cipher(algorithms.TripleDES(key), modes.ECB(), backend=backend)
    encryptor = cipher.encryptor()
    encrypted_text = encryptor.update(padder.update(text) + padder.finalize()) + encryptor.finalize()
    decrypted_text = des_decrypt(encrypted_text, key)
    assert text == decrypted_text
    return encrypted_text


def des_decrypt(encrypted_text, key):
    backend = default_backend()
    unpadder = padding.PKCS7(algorithms.TripleDES.block_size).unpadder()
    cipher = Cipher(algorithms.TripleDES(key), modes.ECB(), backend=backend)
    decryptor = cipher.decryptor()
    return unpadder.update(decryptor.update(encrypted_text) + decryptor.finalize()) + unpadder.finalize()


def calculate_profit(products):
    # TypeError: default storage is list but have one member
    total_price = sum([product['product']['default_storage']['final_price'] * product['count']
                       for product in products])
    discount_price = sum(
        [product['product']['default_storage']['discount_price'] * product['count'] for product in products])
    profit = total_price - discount_price
    return {'total_price': total_price, 'discount_price': discount_price, 'profit': profit, 'shopping_cost': 0}


def get_basket(user, lang, basket=None):
    basket = basket or Basket.objects.filter(user=user, active=True).first()
    if basket is None:
        return {}
    basket_products = BasketProduct.objects.filter(basket=basket).select_related(*BasketProduct.related)
    address_required = False
    profit = {}
    if basket.products.all().count() > 0:
        for basket_product in basket_products:
            basket_product.product = basket_product.storage.product
            basket_product.product.default_storage = basket_product.storage
            if basket_product.product.type == 'product' and not address_required:
                address_required = True
        basket_dict = BasketSchema(lang).dump(basket)
        basket_dict['products'] = BasketProductSchema().dump(basket_products, many=True)
        profit = calculate_profit(basket_dict['products'])
    else:
        basket_dict = {}
    return {'basket': basket_dict, 'summary': profit, 'address_required': address_required}


def get_best_seller(box, basket_ids, language):
    # from invoices
    basket_products = BasketProduct.objects.filter(basket_id__in=basket_ids, box=box).values('storage', 'count')
    storage_count = {}
    for product in basket_products:
        if product['storage'] in storage_count.keys():
            storage_count[product['storage']] += product['count']
            continue
        storage_count[product['storage']] = product['count']
    storage_count = {k: v for k, v in sorted(storage_count.items(), key=lambda item: item[1], reverse=True)}
    storage_ids = storage_count.keys()
    storages = Storage.objects.filter(pk__in=storage_ids)
    products = Product.objects.filter(storage__in=storages)
    sync_default_storage(storages, products)
    return MinProductSchema(language=language).dump(products, many=True)


def sync_default_storage(storages, products):
    for storage, product in zip(storages, products):
        if product.default_storage == storage:
            continue
        if storage.product == product:
            product.default_storage = storage


def sync_storage(basket_id, op):
    basket_products = BasketProduct.objects.filter(basket_id=basket_id)
    for basket_product in basket_products:
        storage = basket_product.storage
        count = basket_product.count
        storage.available_count = op(F('available_count'), count)
        storage.available_count_for_sale = op(F('available_count_for_sale'), count)
        storage.sold_count = op(F('sold_count'), count)
        storage.save()


def to_obj(body):
    dic = json.loads(body)
    obj = type('test', (object,), {})()
    obj.__dict__ = dic
    return obj


def load_location(location):
    return {"lat": location[0], "lng": location[1]}


def add_one_off_job(name, args=None, kwargs=None, task='server.tasks.hello', interval=30,
                    period=IntervalSchedule.MINUTES):
    schedule, created = IntervalSchedule.objects.get_or_create(every=interval, period=period)
    task, created = PeriodicTask.objects.get_or_create(interval=schedule, name=name, task=task, one_off=True,
                                                       args=json.dumps(args), kwargs=json.dumps(kwargs))
    return task


# def products_availability_check(products, step, page):
#     count = 0
#     available_products = []
#     for product in products:
#         storages = Storage.objects.filter(available_count_for_sale__gt=0, product=product).exists()
#         if storages:
#             count += 1
#             available_products.append(product)
#             if count == step:
#                 break
#             continue
#     return available_products


# def available_products2(products):
#     storages = Storage.objects.filter(available_count_for_sale__gt=0, product__in=products)
#     for storage in storages:
#
#     if storages:
#         continue
#     products.remove(product)
#     return products


class LoginRequired(LoginRequiredMixin, View):
    raise_exception = True


class Validation(View):
    def __init__(self):
        super().__init__()
        self.phone_pattern = r'^(09[0-9]{9})$'
        self.email_pattern = r'^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$'
        self.postal_pattern = r'^\d{5}[ -]?\d{5}$'
        self.fullname_pattern = r'^[آ-یA-z]{2,}( [آ-یA-z]{2,})+([آ-یA-z]|[ ]?)$'
        self.activate_pattern = 'test'

    def regex(self, data, pattern, error, raise_error=True):
        data = re.search(pattern, f'{data}')
        if data is None:
            if raise_error:
                raise ValidationError(error)
            return None
        return data[0]

    def valid_phone(self, text, raise_error=True):
        return self.regex(text, self.phone_pattern, 'phone is invalid', raise_error)

    def valid_email(self, text, raise_error=True):
        return self.regex(text, self.email_pattern, 'email is invalid', raise_error)


class ORM:
    @staticmethod
    def get_menu():
        return Menu.objects.select_related('media', 'parent').all()

    @staticmethod
    def get_special_offer():
        return SpecialOffer.objects.select_related('media').all()

    @staticmethod
    def get_special_product():
        return SpecialProduct.objects.select_related('storage', 'storage__product', 'media').all()

    @staticmethod
    def get_best_seller(count=5):
        return Storage.objects.select_related('product', 'product__thumbnail').filter(
            default=True).order_by('-product__sold_count')[:count]

    @staticmethod
    def get_most_discounted(count=5):
        return Storage.objects.select_related('product', 'product__thumbnail').filter(
            default=True).order_by('-product__sold_count')[:count]

    @staticmethod
    def get_cheapest(count=5):
        return Storage.objects.select_related('product', 'product__thumbnail').filter(
            default=True).order_by('-product__sold_count')[:count]

    @staticmethod
    def get_most_expensive(count=5):
        return Storage.objects.select_related('product', 'product__thumbnail').filter(
            default=True).order_by('-product__sold_count')[:count]

    @staticmethod
    def get_latest(count=5):
        return Storage.objects.select_related('product', 'product__thumbnail').filter(
            default=True).order_by('-product__sold_count')[:count]
