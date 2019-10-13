from django.views import View
from django.core import serializers
import json
from server.models import *
from secrets import token_hex
from server.serialize import *
from mehr_takhfif import settings
import os
import jwt
import hashlib
from mehr_takhfif.settings import TOKEN_SECRET
import pysnooper
from django.http import JsonResponse
import magic
from server.decorators import try_except
import difflib


class Tools(View):
    step = 12
    page = 1
    response = {'ok': {'message': 'ok'}, 'bad': {'message': 'bad request'}}

    def safe_delete(self, obj, user):
        obj.deleted_by_id = user
        obj.delete()

    def to_json(self, obj=None, string=None):
        if obj is not list:
            obj = [obj]
        if obj:
            string = serializers.serialize("json", obj)
        return json.loads(string[1:-1])['fields']

    def add_minutes(self, minutes):
        return timezone.now() + timezone.timedelta(minutes=minutes)

    def generate_token(self, request, user):
        data = {'user': f'{user.last_login}'}
        first_encrypt = jwt.encode(data, TOKEN_SECRET, algorithm='HS256')
        secret = token_hex(10)
        second_encrypt = jwt.encode({'data': first_encrypt.decode()}, secret, algorithm='HS256')
        access_token = f'{second_encrypt.decode()}{secret}'
        request.session['counter'] = 0
        return access_token

    def hsencode(self, data, secret):
        return jwt.encode(data, secret, algorithm='HS256').decode()

    def hsdecode(self, token, secret):
        return jwt.decode(token, secret, algorithms=['HS256'])

    def get_token_data(self, token):
        first_decrypt = jwt.decode(token[7:-52], token[-52:-32], algorithms=['HS256'])
        return jwt.decode(first_decrypt['data'].encode(), TOKEN_SECRET, algorithms=['HS256'])

    def increase_token_counter(self, request):
        request.session['counter'] += 1

    @try_except
    def upload(self, request, title, box=1):
        image_formats = ['.jpeg', '.jpg', '.gif', '.png']
        video_formats = ['.avi', '.mp4', '.mkv', '.flv', '.mov', '.webm', '.wmv']
        for file in request.FILES.getlist('file'):
            if file is not None:
                file_format = os.path.splitext(file.name)[-1]
                mimetype = self.get_mimetype(file).split('/')[0]
                if mimetype == 'image' and file_format not in image_formats:
                    return False
                if mimetype == 'video' and file_format not in video_formats:
                    return False
                media = Media(file=file, box_id=box, created_by_id=1, type=mimetype, title=title or file)
                media.save()
                return True

    def get_mimetype(self, image):
        mime = magic.Magic(mime=True)
        mimetype = mime.from_buffer(image.read(1024))
        image.seek(0)
        return mimetype

    def move(self, obj, folder):
        old_path = obj.file.path
        new_path = settings.MEDIA_ROOT + f'\\{folder}\\' + obj.file.name
        try:
            os.rename(old_path, new_path)
        except FileNotFoundError:
            os.makedirs(settings.MEDIA_ROOT + f'\\{folder}\\')
            os.rename(old_path, new_path)
        finally:
            obj.save()

    @staticmethod
    def filter_params(params):
        filters = ('discount_price', 'discount_vip_price', 'discount_price_percent', 'discount_vip_price_percent',
                   'product__sold_count', 'created_at')
        filters_op = ('__gt', '__gte', '__lt', '__lte')
        valid_filters = (x + y for y in filters_op for x in filters)
        filterby = {}
        orderby = ['-created_at']
        try:
            orderby += params['orderby']
        except KeyError:
            pass
        try:
            for key in params.keys():
                if key == 'orderby':
                    continue
                value = params.getlist(key)
                if len(value) == 1:
                    valid_key = difflib.get_close_matches(key, valid_filters)[0]
                    filterby[valid_key] = value[0]
                    continue
                filterby[key + '__in'] = value
        except Exception:
            pass
        return {'filter': filterby, 'order':orderby}


class Validation(Tools):
    def __init__(self):
        super().__init__()
        self.phone_pattern = r'^(09[0-9]{9})$'
        self.email_pattern = r'^\w+.*-*@\w+.com$'

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
