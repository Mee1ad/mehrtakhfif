import difflib
import io
import json
import math
from datetime import datetime

import jwt
import magic
import pysnooper
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.http import FileResponse
from django.http import HttpResponse
from django.views import View
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from mehr_takhfif import settings
from mehr_takhfif.settings import TOKEN_SECRET, SECRET_KEY
from server.models import *
from server.serialize import *

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


def upload(request, title, box=1):
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
            media = Media(file=file, box_id=box, created_by_id=1, type=mimetype, title=title or file)
            media.save()

            return True


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
    filters = ('discount_price', 'discount_vip_price', 'discount_percent', 'discount_vip_percent',
               'product__sold_count', 'created_at')
    filters_op = ('__gt', '__gte', '__lt', '__lte')
    valid_filters = [x + y for y in filters_op for x in filters]
    filter_by = {}
    orderby = ['-created_at']
    try:
        orderby = params.getlist('orderby') + orderby
    except KeyError:
        pass
    try:
        keys = params.keys()
        for key in keys:
            if key == 'orderby' or len(key) < 3:
                continue
            value = params.getlist(key)
            if len(value) == 1:
                valid_key = difflib.get_close_matches(key, valid_filters)[0]
                filter_by[valid_key] = value[0]
                continue
            filter_by[key + '__in'] = value
    except Exception:
        pass
    return {'filter': filter_by, 'order': orderby}

@pysnooper.snoop()
def get_categories(box_id=None, category=None):
    if category is None:
        try:
            category = [Category.objects.get(box_id=box_id)]
            print(category)
        except Exception:
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
    return BoxCategoriesSchema().dump(new_cats, many=True)


def last_page(query, step):
    return math.ceil(query.count() / step)


def make_pdf(data='<h1>hello world</h1>'):
    # https://docs.djangoproject.com/en/2.2/howto/outputting-pdf/
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(50, 750, data)
    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=False, filename='hello.pdf')


def make_table():
    doc = SimpleDocTemplate("simple_table_grid.pdf", pagesize=letter)
    # container for the 'Flowable' objects
    elements = []

    data = [['00', '01', '02', '03', '04'],
            ['10', '11', '12', '13', '14'],
            ['20', '21', '22', '23', '24'],
            ['30', '31', '32', '33', '34']]
    t = Table(data, 5 * [0.4 * inch], 4 * [0.4 * inch])
    t.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'RIGHT'),
                           ('TEXTCOLOR', (1, 1), (-2, -2), colors.red),
                           ('VALIGN', (0, 0), (0, -1), 'TOP'),
                           ('TEXTCOLOR', (0, 0), (0, -1), colors.blue),
                           ('ALIGN', (0, -1), (-1, -1), 'CENTER'),
                           ('VALIGN', (0, -1), (-1, -1), 'MIDDLE'),
                           ('TEXTCOLOR', (0, -1), (-1, -1), colors.green),
                           ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                           ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                           ]))

    elements.append(t)
    # write the document to disk
    doc.build(elements)
    return FileResponse(doc, as_attachment=False, filename='hello.pdf')


def print_pdf():
    cm = 2.54
    response = HttpResponse()
    response['Content-Disposition'] = 'attachment; filename=somefilename.pdf'

    elements = []

    doc = SimpleDocTemplate(response, rightMargin=0, leftMargin=6.5 * cm, topMargin=0.3 * cm, bottomMargin=0)

    data = [(1, 2), (3, 4)]
    table = Table(data, colWidths=270, rowHeights=79)
    elements.append(table)
    doc.build(elements)
    return response


def calculate_profit(products):
    total_price = sum([product['storage']['final_price'] * product['count'] for product in products])
    discount_price = sum([product['storage']['discount_price'] * product['count'] for product in products])
    profit = total_price - discount_price
    return {'total_price': total_price, 'discount_price': discount_price, 'profit': profit, 'shopping_cost': 0}


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


def get_basket(user, lang, basket=None):
    basket = basket or Basket.objects.filter(user=user, active=True).first()
    # products = BasketProduct.objects.filter(basket=basket).select_related(*BasketProduct.related)
    address_required = False
    profit = {}
    if basket.products.all().count() > 0:
        basket_dict = BasketSchema(lang).dump(basket)
        profit = calculate_profit(basket_dict['products'])
        # basket['products'] = BasketProductSchema(lang).dump(products, many=True)
        for product in basket_dict['products']:
            if product['storage']['product']['type'] == 'product':
                address_required = True
                break
    else:
        basket_dict = {}
    return {'basket': basket_dict, 'summary': profit, 'address_required': address_required}



def to_obj(body):
    dic = json.loads(body)
    obj = type('test', (object,), {})()
    obj.__dict__ = dic
    return obj


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
