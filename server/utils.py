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
from django.core.mail import EmailMultiAlternatives
from django.views import View
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from datetime import datetime
import pysnooper
from operator import add, sub
from secrets import token_hex
from mehr_takhfif.settings import CSRF_SALT, TOKEN_SALT, DEFAULT_COOKIE_DOMAIN
from server.models import *
import requests
from server.serialize import MediaSchema
from server.serialize import BoxCategoriesSchema, BasketSchema, BasketProductSchema, MinProductSchema
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
import string
from django.core.exceptions import PermissionDenied
from MyQR import myqr
from mehr_takhfif.settings import BASE_DIR

random_data = string.ascii_lowercase + string.digits
default_step = 10
default_page = 1
default_response = {'ok': {'message': 'ok'}, 'bad': {'message': 'bad request'}}
res_code = {'success': 200, 'bad_request': 400, 'unauthorized': 401, 'forbidden': 403, 'token_issue': 401,
            'integrity': 406, 'banned': 493,
            'signup_with_pp': 251, 'invalid_password': 450, 'signup_with_pass': 201, 'activate': 202}
pattern = {'phone': r'^(09[0-9]{9})$', 'email': r'^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\
           [[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$',
           'postal_code': r'^\d{5}[ -]?\d{5}$', 'fullname': r'^[آ-یA-z]{2,}( [آ-یA-z]{2,})+([آ-یA-z]|[ ]?)$',
           'address': r'(([^ -_]+)[\n -]+){2}.+', 'location': r'\.*', 'bool': r'^(true|false)$',
           'name': r'^[ آ-یA-z]+$', 'first_name': r'^[ آ-یA-z]+$', 'last_name': r'^[ آ-یA-z]+$', 'language': r'^\w{2}$'}


# Data

def validation(data):
    for key in data:
        if key == 'basket':
            assert len(key) < 20
        try:
            assert re.search(pattern[key], str(data[key]))
        except AssertionError:
            raise ValidationError(f'invalid value for {key}')
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
    media_list = []
    for file, title in zip(request.FILES.getlist('file'), titles):
        if file is not None:
            file_format = os.path.splitext(file.name)[-1]
            mimetype = get_mimetype(file).split('/')[0]
            if (mimetype == 'image' and file_format not in image_formats) or \
                    (mimetype != 'image'):
                return False
            if media_type == 'avatar' and type(title) == dict:
                file.name = f"{title['user_id']} {timezone.now().strftime('%Y-%m-%d, %H-%M-%S')}{file_format}"
            media = Media(image=file, box_id=box, created_by_id=1, type=media_type,
                          title=title, updated_by=request.user)
            media.save()
            media_list.append(media)
    return media_list


def filter_params(params, lang):
    filters = {'filter': {'default_storage__isnull': False}, 'rank': {}, 'related': {}, 'query': '', 'order': '-created_at'}
    if not params:
        return filters
    ds = 'default_storage__'
    dis = 'discount'
    valid_orders = {'cheap': f'{ds}{dis}_price', 'expensive': f'-{ds}{dis}_price',
                    'best_seller': f'{ds}sold_count', 'popular': '-created_at',
                    'discount': f'{ds}{dis}discount_percent'}
    box_permalink = params.get('b', None)
    q = params.get('q', None)
    orderby = params.get('o', '-created_at')
    category = params.get('cat', None)
    available = params.get('available', None)
    brand = params.getlist('brand[]', None)
    min_price = params.get('min_price', None)
    max_price = params.get('max_price', None)
    if box_permalink:
        try:
            filters['related'] = {'category_id__in': Category.objects.filter(box__permalink=box_permalink,
                                                                             permalink=None).values_list('parent_id',
                                                                                                         flat=True)}
            filters['filter']['box'] = Box.objects.get(permalink=box_permalink)
        except Box.DoesNotExist:
            pass
    if category:
        filters['filter']['category__permalink'] = category
    if orderby != '-created_at':
        valid_key = valid_orders[orderby]
        filters['order'] = valid_key
    if q:
        filters['rank'] = {'rank': get_rank(q, lang)}
        filters['order'] = '-rank'
    if available:
        filters['filter'][f'{ds}available_count_for_sale__gt'] = 0
    if min_price and max_price:
        filters['filter'][f'{ds}{dis}_price__range'] = (min_price, max_price)
    if brand:
        filters['filter']['brand__in'] = brand

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

    return filters


def get_rank(q, lang):
    sv = SearchVector(KeyTextTransform(lang, 'name'), weight='A')  # + \
    # SearchVector(KeyTextTransform('fa', 'product__category__name'), weight='B')
    sq = SearchQuery(q)
    rank = SearchRank(sv, sq, weights=[0.2, 0.4, 0.6, 0.8])
    return rank


def load_location(location):
    if location is not None:
        return {"lat": location[0], "lng": location[1]}
    return None


def get_tax(tax_type, discount_price, start_price=None):
    return int({
                   1: 0,
                   2: discount_price * 0.09,
                   3: (discount_price - start_price) * 0.09
               }[tax_type])


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


def create_qr(data, output):
    version, level, qr_name = myqr.run(data, version=2, level='L', picture="F:\Download\Photos\mt\mehrtakhfifIcon.png",
                                       colorized=True, contrast=1.0, brightness=1.0, save_name=f'{output}.png',
                                       save_dir=MEDIA_ROOT + f'/qr/')


# Utils

def send_sms(to, pattern="gs3vltcvoi", content=None, input_data=None):
    # +985000125475
    if pattern:
        data = {"op": 'pattern', "user": '09379118854', "pass": 'Mojirzg6654', 'fromNum': '+98100020400',
                'toNum': to, 'patternCode': pattern, 'inputData': input_data}
    if content:
        data = {"op": 'send', "uname": '09379118854', "pass": 'Mojirzg6654', 'from': '+98100020400',
                'to': to, 'message': content}

    return requests.post('http://ippanel.com/api/select', data=json.dumps(data))


def send_email(subject, to, from_email='support@mehrtakhfif.com', message=None, html_content=None, attach=None):
    if type(to) != list:
        to = [to]
    msg = EmailMultiAlternatives(subject, message, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    if html_content:
        msg.content_subtype = "html"
        [msg.attach_file(a) for a in attach]
    msg.send()


def get_categories(language, box_id=None, categories=None, is_admin=None):
    if box_id:
        categories = Category.objects.filter(box_id=box_id)
    if categories is None:
        categories = Category.objects.all()
    if len(categories) == 0:
        return []
    new_cats = [*categories]
    remove_index = []
    for cat, index in zip(categories, range(len(categories))):
        cat.is_admin = is_admin
        if cat.parent is None:
            continue
        try:
            parent_index = new_cats.index(categories.filter(pk=cat.parent_id).first())
            if not hasattr(new_cats[parent_index], 'child'):
                new_cats[parent_index].child = []
            new_cats[parent_index].child.append(cat)
            remove_index.append(cat)
        except ValueError:  # for filterDetail when parent is not in result of query
            pass
    new_cats = [x for x in new_cats if x not in remove_index]
    return BoxCategoriesSchema(language=language).dump(new_cats, many=True)


def get_pagination(query, step, page, serializer, show_all=False, language="fa"):
    if step > 100:
        step = 10
    try:
        count = query.count()
    except TypeError:
        count = len(query)
    query = query if show_all and count <= 500 else query[(page - 1) * step: step * page]
    try:
        items = serializer(language=language).dump(query, many=True)
    except TypeError:
        items = serializer().dump(query, many=True)
    return {'pagination': {'last_page': math.ceil(count / step), 'count': count},
            'data': items}


def user_data_with_pagination(model, serializer, request):
    query = model.objects.filter(user=request.user)
    return get_pagination(query, request.step, request.page, serializer)


def get_basket(user, lang=None, basket_id=None, basket=None, basket_products=None, return_obj=False, tax=False):
    if basket_id:
        basket = Basket.objects.get(pk=basket_id)
    if not basket_id:
        basket = basket or Basket.objects.filter(user=user).order_by('-id').first()
    if basket is None:
        return {}
    basket_products = basket_products or \
                      BasketProduct.objects.filter(basket=basket).select_related(*BasketProduct.related)
    summary = {"total_price": 0, "discount_price": 0, "profit": 0, "shopping_cost": 0, "tax": 0}
    for basket_product in basket_products:
        storage = basket_product.storage
        basket_product.product = storage.product
        basket_product.product.default_storage = storage
        basket_product.supplier = storage.supplier
        address_required = False
        if basket_product.product.type == 2 and not address_required:
            address_required = True
        basket_product.__dict__.update(
            {'item_final_price': storage.final_price, 'discount_percent': storage.discount_percent,
             'item_discount_price': storage.discount_price, 'start_price': storage.start_price})
        for feature in basket_product.features:
            feature_storage = FeatureStorage.objects.get(feature_id=feature['fid'], storage_id=storage.pk)
            for value in feature['fvid']:
                feature_price = next(
                    storage['price'] for storage in feature_storage.value if storage['fvid'] == value)
                basket_product.item_final_price += feature_price
                basket_product.item_discount_price += feature_price
                basket_product.start_price += feature_price
        count = basket_product.count
        basket_product.final_price = basket_product.item_final_price * count
        summary['total_price'] += basket_product.final_price
        basket_product.discount_price = basket_product.item_discount_price * count
        summary['discount_price'] += basket_product.discount_price
        summary['profit'] += basket_product.final_price - basket_product.discount_price
        basket_product.start_price = basket_product.start_price * count
        basket_product.tax = 0
        basket_product.amer = ""
        if tax:
            basket_product.amer = storage.product.box.name['fa']
            basket_product.tax = get_tax(storage.tax_type, basket_product.discount_price, basket_product.start_price)
        basket.basket_products = basket_products
    if return_obj:
        basket.summary = summary
        basket.address_required = address_required
        return basket
    basket = BasketSchema(language=lang).dump(basket)
    return {'basket': basket, 'summary': summary, 'address_required': address_required}


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
        if op == sub:
            storage.sold_count = add(F('sold_count'), count)
        if op == add:
            storage.sold_count = sub(F('sold_count'), count)

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
    response = set_signed_cookie(response, 'token', user.token, max_age=7200, expires=7200)
    return response


def get_token_from_cookie(request):
    return get_signed_cookie(request, 'token', False)


def set_csrf_cookie(response):
    random_text = uuid.uuid4().hex
    token = hashlib.sha3_224(random_text.encode()).hexdigest()
    response = set_signed_cookie(response, 'csrf_cookie', token, max_age=15778800, expires=15778800, )
    return response


def check_csrf_token(request):
    csrf_cookie = get_signed_cookie(request, 'csrf_cookie', False)

    @pysnooper.snoop()
    def double_check_token(minute):
        time = add_minutes(minute).strftime("%Y-%m-%d-%H-%M")
        try:
            token = hashlib.sha3_224((csrf_cookie + time + CSRF_SALT).encode()).hexdigest()
            a = request.headers['X-Csrf-Token']
        except TypeError:
            raise PermissionDenied
        if token == request.headers['X-Csrf-Token']:
            return True

    if double_check_token(0) or double_check_token(-1):
        return True
    raise PermissionDenied


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


def set_signed_cookie(res, key, value, salt=TOKEN_SALT, domain=DEFAULT_COOKIE_DOMAIN, **kwargs):
    res.set_signed_cookie(key, value, salt=salt, domain=domain, **kwargs)
    return res


def get_signed_cookie(req, key, error=None, salt=TOKEN_SALT):
    if error is not None:
        return req.get_signed_cookie(key, error, salt=salt)
    return req.get_signed_cookie(key, salt=salt)


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
