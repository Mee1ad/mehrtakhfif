import hashlib
import string
import uuid
from datetime import datetime
from hashlib import sha3_512
from math import ceil
from operator import add, sub

import jdatetime
import magic
import xlsxwriter
from MyQR import myqr
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.core import serializers
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.db.models import Sum
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.views import View
from django_celery_beat.models import IntervalSchedule
from kavenegar import *

from mehr_takhfif.settings import CSRF_SALT, TOKEN_SALT, DEFAULT_COOKIE_DOMAIN, DEBUG, SMS_KEY, SHORTLINK
from server.documents import ProductDocument, TagDocument
from server.models import *
from server.serialize import get_tax, BasketSchema, MinProductSchema, BasketProductSchema, \
    UserSchema, InvoiceSchema, CategorySchema
# from barcode import generate
# from barcode.base import Barcode
from server.views.post import get_shipping_cost_temp
from django.db import transaction
from django.core.paginator import EmptyPage

random_data = string.ascii_lowercase + string.ascii_uppercase + string.digits
default_step = 18
admin_default_step = 10
default_page = 1

category_with_own_post = [2, 7, 10]  # golkade, adavat_moosighi, super market
res_code = {'success': 200, 'bad_request': 400, 'unauthorized': 401, 'forbidden': 403, 'token_issue': 401,
            'integrity': 406, 'banned': 493, 'activation_warning': 250, 'updated_and_disable': 251,
            'object_does_not_exist': 444, 'signup_with_pp': 203, 'invalid_password': 450,
            'signup_with_pass': 201, 'updated': 202, 'maintenance_mode': 501}  # todo 251 to 203
pattern = {'phone': r'^(09[0-9]{9})$', 'email': r'^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\
           [[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$',
           'postal_code': r'^\d{5}[ -]?\d{5}$', 'fullname': r'^[آ-یA-z]{2,}( [آ-یA-z]{2,})+([آ-یA-z]|[ ]?)$',
           'address': r'(([^ -_]+)[\n -]+){2}.+', 'location': r'\.*', 'bool': r'^(true|false)$',
           'name': r'^[ آ-یA-z]+$', 'first_name': r'^[ آ-یA-z]+$', 'last_name': r'^[ آ-یA-z]+$', 'language': r'^\w{2}$'}


# Data
def validation(data):
    fields = {'address': 'آدرس', 'phone': 'شماره', 'email': 'ایمیل', 'postal_code': 'کد پستی', 'fullname': 'نام',
              'location': 'لوکیشن', 'name': 'نام', 'first_name': 'نام', 'last_name': 'نام خانوادگی', }
    for key in data:
        if key == 'basket':
            assert len(key) < 20
        try:
            if not re.search(pattern[key], str(data[key])):
                if data[key] != "":
                    raise AssertionError
        except AssertionError:
            try:
                raise ValidationError(_(f'{fields[key]} نامعتبر است'))
            except KeyError:
                raise ValidationError(_(f'{key} نامعتبر است'))
        except KeyError:
            pass


def load_data(request, check_token=True):
    data = json.loads(request.body)
    validation(data)
    return data


def add_minutes(minutes, time=None):
    return (time or timezone.now()) + timezone.timedelta(minutes=minutes)


def to_jalali(dt):
    iran_time = add_minutes(210, dt)
    return jdatetime.datetime.fromgregorian(datetime=iran_time)


def add_days(days):
    return timezone.now() + timezone.timedelta(days=days)


def get_mimetype(image):
    mime = magic.Magic(mime=True)
    mimetype = mime.from_buffer(image.read(1024))
    image.seek(0)
    return mimetype


def upload(request, titles, media_type, category=None):
    image_formats = ['.jpeg', '.jpg', '.gif', '.png']
    # audio_formats = ['.jpeg', '.jpg', '.gif', '.png']
    media_list = []
    for file, title in zip(request.FILES.getlist('file'), titles):
        if file is not None:
            file_format = os.path.splitext(file.name)[-1]
            print(type(file))
            mimetype = get_mimetype(file).split('/')[0]
            if (mimetype == 'image' and file_format not in image_formats) or \
                    (mimetype != 'image'):
                return False
            # if media_type == 'avatar' and type(title) == dict:
            #     file.name = f"{title['user_id']} {timezone.now().strftime('%Y-%m-%d, %H-%M-%S')}{file_format}"
            media = Media(image=file, category_id=category, created_by_id=1, type=media_type,
                          title=title, updated_by=request.user)
            media.save()
            media_list.append(media)
    return media_list



def get_request_params(get_parameters):
    param_dict = dict(get_parameters)
    for key, value in param_dict.copy().items():
        if type(value) is list and len(value) < 2:
            param_dict[key] = value[0]
            continue
        param_dict[key.replace('[]', '')] = param_dict.pop(key)
    return param_dict


# def get_rank(q, lang="fa", field='name'):
#     sv = SearchVector(KeyTextTransform(lang, field), weight='A')  # + \
#     # SearchVector(KeyTextTransform('fa', 'product__category__name'), weight='B')
#     sq = SearchQuery(q)
#     rank = SearchRank(sv, sq, weights=[0.2, 0.4, 0.6, 0.8])
#     return rank


def load_location(location):
    if location is not None:
        return {"lat": location[0], "lng": location[1]}
    return None


def get_invoice_file(request, invoice=None, invoice_id=None, user={}):
    if invoice is None:
        invoice = Invoice.objects.get(pk=invoice_id, **user)
    # shipping_invoice = Invoice.objects.filter(basket=invoice.basket, final_price__isnull=True, **user).order_by('-id')
    invoice_dict = InvoiceSchema(**request.schema_params).dump(invoice)
    if invoice.post_invoice:
        invoice_dict['shipping_invoice'] = InvoiceSchema().dump(invoice.post_invoice)
        invoice_dict['shipping_invoice']['tax'] = get_tax(2, invoice_dict['shipping_invoice']['amount'], 0)
    invoice_dict['user'] = UserSchema().dump(invoice.user)
    try:
        # invoice_dict['date'] = jdatetime.datetime.fromgregorian(datetime=add_minutes(invoice.payed_at)) \
        #     .strftime("%Y/%m/%d")
        invoice_dict['date'] = to_jalali(invoice.payed_at).strftime("%Y/%m/%d")
    except ValueError:
        invoice_dict['date'] = '1399/99/99'
    invoice_dict['barcode'] = get_barcode(invoice.id)
    return invoice_dict


def safe_get(*args):
    """
    :param args: obj, attr1, attr2, attr3, ...
    :return: obj.attr1.attr2.attr3
    """
    try:
        o = args[0]
        for arg in args[1:]:
            o = getattr(o, arg)
        return o
    except Exception:
        pass


def get_share(storage=None, invoice=None):
    """
    :param storage:
    :param invoice:
    :return:
    """
    no_profit_categories = [385]
    share = {'tax': 0, 'charity': 0, 'dev': 0, 'admin': 0, 'mt_profit': 0}
    invoice_storages = [storage]
    if invoice:
        share = InvoiceStorage.objects.filter(invoice=invoice).aggregate(tax=Sum('tax'), charity=Sum('charity'),
                                                                         dev=Sum('dev'), admin=Sum('admin'),
                                                                         mt_profit=Sum('mt_profit'))
        return share
    for invoice_storage in invoice_storages:
        count = invoice_storage.count
        storage = invoice_storage.storage
        category = storage.product.category
        share = {'tax': 0, 'charity': 0, 'dev': 0, 'admin': 0, 'mt_profit': 0}
        if category.pk not in no_profit_categories:
            tax = get_tax(storage.tax_type, storage.discount_price, storage.start_price)
            charity = ceil(storage.discount_price * 0.005)
            dev = ceil((storage.discount_price - storage.start_price - tax) * 0.069)
            admin = ceil(
                (storage.discount_price - storage.start_price - tax - charity - dev) * category.settings['share'])
            mt_profit = storage.discount_price - storage.start_price - tax - charity - dev - admin
            share = {'tax': share['tax'] + tax, 'charity': share['charity'] + charity, 'dev': share['dev'] + dev,
                     'admin': share['admin'] + admin, 'mt_profit': share['mt_profit'] + mt_profit}
            share = {k: v * count for k, v in share.items()}
    return share


# No Usage

def obj_to_json(obj=None):
    if obj is not list:
        obj = [obj]
    if obj:
        serialized = serializers.serialize("json", obj)
    return json.loads(serialized[1:-1])['fields']


def move_file(obj, folder):
    old_path = obj.file.path
    new_path = MEDIA_ROOT + f'\\{folder}\\' + obj.file.name
    try:
        os.rename(old_path, new_path)
    except FileNotFoundError:
        os.makedirs(MEDIA_ROOT + f'\\{folder}\\')
        os.rename(old_path, new_path)
    finally:
        obj.save()


def dict_to_obj(dic):
    if type(dic) is not dict:
        dic = json.loads(dic)
    obj = type('test', (object,), {})()
    obj.__dict__ = dic
    return obj


def create_qr(data, output):
    version, level, qr_name = myqr.run(data, version=2, level='L', picture="F:\Download\Photos\mt\mehrtakhfifIcon.png",
                                       colorized=True, contrast=1.0, brightness=1.0, save_name=f'{output}.png',
                                       save_dir=MEDIA_ROOT + f'/qr/')


def get_barcode(data=None):
    return None
    # todo fix this later
    # Barcode.default_writer_options['write_text'] = False
    # barcode_directory = f'{MEDIA_ROOT}/barcode'
    # generate('code39', f'{data}', output=f'{barcode_directory}/{data}')
    # generate('code39', f'1234567891', output=f'{barcode_directory}/{data}')
    # return HOST + f'/media/barcode/{data}.svg'


# Utils

def send_sms(to, template, token, token2=None, token3=None, token10=None, token20=None):
    """
    :param to:
    :param template: digital-order-details, order-summary, user-order, verify
    :param token:
    :param token2:
    :param token3:
    :param token10:
    :param token20:
    :return:
    """
    try:
        api = KavenegarAPI(SMS_KEY)
        params = {
            'receptor': to,  # multiple mobile number, split by comma
            'template': template,
            'token': token,
            'token2': token2,
            'token3': token3,
            'token10': token10,
            'token20': token20,
            'type': 'sms',  # sms vs call
        }
        api.verify_lookup(params)
    except APIException as e:
        print(e)
    except HTTPException as e:
        print(e)


def send_pm(tg_id, message):  # 312145983  -550039210
    url = "https://mtmessenger.herokuapp.com/send_message"
    data = {"tg_id": tg_id, "message": message}
    r = requests.post(url, json=data)
    retry = 0
    while r.status_code != 200 and retry < 3:
        r = requests.post(url, json=data)
        retry += 1
    return r


def send_email(subject, to, from_email='notification@mehrtakhfif.com', message=None, html_content=None, attach=None):
    """
    :param subject:
    :param to:
    :param from_email:
    :param message:
    :param html_content:
    :param attach:
    :return:
    """
    return True
    if type(to) != list:
        to = [to]
    msg = EmailMultiAlternatives(subject, message, from_email, to)
    if html_content:
        msg.attach_alternative(html_content, "text/html")
        msg.content_subtype = "html"
        [msg.attach_file(a) for a in attach]
    msg.send()
    return msg


# info category by moji
# todo check for possible duplicates in category


def get_categories(filters=None):
    if filters is None:
        filters = {}
    prefetch_grand_children = Prefetch('children', to_attr='prefetched_children',
                                       queryset=Category.objects.filter(disable=False))
    prefetch_children = Prefetch('children', to_attr='prefetched_children',
                                 queryset=Category.objects.filter(disable=False)
                                 .prefetch_related(prefetch_grand_children))
    categories = Category.objects.filter(**filters, disable=False).prefetch_related(prefetch_children)
    categories = CategorySchema(only=['id', 'name', 'children', 'permalink', 'type', 'priority']).dump(categories,
                                                                                                       many=True)
    return categories


def get_pagination(request, query, serializer, select=(), prefetch=(), show_all=False, serializer_args={}):
    page = request.page
    step = request.step
    paginator = Paginator(query, step)
    count = len(query)
    # query = query if show_all and count <= 500 else query[(page - 1) * step: step * page]
    try:
        query = paginator.page(page)
    except EmptyPage:
        return {'pagination': {'last_page': ceil(count / step), 'count': count, 'step': step},
                'data': []}
    if show_all and count > 0:
        step = count
    if step > 100:
        step = default_step
    try:
        items = serializer(**request.schema_params, **serializer_args).dump(query, many=True)
    except TypeError:
        items = serializer(**serializer_args).dump(query, many=True)
    return {'pagination': {'last_page': ceil(count / step), 'count': count, 'step': step},
            'data': items}


def user_data_with_pagination(model, serializer, request, show_all=False, extra={}, serializer_args={}):
    query = model.objects.filter(user=request.user, **extra).order_by('-id')
    return get_pagination(request, query, serializer, show_all=show_all, serializer_args=serializer_args)


def get_discount_price(storage):
    try:
        prices = storage.vip_prices.all()
        prices = [price.discount_price for price in prices] + [storage.discount_price]
        return min(prices)
    except Exception:
        return storage.discount_price


def get_discount_percent(storage):
    try:
        prices = storage.vip_prices.all()
        prices = [price.discount_percent for price in prices] + [storage.discount_percent]
        return min(prices)
    except Exception:
        return storage.discount_percent


def check_basket(request, basket):
    if isinstance(basket, Basket):
        basket_products = basket.basket_storages.all().select_related('storage')
    else:
        basket = request.session.get('basket', [])
        # todo optimize cant select related storage
        basket_products = [BasketProduct(**basket_product, id=index) for index, basket_product in enumerate(basket)]
    # todo test
    deleted_items = []
    changed_items = []
    removed_count = 0
    for basket_product in basket_products:
        if basket_product.storage.available_count_for_sale == 0:
            deleted_items.append(BasketProductSchema().dump(basket_product))
            removed_count += basket_product.count + (basket_product.accessory_id or 0 * basket_product.count)
            basket_product.delete()
        elif basket_product.count > basket_product.storage.available_count_for_sale:
            changed_items.append({'product_name': basket_product.storage.title['fa'], 'old_count': basket_product.count,
                                  'new_count': basket_product.storage.available_count_for_sale})
            removed_count += basket_product.count - basket_product.storage.available_count_for_sale
            basket_product.count = basket_product.storage.available_count_for_sale
            basket_product.save()
    try:
        basket.count -= removed_count
        basket.save()
    except Exception as e:
        pass
    return {'deleted': deleted_items, 'changed': changed_items}


def get_basket(request, basket_id=None, basket=None, basket_products=None, return_obj=False, tax=False,
               require_profit=False, use_session=False, with_changes=False):
    user = request.user
    lang = request.lang
    if (not user.is_authenticated or (DEBUG is True and (request.GET.get('use_session') == 'True' or use_session))) and \
            request.session.get('basket'):
        basket = request.session.get('basket', [])
        basket_products = [BasketProduct(**basket_product, id=index) for index, basket_product in enumerate(basket)]
        # basket = Basket(created_by=user, updated_by=user, basket_products=basket_products)
        basket = type('Basket', (), {'basket_products': basket_products})()
    if user.is_authenticated:
        if basket_id:
            basket = Basket.objects.filter(pk=basket_id).select_related('discount_code') \
                .prefetch_related('basket_storages__storage__features', 'basket_storages__storage__product__category',
                                  'basket_storages__storage__product__thumbnail',
                                  'basket_storages__storage__vip_prices') \
                .first()
        if not basket_id and not basket:
            basket = user.baskets.all() \
                .prefetch_related('basket_storages__storage__features', 'basket_storages__storage__product__category',
                                  'basket_storages__storage__product__thumbnail',
                                  'basket_storages__storage__vip_prices') \
                .order_by('-id').first()
    if basket is None:
        return {'basket': {}, 'summary': {}, 'address_required': False}
    changed_items = {}
    if with_changes:
        changed_items = check_basket(request, basket)
    basket_products = basket_products or basket.basket_storages.all().order_by('-id')
    summary = {"total_price": 0, "discount_price": 0, "profit": 0, "mt_profit": 0, 'charity': 0,
               "shipping_cost": 0, "tax": 0, "final_price": 0}
    address_required = False
    summary['max_shipping_time'] = 0
    for basket_product in basket_products:
        storage = basket_product.storage
        if basket_product.accessory:
            basket_product.item_discount_price = basket_product.accessory.discount_price
            basket_product.discount_price = basket_product.accessory.discount_price
            storage.discount_price = basket_product.accessory.discount_price
        if summary['max_shipping_time'] < basket_product.storage.max_shipping_time:
            summary['max_shipping_time'] = basket_product.storage.max_shipping_time
        basket_product.product = storage.product
        basket_product.product.default_storage = storage
        # basket_product.supplier = storage.supplier
        if basket_product.product.type in [2, 4] and not address_required:
            address_required = True
        storage.discount_price = get_discount_price(storage)
        basket_product.__dict__.update(
            {'item_final_price': storage.final_price, 'discount_percent': get_discount_percent(storage),
             'item_discount_price': get_discount_price(storage), 'start_price': storage.start_price})
        # for feature in basket_product.features:
        #     feature_storage = FeatureStorage.objects.get(id=feature['fsid'], storage_id=storage.pk)
        #     for value in feature['fvid']:
        #         feature_price = next(
        #             storage['price'] for storage in feature_storage.value if storage['fvid'] == value)
        #         basket_product.item_final_price += feature_price
        #         basket_product.item_discount_price += feature_price
        #         basket_product.start_price += feature_price
        if tax:
            basket_product.amer = storage.product.category.name['fa']
            # storage = basket_product.storage
            # basket_product.tax = get_tax(storage.tax_type, storage.discount_price, storage.start_price)
            # summary['tax'] += basket_product.tax
        count = basket_product.count

        basket_product.final_price = basket_product.item_final_price * count
        summary['total_price'] += basket_product.final_price
        # basket_product.discount_price = (basket_product.item_discount_price - basket_product.tax) * count
        basket_product.discount_price = basket_product.item_discount_price * count
        summary['discount_price'] += basket_product.discount_price
        summary['profit'] += basket_product.final_price - basket_product.discount_price
        basket_product.start_price = basket_product.start_price * count
        # basket_product.tax = 0
        # basket_product.amer = ""
        tax = get_tax(storage.tax_type, storage.discount_price, storage.start_price)
        # charity = (basket_product.discount_price - basket_product.start_price - tax) * 0.05
        charity = round(basket_product.discount_price * 0.005)
        summary['charity'] += charity
        summary['mt_profit'] += (basket_product.discount_price - basket_product.start_price) - charity
    try:
        basket.basket_products = basket_products
    except AttributeError:
        pass
    shipping_cost = 0
    if address_required:
        # summary['shipping_cost'] = get_shipping_cost(user, basket)
        summary['shipping_cost'] = get_shipping_cost_temp(user, basket)
        if summary['shipping_cost'] != -1:
            shipping_cost = summary['shipping_cost']

    if return_obj:
        basket.summary = summary
        basket.address_required = address_required
        return basket
    if require_profit is False:
        summary.pop('mt_profit', None)
        summary.pop('charity', None)
    basket = BasketSchema(language=lang, nested_accessories=True).dump(basket)
    summary['invoice_discount'] = summary['total_price'] - summary['discount_price']
    summary['total_price'] += shipping_cost
    summary['discount_price'] += shipping_cost
    return {'basket': basket, 'summary': summary, 'address_required': address_required, **changed_items}


def get_basket_count(user=None, basket_id=None, session=None):
    if session:
        return sum([product['count'] for product in session.get('basket', [])])
    if basket_id:
        return BasketProduct.objects.filter(basket_id=basket_id).aggregate(count=Sum('count'))['count'] or 0
    return user.baskets.order_by('id').prefetch_related('basket_products').last().basket_storages \
               .aggregate(count=Sum('count'))['count'] or 0


def sync_session_basket(request):
    user = request.user
    basket_count = 0
    if request.session.get('basket', None):
        try:
            basket = Basket.objects.filter(user=user).order_by('-id').first()
            if basket is None:
                basket = Basket.objects.create(user=user, created_by=user, updated_by=user)
        except TypeError:
            basket = Basket.objects.create(user=user, created_by=user, updated_by=user)
        session_basket = request.session['basket']
        for product in session_basket[::-1]:
            is_updated = BasketProduct.objects.filter(basket=basket, storage_id=product['storage_id']).update(
                count=product['count'])
            if not is_updated:
                BasketProduct.objects.create(basket=basket, **product)
        request.session['basket'] = []
        request.session.save()
        basket_count = get_basket_count(basket_id=basket.id)
        basket.count = basket_count
        basket.save()
    return basket_count


def sync_default_storage(storages, products):
    for storage, product in zip(storages, products):
        if product.default_storage == storage:
            continue
        if storage.product == product:
            product.default_storage = storage


def get_best_seller(request, category, invoice_ids):
    # from invoices
    basket_products = InvoiceStorage.objects.filter(invoice_id__in=invoice_ids, category=category).values('storage',
                                                                                                          'count')
    storage_count = {}
    for product in basket_products:
        if product['storage'] in storage_count.keys():
            storage_count[product['storage']] += product['count']
            continue
        storage_count[product['storage']] = product['count']
    storage_count = {k: v for k, v in sorted(storage_count.items(), key=lambda item: item[1])}
    storage_ids = storage_count.keys()
    storages = Storage.objects.filter(pk__in=storage_ids)
    products = Product.objects.filter(default_storage__in=storages)
    sync_default_storage(storages, products)
    return get_pagination(request, products, MinProductSchema)


def sync_storage(invoice, op):
    def update_storage_counts(s, c):  # Storage, Count
        s.available_count = op(s.available_count, c)
        s.available_count_for_sale = op(s.available_count_for_sale, c)
        if op == sub:
            s.sold_count = add(s.sold_count, c)
        if op == add:
            s.sold_count = sub(s.sold_count, c)

    attr = {'Basket': 'basket_storages', 'Invoice': 'invoice_storages'}[invoice.__class__.__name__]

    with transaction.atomic():
        products = getattr(invoice, attr).all()
        for product in products:
            if product.storage.product.get_type_display() == 'package':
                package_items = Package.objects.filter(package=product.storage)
                for package_item in package_items:
                    storage = package_item.package_item
                    count = package_item.count
                    update_storage_counts(storage, count)
                    storage.save()
            count = product.count
            storage = product.storage
            update_storage_counts(storage, count)
            storage.save()


def add_one_off_job(name, args=None, kwargs=None, task='server.tasks.hello', interval=30,
                    period=IntervalSchedule.MINUTES):
    schedule, created = IntervalSchedule.objects.get_or_create(every=interval, period=period)
    task, created = PeriodicTask.objects.get_or_create(interval=schedule, name=name, task=task, one_off=True,
                                                       args=json.dumps(args), kwargs=json.dumps(kwargs))
    return task


def get_vip_price(user, storage):
    user_vip_groups = user.vip_types.all()
    vip_prices = storage.vip_prices.all()


def remove_null_from_dict(required_keys, dictionary):
    for key in required_keys:
        if not dictionary[key]:
            dictionary.pop(key, None)
    return dictionary


def get_preview_permission(user, category_check=True, box_check=True, category_key='category', product_check=False,
                           is_get=True):
    permitted_users = []  # user_id, can order for disabled product
    if is_get:
        permitted_users = [user.pk]
    if user.is_staff and user.pk in permitted_users:
        return {}
    preview = {'disable': False}
    product = ""
    if product_check:
        product = "product__"
        preview[f'product__disable'] = False
    if category_check:
        preview[f'{product}categories__disable'] = False
    if box_check:
        preview[f'{product}{category_key}__disable'] = False
    return preview


def add_to_basket(basket, products):
    for product in products:
        count = int(product['count'])
        storage_id = product['storage_id']
        storage = Storage.objects.get(pk=storage_id)
        accessories = product.get("accessories", [])
        accessories_ids = [accessory['id'] for accessory in accessories]
        storage_accessories = StorageAccessories.objects.filter(id__in=accessories_ids)
        accessory_id = product.get("accessory_id", None)
        for accessory in accessories:
            accessory_storage = next(sa.accessory_storage for sa in storage_accessories if sa.id == accessory['id'])
            accessory['storage_id'] = accessory_storage.id
            accessory['accessory_id'] = accessory['id']
            # accessory['parent_id'] = storage
        products += accessories
        if storage.is_available(count) is False:
            raise ValidationError(_('متاسفانه این محصول ناموجود میباشد'))
        try:
            basket_product = BasketProduct.objects.filter(basket=basket, storage=storage, accessory_id=accessory_id)
            assert basket_product.exists()
            basket_product.update(count=count)
        except AssertionError:
            category = storage.product.category
            # features = storage.features.all()
            # features = ProductFeatureSchema().dump(features, many=True)
            # accessory =
            BasketProduct.objects.create(basket=basket, storage=storage, count=count, category=category,
                                         accessory_id=accessory_id)

    basket.count = basket.basket_storages.aggregate(count=Sum('count'))['count']
    basket.save()
    basket.discount_codes.update(basket=None)
    return basket.count


def make_short_link(link):
    url = None
    while not url:
        try:
            shortlink = f"l{get_random_string(4)}"
            url, created = URL.objects.get_or_create(url=link, shortlink=shortlink)
        except IntegrityError:
            pass
    return f"{SHORTLINK}/{url.shortlink}"


# todo incomplete
def supplier_sale_report(supplier):
    book = xlsxwriter.Workbook(f'book.xlsx')
    sheet = book.add_worksheet()
    sheet.write(f'A1', "name")
    sheet.write(f'B1', "date")
    sheet.write(f'C1', "description")
    sheet.write(f'D1', "price")
    invoice_storages = InvoiceStorage.objects.filter(invoice__payed_at__isnull=False, storage__supplier=supplier)
    for index, invoice_storage in enumerate(invoice_storages):
        sheet.write(f'A{index + 2}', invoice_storage.storage.title['fa'])
        sheet.write(f'B{index + 2}', invoice_storage.invoice.payed_at.strftime("%Y-%m-%d"))
        sheet.write(f'C{index + 2}', "بلا بلا بلا")
        sheet.write(f'D{index + 2}', invoice_storage.discount_price)
    book.close()


# Security
def get_access_token(user, model=None, pk=None, try_again=None, data=''):
    pk = 0 if pk is None else pk
    time = add_minutes(0).strftime("%Y-%m-%d-%H") if try_again is None else add_minutes(-60).strftime("%Y-%m-%d-%H")
    data = f'{data}{user.pk}{pk}{time}{TOKEN_SALT}'
    data = model.__name__.lower() + data if model else data
    token = hashlib.sha3_512(data.encode()).hexdigest()
    return token


def check_access_token(new_token, user, model=None, pk=None, data=''):
    token = get_access_token(user, model, pk, data=data)
    if new_token == token:
        return True
    token = get_access_token(user, model, pk, try_again=1, data=data)
    if new_token == token:
        return True
    return False


def set_token(user, response):
    user.token = get_access_token(user)
    user.save()
    response = set_custom_signed_cookie(response, 'token', user.token, max_age=7200, expires=7200)
    return response


def get_token_from_cookie(request):
    return get_custom_signed_cookie(request, 'token', False)


def set_csrf_cookie(response):
    random_text = uuid.uuid4().hex
    token = hashlib.sha3_224(random_text.encode()).hexdigest()
    response = set_custom_signed_cookie(response, 'csrf_cookie', token, max_age=15778800, expires=15778800, )
    return response


def check_csrf_token(request):
    csrf_cookie = get_custom_signed_cookie(request, 'csrf_cookie', False)

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


def set_custom_signed_cookie(res, key, value, salt=TOKEN_SALT, domain=DEFAULT_COOKIE_DOMAIN, max_age=2678400, **kwargs):
    res.set_signed_cookie(key, value, salt=salt, domain=domain, max_age=max_age, **kwargs)
    return res


def delete_custom_signed_cookie(res, key, domain=DEFAULT_COOKIE_DOMAIN):
    res.delete_cookie(key, domain=domain)
    return res


def get_custom_signed_cookie(req, key, error=None, salt=TOKEN_SALT):
    if error is not None:
        return req.get_signed_cookie(key, error, salt=salt)
    return req.get_signed_cookie(key, default=None, salt=salt)


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
