import difflib
import json
import math
import traceback
import hashlib
import uuid
import magic
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.db.models import F
from django.core.mail import send_mail
from django.views import View
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from datetime import datetime
import pysnooper
from operator import add, sub
from secrets import token_hex
from server.error import *
from mehr_takhfif.settings import CSRF_SALT, TOKEN_SALT, MEDIA_ROOT
from server.models import *
import requests
from server.serialize import MediaSchema
from server.serialize import BoxCategoriesSchema, BasketSchema, BasketProductSchema, MinProductSchema

default_step = 12
default_page = 1
default_response = {'ok': {'message': 'ok'}, 'bad': {'message': 'bad request'}}
res_code = {'success': 200, 'bad_request': 400, 'unauthorized': 401, 'forbidden': 403, 'token_issue': 401,
            'integrity': 406, 'banned': 493,
            'signup_with_pp': 251, 'invalid_password': 450, 'signup_with_pass': 201, 'activate': 202}
pattern = {'phone': r'^(09[0-9]{9})$', 'email': r'^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\
           [[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$',
           'postal_code': r'^\d{5}[ -]?\d{5}$', 'fullname': r'^[آ-یA-z]{2,}( [آ-یA-z]{2,})+([آ-یA-z]|[ ]?)$',
           'address': r'(([^ -_]+)[\n -]+){2}.+', 'location': r'\.*', 'bool': r'^(true|false)$',
           'name': r'^[ آ-یA-z]+$', 'first_name': r'^[ آ-یA-z]+$', 'last_name': r'^[ آ-یA-z]+$',
           'id': r'^\d+$', 'language': r'^\w{2}$', 'type': r'^[1-2]$'}
ids = ['id', 'city_id', 'state_id', 'product_id', 'house_id']
bools = ['gender', 'set_default', 'notify']


# Data

def validation(data):
    for key in data:
        if key in ids:
            assert re.search(pattern['id'], str(data[key]))
            continue
        if key in bools:
            assert type(data[key]) == bool
            continue
        if key == 'basket':
            assert len(key) < 20
        try:
            assert re.search(pattern[key], str(data[key]))
        except KeyError:
            pass


def load_data(request, check_token=True):
    data = json.loads(request.body)
    validation(data)
    return data


def add_minutes(minutes, time=None):
    return (time or timezone.now()) + timezone.timedelta(minutes=minutes)


def add_days(days):
    return timezone.now() + timezone.timedelta(days=days)


def get_mimetype(image):
    mime = magic.Magic(mime=True)
    mimetype = mime.from_buffer(image.read(1024))
    image.seek(0)
    return mimetype


def upload(request, titles, media_type, box=None):
    image_formats = ['.jpeg', '.jpg', '.gif', '.png']
    audio_formats = ['.jpeg', '.jpg', '.gif', '.png']
    types = {'image': 1, 'thumbnail': 2, 'slider': 3, 'ads': 4, 'avatar': 7}
    media_list = []
    for file, title in zip(request.FILES.getlist('file'), titles):
        if file is not None:
            file_format = os.path.splitext(file.name)[-1]
            mimetype = get_mimetype(file).split('/')[0]
            if (mimetype == 'image' and file_format not in image_formats) or \
                    (mimetype == 'audio' and file_format not in audio_formats) or \
                    (mimetype != 'image' and mimetype != 'audio'):
                return False

            if media_type == 'avatar' and title == str:
                file.name = f"{title['user_id']} {datetime.now().strftime('%Y-%m-%d, %H-%M-%S')}{file_format}"
            media = Media(file=file, box_id=box, created_by_id=1, type=types[media_type],
                          title=title, updated_by=request.user)
            media.save()
            media_list.append(media)
    return media_list


def filter_params(params):
    if not params:
        return {'filter': {}, 'order': '-created_at'}
    ds = 'default_storage__'
    dis = 'discount'
    valid_orders = {'cheap': f'{ds}{dis}_price', 'expensive': f'-{ds}{dis}_price',
                    'best_seller': f'{ds}sold_count', 'popular': '-created_at',
                    'discount': f'{ds}{dis}discount_percent'}
    filter_by = {}
    orderby = params.get('o', '-created_at')
    category = params.get('cat', None)
    available = params.get('available', None)
    brand = params.getlist('brand', None)
    min_price = params.get('min_price', None)
    max_price = params.get('max_price', None)
    if category:
        filter_by['category__permalink'] = category
    if orderby != '-created_at':
        valid_key = valid_orders[orderby]
        orderby = valid_key
    if available:
        filter_by[f'{ds}available_count_for_sale__gt'] = 0
    if min_price and max_price:
        filter_by[f'{ds}{dis}_price__range'] = (min_price, max_price)
    if brand:
        if len(brand) == 1:
            filter_by['brand'] = brand[0]
        else:
            filter_by['brand__in'] = brand

    # keys = params.keys()
    # for key in keys:
    #     if len(key) < 3:
    #         continue
    #     if key == 'orderby':
    #         valid_key = valid_orders[f'{params[key]}']
    #         orderby = valid_key
    #         continue
    #     value = params.getlist(key)
    #     if len(value) == 1:
    #         valid_key = difflib.get_close_matches(key, valid_filters)[0]
    #         filter_by[valid_key] = value[0]
    #         continue
    #     filter_by[key + '__in'] = value

    return {'filter': filter_by, 'order': orderby}


def load_location(location):
    if location is not None:
        return {"lat": location[0], "lng": location[1]}
    return None


# No Usage

def to_json(obj=None, string=None):
    if obj is not list:
        obj = [obj]
    if obj:
        string = serializers.serialize("json", obj)
    return json.loads(string[1:-1])['fields']


def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(timestamp)


def move(obj, folder):
    old_path = obj.file.path
    new_path = MEDIA_ROOT + f'\\{folder}\\' + obj.file.name
    try:
        os.rename(old_path, new_path)
    except FileNotFoundError:
        os.makedirs(MEDIA_ROOT + f'\\{folder}\\')
        os.rename(old_path, new_path)
    finally:
        obj.save()


def to_obj(body):
    dic = json.loads(body)
    obj = type('test', (object,), {})()
    obj.__dict__ = dic
    return obj


# Utils

def send_sms(code, to):
    # +985000125475
    data = {"op": 'pattern', "user": '09379118854', "pass": 'Mojirzg6654', 'fromNum': '+98100020400',
            'toNum': to, 'patternCode': "gs3vltcvoi", 'inputData': [{'code': code}]}
    # data = {"op": 'send', "uname": '09379118854', "pass": 'Mojirzg6654', 'from': '+98100020400',
    #         'to': to, 'message': f'کد: {code}\nمهرتخفیف'}

    return requests.post('http://ippanel.com/api/select', data=json.dumps(data))


def send_email(subject, to, mail='support@mehrtakhfif.com', message=None, html_message=None):
    if type(to) != list:
        to = [to]
    send_mail(subject, message, mail, to, fail_silently=False, html_message=html_message)


def get_categories(language, box_id=None, category=None):
    if category is None and box_id:
        category = Category.objects.filter(box_id=box_id)
    else:
        category = Category.objects.all()
    if len(category) == 0:
        return []
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


def get_pagination(query, step, page, serializer, language="fa"):
    try:
        count = query.count()
    except TypeError:
        count = len(query)
    try:
        items = serializer(language=language).dump(query[(page - 1) * step: step * page], many=True)
    except TypeError:
        items = serializer().dump(query[(page - 1) * step: step * page], many=True)
    return {'pagination': {'last_page': math.ceil(count / step), 'count': count},
            'data': items}


def user_data_with_pagination(model, serializer, request):
    query = model.objects.filter(user=request.user)
    return get_pagination(query, request.step, request.page, serializer)


def calculate_profit(products):
    # TypeError: default storage is list but have one member
    total_price = sum([product['product']['default_storage']['final_price'] * product['count'] for product in products])
    discount_price = sum(
        [product['product']['default_storage']['discount_price'] * product['count'] for product in products])
    # feature_price = sum([sum([feature['price'] for feature in product['feature']]) * product['count']
    #                      for product in products])
    discount_price = 0
    total_price = 0
    for product in products:
        discount_price += product['discount_price']
        total_price += product['final_price']
        # try:
        #     feature_storage = FeatureStorage.objects.get(storage_id=storage_id, feature_id=feature['id'])
        #     prices = sum([item['price'] for item in feature_storage.value if item['fvid'] in feature['fvid']])
        #     print(prices)
        # except KeyError:
        #     continue

    profit = total_price - discount_price
    return {'total_price': total_price, 'discount_price': discount_price, 'profit': profit, 'shopping_cost': 0}


def get_basket(user, lang, basket_id=None):
    basket = None
    if basket_id:
        basket = Basket.objects.get(pk=basket_id)
    if not basket:
        basket = basket or Basket.objects.filter(user=user).order_by('-id').first()
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
        for product in basket_dict['products']:
            price = 0
            for feature in product['features']:
                for value in feature['value']:
                    price += value['price']
            product['item_final_price'] = product['product']['default_storage']['final_price'] + price
            product['item_discount_price'] = product['product']['default_storage']['discount_price'] + price
            product['final_price'] = product['count'] * product['item_final_price']
            product['discount_price'] = product['count'] * product['item_discount_price']
        profit = calculate_profit(basket_dict['products'])
    else:
        basket_dict = {}
    return {'basket': basket_dict, 'summary': profit, 'address_required': address_required}


def sync_default_storage(storages, products):
    for storage, product in zip(storages, products):
        if product.default_storage == storage:
            continue
        if storage.product == product:
            product.default_storage = storage


def get_best_seller(box, invoice_ids, step, page):
    # from invoices
    basket_products = InvoiceStorage.objects.filter(invoice_id__in=invoice_ids, box=box).values('storage', 'count')
    storage_count = {}
    for product in basket_products:
        if product['storage'] in storage_count.keys():
            storage_count[product['storage']] += product['count']
            continue
        storage_count[product['storage']] = product['count']
    storage_count = {k: v for k, v in sorted(storage_count.items(), key=lambda item: item[1])}
    storage_ids = storage_count.keys()
    storages = Storage.objects.filter(pk__in=storage_ids)
    products = Product.objects.filter(storage__in=storages)
    sync_default_storage(storages, products)
    return get_pagination(products, step, page, MinProductSchema)


def sync_storage(basket_id, op):
    basket_products = BasketProduct.objects.filter(basket_id=basket_id)
    for basket_product in basket_products:
        storage = basket_product.storage
        count = basket_product.count
        storage.available_count = op(F('available_count'), count)
        storage.available_count_for_sale = op(F('available_count_for_sale'), count)
        storage.sold_count = op(F('sold_count'), count)
        storage.save()


def add_one_off_job(name, args=None, kwargs=None, task='server.tasks.hello', interval=30,
                    period=IntervalSchedule.MINUTES):
    schedule, created = IntervalSchedule.objects.get_or_create(every=interval, period=period)
    task, created = PeriodicTask.objects.get_or_create(interval=schedule, name=name, task=task, one_off=True,
                                                       args=json.dumps(args), kwargs=json.dumps(kwargs))
    return task


# Security

def get_access_token(user, model=None, pk=None, try_again=None):
    pk = 0 if pk is None else pk
    time = add_minutes(0).strftime("%Y-%m-%d-%H") if try_again is None else add_minutes(-60).strftime("%Y-%m-%d-%H")
    data = f'{user.pk}{pk}{time}'
    data = model.__name__.lower() + data if model else data
    token = hashlib.sha3_224(data.encode()).hexdigest()
    return token


def check_access_token(token, user, model=None, pk=None):
    if token == get_access_token(user, model, pk):
        return True
    if token == get_access_token(user, model, pk, try_again=1):
        return True
    return False


def set_token(user, response):
    user.token = get_access_token(user)
    user.save()
    response.set_signed_cookie('token', user.token, TOKEN_SALT, max_age=7200, expires=7200)
    return response


def get_token_from_cookie(request):
    return request.get_signed_cookie('token', False, salt=TOKEN_SALT)


def set_csrf_cookie(response):
    random_text = uuid.uuid4().hex
    token = hashlib.sha3_224(random_text.encode()).hexdigest()
    response.set_signed_cookie('csrf_cookie', token, max_age=15778800, expires=15778800, domain="mt.com")  # 6 month
    return response


def check_csrf_token(request):
    csrf_cookie = request.get_signed_cookie('csrf_cookie', False)

    def double_check_token(minute):
        time = add_minutes(minute).strftime("%Y-%m-%d-%H-%M")
        try:
            token = hashlib.sha3_224((csrf_cookie + time + CSRF_SALT).encode()).hexdigest()
        except TypeError:
            raise AuthError
        print(request.headers)
        if token == request.headers['X-Csrf-Token']:
            return True

    if double_check_token(0) or double_check_token(-1):
        return True
    raise AuthError


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


def products_availability_check(products, step, page):
    count = 0
    available_products = []
    for product in products:
        storages = Storage.objects.filter(available_count_for_sale__gt=0, product=product).exists()
        if storages:
            count += 1
            available_products.append(product)
            if count == step:
                break
            continue
    return available_products


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
