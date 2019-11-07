from django.views import View
from django.core import serializers
import json
from server.models import *
from secrets import token_hex
from server.serialize import *
from mehr_takhfif import settings
import os
import jwt
from mehr_takhfif.settings import TOKEN_SECRET, SECRET_KEY
import pysnooper
import magic
import difflib
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import datetime
from PIL import Image
from mehr_takhfif.settings import MEDIA_ROOT
import math
import reportlab
import io
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from  django.http import JsonResponse, HttpResponse

default_step = 12
default_page = 1
response = {'ok': {'message': 'ok'}, 'bad': {'message': 'bad request'}}


def safe_delete(obj, user):
    obj.deleted_by_id = user
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


@pysnooper.snoop()
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
    filters = ('discount_price', 'discount_vip_price', 'discount_price_percent', 'discount_vip_price_percent',
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


def get_categories(box):
    try:
        category = [Category.objects.get(box=box)]
    except Exception:
        category = Category.objects.all()
    new_cats = [*category]
    remove_index = []
    for cat, index in zip(category, range(len(category))):
        if cat.parent is None:
            continue
        parent_index = new_cats.index(
            category.filter(pk=cat.parent_id).first())
        if not hasattr(new_cats[parent_index], 'child'):
            new_cats[parent_index].child = []
        new_cats[parent_index].child.append(cat)
        remove_index.append(cat)
    new_cats = [x for x in new_cats if x not in remove_index]
    return CategoryMinSchema().dump(new_cats, many=True)


def last_page(query, step):
    return math.ceil(query.count()/step)


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

    data=[(1,2),(3,4)]
    table = Table(data, colWidths=270, rowHeights=79)
    elements.append(table)
    doc.build(elements)
    return response


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
