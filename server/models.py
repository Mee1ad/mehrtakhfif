import datetime
import os
from operator import attrgetter
from random import randint

import pytz
import requests
from PIL import Image, ImageFilter
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import BTreeIndex, HashIndex, BrinIndex, GinIndex
from django.contrib.sessions.models import Session
from django.core.exceptions import FieldDoesNotExist
from django.core.validators import *
from django.db import models
from django.db.models import CASCADE, PROTECT, SET_NULL, Q, F
from django.db.models import Count
from django.db.utils import IntegrityError
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult
from funcy import project
from push_notifications.models import APNSDevice, GCMDevice
from push_notifications.models import GCMDevice
from safedelete.config import DELETED_INVISIBLE
from safedelete.managers import SafeDeleteQueryset
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from safedelete.signals import post_softdelete

from mehr_takhfif.settings import ELASTICSEARCH_DSL
from mehr_takhfif.settings import HOST, MEDIA_ROOT
from mtadmin.exception import *
from server.field_validation import *

# from django.contrib.sites.models import Site

deliver_status = [(1, 'pending'), (2, 'packing'), (3, 'sending'), (4, 'delivered'), (5, 'referred')]


def get_activation_warning_msg(field_name):
    messages = ['آیتم غیرفعال شد. ' + f'{field_name} مشکل داره']
    index = randint(0, 0)
    return messages[index]


def multilanguage():
    return {"fa": "",
            "en": ""}


def feature_value():
    return [{"id": 0, "fa": "", "en": "", "ar": ""}]


def feature_value_storage():
    return {"bool": {"fsid": 1, "sid": 1, "value": [{"fvid": 1, "price": 5000}]}}


def product_properties():
    lorem = "محصول اول این مجموعه میباشد."
    data = [
        {"type": "default", "priority": "high", "text": lorem},
        {"type": "date", "priority": "high", "text": lorem},
        {"type": "phone", "priority": "high", "text": lorem},
        {"type": "default", "priority": "medium", "text": lorem},
        {"type": "default", "priority": "medium", "text": lorem},
        {"type": "phone", "priority": "medium", "text": lorem},
        {"type": "default", "priority": "low", "text": lorem},
        {"type": "default", "priority": "low", "text": lorem},
        {"type": "date", "priority": "low", "text": lorem}
    ]
    return {'fa': {"usage_condition": data, "property": data}}


def product_details():
    return {
        "fa": {
            "text": "سلام",
            "phone": [
                {
                    "value": "0911138056",
                    "type": "mobile"
                },
                {
                    "value": "0133356255",
                    "type": "phone"
                }
            ],
            "serving_hours": "با هماهنگی",
            "serving_days": "با هماهنگی"
        },
        "en": {
            "text": "salam",
            "phone": [
                {
                    "value": "0911138056",
                    "type": "mobile"
                },
                {
                    "value": "0133356255",
                    "type": "phone"
                }
            ],
            "serving_hours": "ba hamahangi",
            "serving_days": "ba hamahangi"
        }
    }


def next_month():
    return timezone.now() + datetime.timedelta(days=30)


def upload_to(instance, filename):
    date = timezone.now().strftime("%Y-%m-%d")
    time = timezone.now().strftime("%H-%M-%S-%f")[:-4]
    if instance.type < 100:
        time = f'{time}-has-ph'
    # file_type = re.search('\\w+', instance.type)[0]
    file_format = os.path.splitext(instance.image.name)[-1]
    # todo make it with box name
    return f'boxes/{instance.box_id}/{date}/{instance.get_type_display()}/{time}{file_format}'


def reduce_image_quality(img):
    try:
        with Image.open(img) as img:
            x, y = img.size
            width = (60 / x)
            height = int((y * width))
            ph = img.resize((60, height), Image.ANTIALIAS)
            ph = ph.filter(ImageFilter.GaussianBlur(1.6))
        return ph
    except Exception:
        raise ValidationError('بنظر میاد فرمت عکست درست نیست باید jpg باشه!')


def is_list_of_dict(data):
    if type(data) is list:
        for d in data:
            if type(d) is dict:
                continue
            raise ValidationError(_('list item is not dict'))
        return True
    raise ValidationError(_('data is not list'))


def default_meals():
    return {'Breakfast': False, 'Lunch': False, 'Dinner': False}


def permalink_validation(permalink):
    pattern = '^[A-Za-z0-9\u0591-\u07FF\uFB1D-\uFDFD\uFE70-\uFEFC][A-Za-z0-9-\u0591-\u07FF\uFB1D-\uFDFD\uFE70-\uFEFC]*$'
    permalink = permalink
    if permalink and not re.match(pattern, permalink):
        raise ValidationError(_("پیوند یکتا نامعتبر است"))
    return permalink.lower()


def get_name(name, self):
    try:
        return name['fa']
    except Exception:
        return self.id


def timestamp_to_datetime(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)


def translate_types(dictionary, model):
    """
    :types list of tuple: [(1, 'image'), (2, 'thumbnail'), (3, 'media')]
    :param dictionary:
    :param model:
    :return: dictionary
    """
    for item in model.choices:
        types = getattr(model, f'{item}s')
        try:
            dictionary[item] = next((v[0] for i, v in enumerate(types) if v[1] == dictionary[item]), dictionary[item])
        except KeyError:
            pass
    return dictionary


def default_review():
    return {"chats": [], "state": "ready"}


def next_half_hour(minutes=30):
    return timezone.now() + timezone.timedelta(minutes=minutes)


def esearch(q, document, fields=("name_fa",), exact_match=False, only=None):
    s = document.search()
    # r = s.query("multi_match", query=q, fields=fields)
    r = s.query({"dis_max": {"queries": [{"match": {"name_fa": q}}, {"wildcard": {"name_fa": f"*{q}*"}}]}}).sort(
        "_score")
    # r = s.query("wildcard", name_fa=f"{q}*")
    # r = s.query(Q("bool", must=[Q('match', name_fa=q)]))
    # s = Search(index='product')
    # r = s.query(Q('bool', must=[Q('match', name_fa='python'), Q('match', name_fa='best')]))
    [print(hit.to_dict(), hit.meta) for hit in r]
    if exact_match:
        r = r.execute()[0].to_dict()
        if q not in project(r, fields).values():
            return []
        return r
    if only:
        return [project(hit.to_dict(), only)[only[0]] for hit in r]
    return [hit.to_dict() for hit in r]


class MyQuerySet(SafeDeleteQueryset):
    _safedelete_visibility = DELETED_INVISIBLE
    _safedelete_visibility_field = 'pk'
    _queryset_class = SafeDeleteQueryset

    def update(self, *args, **kwargs):
        warning = kwargs.pop('warning', True)
        # todo say if enabled or disabled
        if not self:
            return True
        remove_list = ['id', 'box_id', 'remove_fields']
        validations = {'storage': self.storage_validation, 'category': self.category_validation,
                       'product': self.product_validation, 'ad': self.ad_validation, 'slider': self.ad_validation,
                       'invoicestorage': self.invoice_storage_validation, 'invoice': self.invoice_validation}
        model = self[0].__class__.__name__.lower()
        validations.update(dict.fromkeys(['feature', 'brand', 'tag'], self.default_validation))
        # noinspection PyArgumentList
        kwargs = validations[model](**kwargs)
        remove_fields = kwargs.get('remove_fields', None)
        [kwargs.pop(item, None) for item in remove_list]
        is_updated = super().update(**kwargs)
        if model == 'storage' and self:
            storage = self.first()
            storage.post_process(remove_fields)
            storage.update_price()
            if kwargs.get('disable') is True:
                if storage.product.storages.count() <= 1:
                    storage.product.disable = True
                # storage.related_packages.update(package__disable=True)
                storage.cascade_disabling(storage, warning)

        elif model == 'product':
            product = self.first()
            # storages = product.storages.all()
            # todo fix in add product
            # storages.first().cascade_disabling(storages)
        return is_updated

    def category_validation(self, **kwargs):
        category = self.first()
        permalink_validation(kwargs.get('permalink', 'pass'))
        pk = kwargs.get('id')
        parent_id = kwargs.get('parent_id')
        if (pk == parent_id and pk is not None) or Category.objects.filter(pk=parent_id, parent_id=pk).exists():
            raise ValidationError(_("والد نامعتبر است"))
        if not category.media and kwargs.get('disable') is False:
            raise ValidationError(_('قبل از فعالسازی تصویر دسته بندی را مشخص کنید'))
        # features = Feature.objects.filter(pk__in=kwargs.get('features', []))
        # category.feature_set.clear()
        # category.feature_set.add(*features)
        return kwargs

    def storage_validation(self, **kwargs):
        # for storage and invoice_storage
        storage = self.first()
        kwargs = storage.pre_process(kwargs, storage.product.box_id)
        return kwargs

    def invoice_validation(self, **kwargs):
        invoice = self.first()
        kwargs = invoice.pre_process(kwargs)
        return kwargs

    def invoice_storage_validation(self, **kwargs):
        invoice = self.first()
        kwargs = invoice.pre_process(kwargs)
        return kwargs

    def product_validation(self, **kwargs):
        product = self.first()
        kwargs = product.pre_process(kwargs)
        storages_id = kwargs.get('storages_id', [])
        if storages_id:
            [Storage.objects.filter(pk=pk).update(priority=kwargs['storages_id'].index(pk))
             for pk in storages_id]
            kwargs.pop('storages_id')
            return kwargs
        default_storage_id = kwargs.get('default_storage_id')
        pk = kwargs.get('id')
        if default_storage_id:
            new_default_storage = Storage.objects.filter(pk=default_storage_id)
            Storage.objects.filter(product_id=pk, priority__lt=new_default_storage.first().priority) \
                .order_by('priority').update(priority=F('priority') + 1)
            new_default_storage.update(priority=0)
        if kwargs.get('manage', None):
            item = self.first()
            item.assign_default_value()
        return kwargs

    def ad_validation(self, **kwargs):
        self.full_clean()
        return kwargs

    # todo advance disabler for product storage category

    def default_validation(self, **kwargs):
        item = self.first()
        return item.validation(kwargs)


# noinspection PyUnresolvedReferences
class Base(SafeDeleteModel):
    # related_query_name = "%(app_label)s_%(class)ss" for many to many
    class Meta:
        abstract = True

    serializer_exclude = ()
    no_box_type = [4, 5, 6, 8]
    required_fields = []
    required_multi_lang = []
    related_fields = []
    m2m = []
    remove_fields = []
    custom_m2m = {}
    ordered_m2m = {}
    required_m2m = []
    fields = {}
    keep_m2m_data = []
    table_select = []
    select = ['created_by', 'updated_by', 'deleted_by']
    table_prefetch = []
    prefetch = []
    table_annotate = {}
    annotate = {}
    choices = ()
    exclude_fields = []

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=PROTECT, related_name="%(app_label)s_%(class)s_created_by")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('User', on_delete=PROTECT, related_name="%(app_label)s_%(class)s_updated_by")
    deleted_by = models.ForeignKey('User', on_delete=PROTECT, null=True, blank=True,
                                   related_name="%(app_label)s_%(class)s_deleted_by")

    def safe_delete(self, user_id=1):
        i = 1
        message = None
        model = self.__class__
        query = model.objects.filter(pk=self.pk)
        while True:
            try:
                # self.permalink = f"{self.permalink}-deleted-{i}"
                # self.deleted_by_id = user_id
                # self.save()
                query.update(permalink=f'{F("permalink")}-deleted-{i}', deleted_by=user_id)
                break
            except IntegrityError:
                i += 1
            except FieldDoesNotExist:
                # self.deleted_by_id = user_id
                # message = self.save()
                query.update(deleted_by=user_id)
                break
        self.delete()
        if message:
            # todo
            raise WarningMessage(message['message'])

    def get_name_fa(self):
        try:
            return self.name['fa']
        except Exception:
            pass

    def clean(self):
        if hasattr(self, 'disable'):
            for field in self.required_fields:
                if not getattr(self, field):
                    self.make_item_disable(self)
                    raise ActivationError(get_activation_warning_msg(self.fields[field]))
            for field in self.related_fields:
                if not hasattr(self, field):
                    self.make_item_disable(self)
                    raise ActivationError(get_activation_warning_msg(self.fields[field]))
            for field in self.required_m2m:
                if not getattr(self, field).all():
                    self.make_item_disable(self)
                    raise ActivationError(get_activation_warning_msg(self.fields[field]))
            for field in self.required_multi_lang:
                if not getattr(self, field)['fa']:
                    raise ActivationError(get_activation_warning_msg(self.fields[field]))

    def make_item_disable(self, obj, warning=True):
        obj.__class__.objects.filter(pk=obj.pk).update(disable=True, warning=warning)

    def cascade_disabling(self, storages=None, warning=True):
        if type(storages) != list and storages is not None:
            storages = [storages]
        for storage in storages:
            if not storage.product.storages.filter(disable=False):
                Product.objects.filter(pk=storage.product_id).update(disable=True)
            special_products = storage.special_products.all()
            if special_products:
                [special_product.safe_delete() for special_product in special_products]
            package_records = storage.related_packages.all()
            for package_record in package_records:
                Storage.objects.filter(pk=package_record.package_id).update(disable=True)
        # if warning:
        #     raise WarningMessage('آیا میدانستی: محصولات ویژه و پکیج هایی که شامل این انبار بودن هم غیرفعال میشن؟! 🤭')


class MyModel(models.Model):
    class Meta:
        abstract = True

    id = models.BigAutoField(auto_created=True, primary_key=True)
    serializer_exclude = ()
    no_box_type = [4, 5, 6, 8]
    required_fields = []
    required_multi_lang = []
    related_fields = []
    m2m = []
    remove_fields = []
    custom_m2m = {}
    ordered_m2m = {}
    required_m2m = []
    fields = {}
    keep_m2m_data = []
    table_select = []
    select = []
    table_prefetch = []
    prefetch = []
    table_annotate = {}
    annotate = {}
    choices = ()
    exclude_fields = []


class Ad(Base):
    select = ['media', 'mobile_media', 'storage'] + Base.select
    serializer_exclude = ()
    required_fields = ['media', 'mobile_media', 'type']
    required_multi_lang = ['title']
    fields = {'title': 'عنوان', 'media': 'تصویر', 'mobile_media': 'تصویر موبایل', 'type': 'نوع'}

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args)

    def __str__(self):
        return self.title['fa']

    title = JSONField(default=multilanguage)
    url = models.CharField(max_length=255, null=True, blank=True)
    priority = models.PositiveIntegerField(default=0)
    media = models.ForeignKey("Media", on_delete=PROTECT, related_name='ad')
    mobile_media = models.ForeignKey("Media", on_delete=PROTECT, null=True, blank=True, related_name='ad_mobile')
    storage = models.ForeignKey("Storage", on_delete=PROTECT, blank=True, null=True)
    type = models.CharField(default='home', max_length=255)

    class Meta:
        db_table = 'ad'
        indexes = [BTreeIndex(fields=['priority', 'type'])]


class User(AbstractUser):
    select = ['default_address', 'created_by', 'updated_by']
    prefetch = ['vip_types', 'box_permission']
    serializer_exclude = ()
    required_fields = []
    required_multi_lang = []
    related_fields = []
    m2m = []
    remove_fields = []
    custom_m2m = {}
    ordered_m2m = {}
    required_m2m = []
    fields = {}
    table_select = []
    table_prefetch = []
    table_annotate = {}
    annotate = {}
    choices = ()

    def __str__(self):
        try:
            return self.first_name + ' ' + self.last_name
        except TypeError:
            return self.username
        except Exception:
            return ""

    def clean(self):
        pass

    def save(self, *args, **kwargs):
        # self.full_clean()
        super().save(*args, **kwargs)

    tg_id = models.PositiveIntegerField(null=True, blank=True)
    tg_username = models.CharField(max_length=255, null=True, blank=True)
    tg_first_name = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.URLField(null=True, blank=True)
    first_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='First name')
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Last name')
    username = models.CharField(max_length=150, unique=True)
    phone = models.CharField(max_length=150, null=True, blank=True)
    language = models.CharField(max_length=7, default='fa')
    email = models.CharField(max_length=255, blank=True, null=True, validators=[validate_email])
    password = models.CharField(max_length=255, blank=True, null=True)
    gender = models.BooleanField(blank=True, null=True)  # True: man, False: woman
    is_ban = models.BooleanField(default=False)
    shaba = models.CharField(max_length=255, null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False, verbose_name='Phone verified')
    is_superuser = models.BooleanField(default=False, verbose_name='Superuser')
    is_staff = models.BooleanField(default=False, verbose_name='Staff')
    is_supplier = models.BooleanField(default=False)
    is_verify = models.BooleanField(default=False)
    email_alert = models.BooleanField(default=True)
    pm_alert = models.BooleanField(default=True)
    privacy_agreement = models.BooleanField(default=False)
    deposit_id = models.PositiveSmallIntegerField(null=True, blank=True)
    default_address = models.OneToOneField(to="Address", on_delete=SET_NULL, null=True, blank=True,
                                           related_name="user_default_address")
    vip_types = models.ManyToManyField(to="VipType", related_name="users", blank=True)
    box_permission = models.ManyToManyField("Box", blank=True)
    email_verified = models.BooleanField(default=False, verbose_name='Email verified')
    subscribe = models.BooleanField(default=True)
    meli_code = models.CharField(max_length=15, blank=True, null=True, verbose_name='National code',
                                 validators=[validate_meli_code])
    wallet_credit = models.IntegerField(default=0)
    suspend_expire_date = models.DateTimeField(blank=True, null=True, verbose_name='Suspend expire date')
    activation_code = models.CharField(max_length=127, null=True, blank=True)
    activation_expire = models.DateTimeField(null=True, blank=True)
    token = models.CharField(max_length=255, unique=True, null=True, blank=True)
    token_expire = models.DateTimeField(auto_now_add=True)
    settings = JSONField(default=dict, blank=True)
    created_by = models.ForeignKey('User', on_delete=PROTECT, related_name="%(app_label)s_%(class)s_created_by",
                                   null=True, blank=True)
    updated_by = models.ForeignKey('User', on_delete=PROTECT, related_name="%(app_label)s_%(class)s_updated_by",
                                   null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(blank=True, auto_now=True, verbose_name='Updated at')

    class Meta:
        db_table = 'user'
        indexes = [BTreeIndex(fields=['is_staff'])]


class VipType(Base):
    serializer_exclude = ()
    required_fields = []
    required_multi_lang = []
    related_fields = []
    m2m = []
    remove_fields = []
    custom_m2m = {}
    ordered_m2m = {}
    required_m2m = []
    fields = {}

    def __str__(self):
        return self.name['fa']

    name = JSONField(default=multilanguage)
    media = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'vip_type'


class Client(MyModel):
    select = ['gcm_device'] + MyModel.select
    device_id = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    last_login_ip = models.CharField(max_length=31, null=True, blank=True)
    gcm_device = models.ForeignKey(GCMDevice, on_delete=CASCADE, related_name="client")

    class Meta:
        db_table = 'client'
        indexes = [HashIndex(fields=['device_id'])]


class Charity(Base):
    name = JSONField(default=multilanguage)
    deposit_id = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'charity'


class State(MyModel):
    def __str__(self):
        return self.name

    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'state'


class City(MyModel):
    select = ['state'] + MyModel.select

    def __str__(self):
        return self.name

    name = models.CharField(max_length=255)
    state = models.ForeignKey(State, on_delete=CASCADE)

    class Meta:
        db_table = 'city'


class Address(MyModel):
    """
        Stores a single blog entry, related to :model:`auth.User` and
        :model:`server.Address`.
    """

    select = ['state', 'city', 'user'] + MyModel.select

    def __str__(self):
        return self.city.name

    def validation(self):
        if not City.objects.filter(pk=self.city.pk, state=self.state).exists():
            raise ValidationError(_('شهر یا استان نامعتبر است'))

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    state = models.ForeignKey(State, on_delete=PROTECT)
    city = models.ForeignKey(City, on_delete=PROTECT)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    postal_code = models.CharField(max_length=15, verbose_name='Postal code')
    address = models.TextField()
    location = JSONField(null=True, blank=True)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    reservable = models.BooleanField(default=False)

    class Meta:
        db_table = 'address'


class Box(Base):
    select = ['owner', 'media']

    def __str__(self):
        return self.name['fa']

    def clean(self, **kwargs):
        super().clean()
        if self.disable:
            special_products = SpecialProduct.objects.filter(box=self)
            [special_product.safe_delete() for special_product in special_products]

    name = JSONField(default=multilanguage)
    permalink = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(User, on_delete=PROTECT)
    settings = JSONField(default=dict, blank=True)
    disable = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(default=0)
    share = models.FloatField(default=0.325)
    media = models.ForeignKey("Media", on_delete=CASCADE, null=True, blank=True, related_name="box_image_box_id")

    class Meta:
        db_table = 'box'
        permissions = [("has_access", "Can manage that box")]
        indexes = [HashIndex(fields=['permalink'])]


class Media(Base):
    types = [(1, 'image'), (2, 'thumbnail'), (3, 'media'), (4, 'slider'), (5, 'ads'), (6, 'mobile_ads'),
             (7, 'category'), (8, 'mobile_slider'), (9, 'description'), (100, 'video'), (200, 'audio')]
    no_box_type = [4, 5, 6, 8]
    media_sizes = {'thumbnail': (600, 372), 'media': (1280, 794), 'category': (800, 500), 'ads': (820, 300),
                   'mobile_ads': (500, 384), 'slider': (1920, 504), 'mobile_slider': (980, 860)}
    select = ['box'] + Base.select

    def get_absolute_url(self):
        return self.image.url

    def get_urls(self):
        return "/test/"

    def __str__(self):
        try:
            return self.title['fa']
        except KeyError:
            return self.title['user_id']

    def save(self, *args, **kwargs):
        try:
            with Image.open(self.image) as im:
                try:
                    width, height = im.size
                    if (width, height) != self.media_sizes[self.get_type_display()]:
                        raise ValidationError(_('سایز عکس نامعتبر است'))
                except KeyError as e:
                    print(e)
        except ValueError:
            pass
        super().save(*args, **kwargs)
        if self.type < 100 and self.image:
            ph = reduce_image_quality(self.image.path)
            name = self.image.name.replace('has-ph', 'ph')
            ph.save(f'{MEDIA_ROOT}/{name}', optimize=True, quality=80)

    image = models.FileField(upload_to=upload_to, null=True, blank=True)
    video = models.URLField(null=True, blank=True)
    audio = models.URLField(null=True, blank=True)
    title = JSONField(default=multilanguage)
    type = models.PositiveSmallIntegerField(choices=types)
    box = models.ForeignKey(Box, on_delete=models.CASCADE, null=True, blank=True, related_name="medias")

    class Meta:
        db_table = 'media'
        indexes = [BrinIndex(fields=['type'])]


class Category(Base):
    objects = MyQuerySet.as_manager()
    serializer_exclude = ('box',)
    required_fields = []
    related_fields = []
    m2m = ['feature_groups']
    required_m2m = []
    fields = {}
    select = ['parent', 'box', 'media'] + Base.select

    def get_absolute_url(self):
        return "/search/" + self.permalink

    def clean(self):
        if self.products.count() <= 10:
            self.make_item_disable(self)
            raise ActivationError('حداقل تعداد محصولات باید 10 عدد باشد')
        if getattr(getattr(self, 'parent', None), 'disable', None) is True:
            self.make_item_disable(self)
            raise ActivationError('لطفا ابتدا دسته بندی والد را فعال نمایید')
        if self.parent is None and self.permalink is None:
            self.make_item_disable(self)
            raise ActivationError('این دسته بندی که ساختی بدرد نمیخوره')
        super().clean()

    def __str__(self):
        return f"{self.name['fa']}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        pk = self.id
        parent_id = self.parent_id
        if Category.objects.filter(pk=parent_id, parent_id=pk).exists():
            self.parent = None
            self.save()
            raise ValidationError(_("والد نامعتبر است"))

    def get_media(self):
        try:
            return HOST + self.media.image.url
        except Exception:
            pass

    def get_parent_fa(self):
        return getattr(getattr(self, 'parent', None), 'name', {}).get('fa')

    def get_box_name(self):
        return self.box.name['fa']

    parent = models.ForeignKey("self", on_delete=CASCADE, null=True, blank=True)
    box = models.ForeignKey(Box, on_delete=CASCADE)
    # features = models.ManyToManyField("Feature")
    feature_groups = models.ManyToManyField("FeatureGroup", through="CategoryGroupFeature", related_name='categories')
    name = JSONField(default=multilanguage)
    permalink = models.CharField(max_length=255, db_index=True, unique=True, null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=0)
    disable = models.BooleanField(default=True)
    media = models.ForeignKey(Media, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'category'
        indexes = [HashIndex(fields=['permalink'])]


class CategoryGroupFeature(MyModel):
    select = ['category', 'featuregroup'] + Base.select
    category = models.ForeignKey(Category, on_delete=PROTECT)
    featuregroup = models.ForeignKey("FeatureGroup", on_delete=PROTECT)

    class Meta:
        db_table = 'category_group_feature'


class FeatureValue(Base):
    select = ['feature'] + Base.select

    def __str__(self):
        return f"{self.id}"

    feature = models.ForeignKey("Feature", on_delete=CASCADE, related_name="values")
    value = JSONField(default=dict)
    priority = models.PositiveIntegerField(default=0)
    settings = JSONField(default=dict, blank=True)

    # priority = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'feature_value'


class Feature(Base):
    objects = MyQuerySet.as_manager()

    m2m = ['groups']
    ordered_m2m = {'values': FeatureValue}
    keep_m2m_data = ['values']
    types = ((1, 'bool'), (2, 'text'), (3, 'selectable'))
    layout_types = ((1, 'default'),)
    choices = ('type', 'layout_type')
    table_prefetch = ('values', 'groups__feature_group_features__feature',
                      'groups__feature_group_features__feature__values')

    def __str__(self):
        return get_name(self.name, self)

    def validation(self, kwargs):
        # [kwargs.pop(item, None) for item in kwargs.get('remove_fields', [])]
        # if kwargs['type'] in [1, 3]:
        #     if len(kwargs['values']) < 2:
        #         raise ValidationError(_('حداقل دوتا آیتم باید وارد کنی'))
        # if kwargs['type'] == 2:
        #     if len(kwargs['values']) < 1:
        #         raise ValidationError(_('مقدار پیشفرض رو باید وارد کنی'))
        return kwargs

    def save(self, *args, **kwargs):
        self.validation(self.__dict__)
        super().save(*args, **kwargs)

    name = JSONField(default=multilanguage)
    # group = models.ForeignKey("FeatureGroup", on_delete=CASCADE, related_name="features", null=True, blank=True)
    type = models.PositiveSmallIntegerField(default=1, choices=types)
    layout_type = models.PositiveSmallIntegerField(default=1, choices=layout_types)
    settings = JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'feature'


class FeatureGroupFeature(MyModel):
    select = ['feature', 'featuregroup'] + MyModel.select
    feature = models.ForeignKey(Feature, on_delete=CASCADE, related_name="feature_group_features")
    featuregroup = models.ForeignKey("FeatureGroup", on_delete=CASCADE, related_name="feature_group_features")
    priority = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'feature_group_feature'


class FeatureGroup(Base):
    select = ['box'] + Base.select
    prefetch = ['feature_group_features__feature__values']

    def __str__(self):
        return get_name(self.name, self)

    # m2m = ['features']
    ordered_m2m = {'features': FeatureGroupFeature}
    # custom_m2m = {'features': Feature}

    name = JSONField(default=multilanguage)
    settings = JSONField(default=dict, help_text="{ui: {show_title: true}}")
    box = models.ForeignKey(Box, on_delete=PROTECT)
    features = models.ManyToManyField("Feature", through="FeatureGroupFeature", related_name='groups')

    class Meta:
        db_table = 'feature_group'


class Tag(Base):
    objects = MyQuerySet.as_manager()

    def get_absolute_url(self):
        return "/search?tags=" + self.permalink

    def __str__(self):
        return f"{self.name['fa']}"

    def validation(self, kwargs):
        permalink_validation(kwargs.get('permalink', 'pass'))
        name = kwargs.get('name', None)
        name_fa = name['fa']
        es = f"http://{ELASTICSEARCH_DSL['default']['hosts']}"
        r = requests.get(f"{es}/tag/_search?q=name_fa:{name_fa}&size=1")
        try:
            if name_fa == r.json()['hits']['hits'][0]['_source']['name_fa']:
                raise ValidationError("نام تگ تکراریه")
        except (IndexError, KeyError):
            pass
        # if esearch(name, Tag):
        #
        #     if Tag.objects.filter((Q(name__en=name['en']) & ~Q(name__en="") & ~Q(id=kwargs['id'])) |
        #                           (Q(name__fa=name['fa']) & ~Q(name__fa="") & ~Q(id=kwargs['id'])) |
        #                           (Q(name__ar=name['ar']) & ~Q(name__ar="") & ~Q(id=kwargs['id']))).count() > 0:
        #         raise IntegrityError("DETAIL:  Key (name)=() already exists.")
        return kwargs

    def save(self, *args, **kwargs):
        self.__dict__ = self.validation(self.__dict__)
        super().save(*args, **kwargs)

    permalink = models.CharField(max_length=255, db_index=True, unique=True)
    name = JSONField(default=multilanguage)

    class Meta:
        db_table = 'tag'
        indexes = [HashIndex(fields=['permalink']), GinIndex(fields=['name'])]


class TagGroupTag(MyModel):
    select = ['taggroup', 'tag'] + MyModel.select
    taggroup = models.ForeignKey("TagGroup", on_delete=PROTECT, related_name='tag_group_tags')
    tag = models.ForeignKey(Tag, on_delete=PROTECT, related_name='tag_group_tags')
    show = models.BooleanField(default=False)

    class Meta:
        db_table = 'tag_group_tags'


class TagGroup(Base):
    # objects = MyQuerySet.as_manager()

    custom_m2m = {'tags': TagGroupTag}
    select = ['box'] + Base.select

    def __str__(self):
        return f"{self.name['fa']}"

    box = models.ForeignKey(Box, on_delete=PROTECT)
    name = JSONField(default=multilanguage)
    tags = models.ManyToManyField(Tag, through="TagGroupTag", related_name='groups')

    class Meta:
        db_table = 'tag_group'


class Brand(Base):
    objects = MyQuerySet.as_manager()

    def __str__(self):
        return f"{self.name['fa']}"

    def validation(self, kwargs):
        self.permalink = self.permalink.lower()
        name = kwargs.get('name', None)
        name_fa = name['fa']
        es = f"http://{ELASTICSEARCH_DSL['default']['hosts']}"
        r = requests.get(f"{es}/brand/_search?q=name_fa:{name_fa}&size=1")
        try:
            if name_fa == r.json()['hits']['hits'][0]['_source']['name_fa']:
                raise ValidationError("نام برند تکراریه")
        except (IndexError, KeyError):
            pass

        # if Brand.objects.filter((Q(name__en=name['en']) & ~Q(name__en="") & ~Q(id=kwargs['id'])) |
        #                         (Q(name__fa=name['fa']) & ~Q(name__fa="") & ~Q(id=kwargs['id'])) |
        #                         (Q(name__ar=name['ar']) & ~Q(name__ar="") & ~Q(id=kwargs['id']))).count() > 0:
        #     raise IntegrityError("DETAIL:  Key (name)=() already exists.")
        return kwargs

    def save(self, *args, **kwargs):
        self.validation(self.__dict__)
        super().save(*args, **kwargs)

    name = JSONField(default=multilanguage)
    permalink = models.CharField(max_length=255, db_index=True, unique=True)

    class Meta:
        db_table = 'brand'
        # indexes = [GinIndex(fields=['permalink'])]


# from django.db.models.signals import pre_init
#
#
# @receiver(pre_init, sender=Brand)
# def blog_pre_init_signal(sender, *args, **kwargs):
#     print("sender:", sender)
#     print("kwargs is:", kwargs['kwargs'])
#     kwargs['kwargs']['name'] = {'fa': 'haha', 'en': '', 'ar': ''}


class ProductTag(MyModel):
    select = ['product', 'tag'] + MyModel.select
    product = models.ForeignKey("Product", on_delete=CASCADE, related_name='product_tags')
    tag = models.ForeignKey(Tag, on_delete=CASCADE)
    show = models.BooleanField(default=False)

    class Meta:
        db_table = 'product_tag'


class ProductMedia(MyModel):
    related = ['storage']
    select = ['product', 'media'] + MyModel.select

    def __str__(self):
        return f"{self.id}"

    product = models.ForeignKey("Product", on_delete=CASCADE, related_name="product_media")
    media = models.ForeignKey(Media, on_delete=CASCADE)
    priority = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'product_media'


class ProductFeature(Base):
    select = ['product', 'feature', 'feature_value'] + Base.select

    def __str__(self):
        return f"{self.id}"

    product = models.ForeignKey("Product", on_delete=CASCADE, related_name="product_features", db_index=False)
    feature = models.ForeignKey(Feature, on_delete=CASCADE, db_index=False)
    feature_value = models.ForeignKey(FeatureValue, on_delete=CASCADE, null=True, related_name='product_features')
    settings = JSONField(default=dict)
    priority = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'product_feature'
        indexes = [BTreeIndex(fields=['product', 'feature'])]


class ProductFeatureStorage(MyModel):
    select = ['product_feature', 'storage'] + MyModel.select

    def __str__(self):
        return f"{self.id}"

    product_feature = models.ForeignKey(ProductFeature, on_delete=CASCADE, related_name="product_feature_storages",
                                        db_index=False)
    storage = models.ForeignKey("Storage", on_delete=CASCADE, db_index=False)
    extra_data = JSONField(default=dict)

    class Meta:
        db_table = 'product_feature_storage'
        indexes = [BTreeIndex(fields=['product_feature', 'storage'])]


class StorageAccessories(MyModel):
    # related = ['storage']
    # select = ['storage', 'basket', 'vip_price', 'box'] + MyModel.select

    def __str__(self):
        return f"{self.id}"

    def validation(self):
        pass

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    storage = models.ForeignKey("Storage", on_delete=CASCADE, related_name="storage_accessories")
    accessory_product = models.ForeignKey("Product", on_delete=CASCADE, related_name="accessory_products")
    accessory_storage = models.ForeignKey("Storage", on_delete=CASCADE, related_name="accessory_storage_storages")
    discount_price = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'storage_accessories'
        # indexes = [BTreeIndex(fields=['basket', 'storage'])]
        # unique_together = ('basket', 'storage')


class Product(Base):
    objects = MyQuerySet.as_manager()
    table_select = ['thumbnail']
    select = ['box', 'default_storage', 'brand'] + Base.select + table_select
    table_prefetch = ['storages', 'categories']
    prefetch = ['cities', 'states'] + Base.prefetch
    # Prefetch('storages', queryset=Storage.objects.filter, to_attr='count')] + Base.prefetch
    table_annotate = {'active_storages_count': Count('storages', filter=Q(storages__disable=False)),
                      'storages_count': Count('storages')}
    annotate = {**Base.annotate}
    filter = {"verify": True, "disable": False}

    required_fields = ['thumbnail', 'description']
    related_fields = []
    remove_fields = []
    custom_m2m = {'tags': ProductTag}
    ordered_m2m = {'media': ProductMedia, 'features': ProductFeature}
    m2m = ['categories', 'cities', 'tag_groups', 'states', 'feature_groups']
    required_m2m = ['categories', 'media']
    fields = {'thumbnail': 'تامبنیل', 'categories': 'دسته بندی', 'tags': 'تگ', 'media': 'مدیا',
              'description': 'توضیحات'}
    types = [(1, 'service'), (2, 'product'), (3, 'tourism'), (4, 'package'), (5, 'package_item')]
    booking_types = [(1, 'unbookable'), (2, 'datetime'), (3, 'range')]
    accessory_types = [(1, 'not'), (2, 'can_be'), (3, 'only')]
    choices = ('type', 'booking_type', 'accessory_type')
    exclude_fields = ['feature_groups', 'storages', 'default_storage', 'available']

    def get_absolute_url(self):
        return f"/product/{self.permalink}"

    def pre_process(self, my_dict):
        # if (self.review['chat'] != []) and (my_dict.get('review') != self.review):
        #     my_dict['check_review'] = False
        try:
            my_dict['type'] = {'service': 1, 'product': 2, 'tourism': 3, 'package': 4, 'package_item': 5}[
                my_dict['type']]
        except KeyError:
            pass
        try:
            my_dict['booking_type'] = {'unbookable': 1, 'datetime': 2, 'range': 3}[my_dict['booking_type']]
        except KeyError:
            pass
        return my_dict

    def clean(self):
        super().clean()
        if not self.tags.all() and not self.tag_groups.all():
            self.make_item_disable(self)
            raise ActivationError('نه تگ داری نه گروه تک، نمیشه ک اینجوری میشه؟')
        if not self.storages.filter(disable=False):
            self.make_item_disable(self)
            raise ActivationError(get_activation_warning_msg('انبار فعال'))
        if self.review['state'] == 'reviewed':
            self.make_item_disable(self)
            raise ActivationError('بنظر نمیاد محصولت آماده فعال شدن باشه، یه نگاه به چت محصول بنداز!')
        # todo for now
        Product.objects.filter(pk=self.pk).update(verify=True)

    def assign_default_value(self):
        storages = self.storages.filter(available_count_for_sale__gt=0, unavailable=False, disable=False)
        if not storages:
            storages = self.storages.all()
        try:
            Product.objects.filter(pk=self.pk).update(default_storage=min(storages, key=attrgetter('discount_price')))
        except ValueError:
            print(f'product {self.id} has not any storage, cant assign default storage')

    def save(self, *args, **kwargs):
        self.pre_process(self.__dict__)
        super().save(*args, **kwargs)

    def __str__(self):
        return getattr(self.name, 'fa', '')

    def get_name_en(self):
        return self.name['en']

    def get_name_ar(self):
        return self.name['ar']

    def get_category_fa(self):
        try:
            return self.categories.all().first().name['fa']
        except Exception:
            pass

    def get_category_en(self):
        return self.categories.name['en']

    def get_category_ar(self):
        return self.categories.name['ar']

    def get_thumbnail(self):
        try:
            return HOST + self.thumbnail.image.url
        except Exception:
            pass

    # def save(self):
    #     self.slug = slugify(self.title)
    #     super(Post, self).save()

    categories = models.ManyToManyField(Category, related_name="products", blank=True)
    box = models.ForeignKey(Box, on_delete=PROTECT, db_index=False)
    brand = models.ForeignKey(Brand, on_delete=SET_NULL, null=True, blank=True, related_name="products")
    thumbnail = models.ForeignKey(Media, on_delete=PROTECT, related_name='products', null=True, blank=True)
    cities = models.ManyToManyField(City, blank=True)
    states = models.ManyToManyField(State, blank=True)
    default_storage = models.OneToOneField(null=True, blank=True, to="Storage", on_delete=SET_NULL,
                                           related_name='product_default_storage', db_index=False)
    tags = models.ManyToManyField(Tag, through="ProductTag", related_name='products', blank=True)
    tag_groups = models.ManyToManyField(TagGroup, related_name='products', blank=True)
    media = models.ManyToManyField(Media, through='ProductMedia', blank=True)
    features = models.ManyToManyField(Feature, through='ProductFeature', related_name='products', blank=True)
    feature_groups = models.ManyToManyField("FeatureGroup", related_name='products', blank=True)
    income = models.BigIntegerField(default=0)
    profit = models.PositiveIntegerField(default=0)
    rate = models.PositiveSmallIntegerField(default=0)
    disable = models.BooleanField(default=True)
    verify = models.BooleanField(default=False)
    manage = models.BooleanField(default=True)
    booking_type = models.PositiveSmallIntegerField(choices=booking_types, default=1)
    accessory_type = models.PositiveSmallIntegerField(choices=accessory_types, default=1)
    # accessories = models.ManyToManyField("self", through='ProductAccessories', symmetrical=False)
    breakable = models.BooleanField(default=False)
    type = models.PositiveSmallIntegerField(choices=types, validators=[validate_product_type])
    permalink = models.CharField(max_length=255, db_index=False, unique=True)

    name = JSONField(default=multilanguage)
    # name = pg_search.SearchVectorField(null=True)
    short_description = JSONField(default=multilanguage)
    description = JSONField(default=multilanguage)
    invoice_description = JSONField(default=multilanguage)
    location = JSONField(null=True, blank=True)
    address = JSONField(null=True, blank=True)
    short_address = JSONField(null=True, blank=True)
    properties = JSONField(null=True, blank=True)
    details = JSONField(null=True, blank=True)
    settings = JSONField(default=dict, blank=True)
    # review = models.TextField(null=True, blank=True)
    review = JSONField(default=default_review, help_text="{chats: [], state: reviewed/request_review/ready}")

    # site = models.ForeignKey(Site, on_delete=models.CASCADE, default=1)

    # check_review = models.BooleanField(default=False)

    # home_buissiness =
    # support_description =
    class Meta:
        db_table = 'product'
        # ordering = ['-updated_at']
        indexes = [BTreeIndex(fields=['box', 'default_storage', 'updated_at', 'created_at']),
                   HashIndex(fields=['permalink'])]


class Package(Base):
    select = ['package', 'package_item'] + Base.select

    def __str__(self):
        return self.package.title['fa']

    def save(self, *args, **kwargs):
        if Package.objects.filter(package_item=self.package_item).exists():
            raise ValidationError('انبار تکراریه')
        super().save(*args, **kwargs)

    package = models.ForeignKey("Storage", on_delete=PROTECT, related_name="packages")
    package_item = models.ForeignKey("Storage", on_delete=PROTECT, related_name="related_packages")
    count = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = 'package'


class VipPrice(MyModel):
    select = ['vip_type', 'storage'] + MyModel.select

    def __str__(self):
        return f"{self.storage.title['fa']}"

    vip_type = models.ForeignKey(VipType, on_delete=PROTECT)
    storage = models.ForeignKey("Storage", on_delete=PROTECT, related_name="vip_prices")
    discount_price = models.PositiveIntegerField()
    discount_percent = models.PositiveSmallIntegerField()
    max_count_for_sale = models.PositiveSmallIntegerField(default=1)
    available_count_for_sale = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'vip_price'


class Storage(Base):
    objects = MyQuerySet.as_manager()
    select = ['product__thumbnail', 'supplier'] + Base.select
    prefetch = []

    required_fields = ['supplier']
    related_fields = []
    m2m = []
    remove_fields = ['vip_prices', 'items']  # handle in post_process
    custom_m2m = {'features': ProductFeatureStorage, 'accessories': StorageAccessories}
    required_m2m = []
    fields = {'supplier': 'تامین کننده', 'dimensions': 'ابعاد'}
    tax_types = [(1, 'has_not'), (2, 'from_total_price'), (3, 'from_profit')]
    choices = ('tax_type',)

    def full_clean(self, exclude=None, validate_unique=True):
        if Package.objects.filter(package=self):
            self.clean()
        else:
            super().full_clean(exclude=None, validate_unique=True)

    def clean(self):
        if self.product.type != 4:
            super().clean()
            if self.available_count < self.available_count_for_sale:
                self.make_item_disable(self)
                raise ActivationError(get_activation_warning_msg('موجودی انبار'))
            if self.supplier and self.supplier.is_verify is False:
                self.make_item_disable(self)
                raise ActivationError(get_activation_warning_msg('تامین کننده'))
            if (self.features_percent > 100 or self.discount_percent > 100) or (self.discount_price < self.start_price):
                self.make_item_disable(self)
                raise ActivationError(get_activation_warning_msg('درصد تخفیف'))
            if self.disable is True and self.priority == '0':
                self.make_item_disable(self)
                raise ActivationError(get_activation_warning_msg('انبار پیش فرض'))
            if self.deadline:
                if self.deadline < timezone.now() and self.deadline is not None and self.disable is False:
                    self.make_item_disable(self)
                    raise ActivationError(get_activation_warning_msg('ددلاین'))
            if (not self.dimensions.get('width') or not self.dimensions.get('height') or not self.dimensions.get(
                    'length') or not self.dimensions.get('weight')) and self.product.type in [2,
                                                                                              5]:  # product, package_item
                self.make_item_disable(self, warning=False)
                raise ActivationError(get_activation_warning_msg('ابعاد'))
        else:
            self.required_fields = ['dimensions']
            items = self.items.filter(Q(disable=True) | Q(available_count_for_sale=0))
            if items.exists():
                self.make_item_disable(self)
                raise ActivationError(get_activation_warning_msg(f'انبار: {items[0]}'))
            super().clean()

    def __str__(self):
        return f"{self.product}"

    def pre_process(self, my_dict, box_id=None):
        [my_dict.pop(field, None) for field in self.remove_fields]
        if type(my_dict.get('start_time')) is int or type(my_dict.get('start_time')) is float:
            my_dict['start_time'] = timestamp_to_datetime(my_dict['start_time'])
        if type(my_dict.get('deadline', None)) is int or type(my_dict.get('deadline')) is float:
            my_dict['deadline'] = timestamp_to_datetime(my_dict['deadline'])
        if not my_dict.get('deadline', None):
            my_dict['deadline'] = None
        if type(my_dict.get('tax_type')) is str:
            my_dict['tax_type'] = {'has_not': 1, 'from_total_price': 2, 'from_profit': 3}[my_dict['tax_type']]
        if my_dict.get('discount_price'):
            my_dict['discount_percent'] = int(100 - int(my_dict['discount_price']) / int(my_dict['final_price']) * 100)
            if my_dict['discount_percent'] < 0:
                raise ValidationError(_('تخفیف داری میدی؟ درصد تخفیف منفیه ک!'))
        if my_dict.get('features', None) and not my_dict.get('features_percent', None):
            # todo debug
            # todo feature: add default_selected_value for feature
            pass
            # raise ValidationError('درصد ویژگی ها نامعتبر است')

        if my_dict.get('priority', None) == 0 and my_dict.get('disable', None):
            my_dict['manage'] = True
        no_profit_boxes = [14]  # home jobs
        # todo free post recommended profit
        # if my_dict.get('discount_price', None) and box_id not in no_profit_boxes:
        #     recommended_profit = 1.15
        #     tax_factor = 1
        #     if my_dict.get('tax_type', self.tax_type) == 2:
        #         tax_factor = 1.09
        #     recommended_price = ceil(my_dict.get('start_price', self.start_price) * recommended_profit * tax_factor)
        #     if recommended_price > my_dict.get('discount_price'):
        #         raise ValidationError(_(f'قیمت فروش باید بیشتر از {recommended_price} باشد'))
        return my_dict

    def post_process(self, my_dict):
        if my_dict is None:
            return True
        ds = getattr(self.product, 'default_storage', None)
        if self.product.manage or getattr(ds, 'available_count_for_sale', 0) < 1 \
                or getattr(ds, 'disable', None) is True or getattr(ds, 'unavailable', None) is True:
            self.product.assign_default_value()
        if my_dict.get('vip_prices', None):
            self.vip_prices.clear()
            dper = int(100 - (my_dict.get('discount_price') or self.discount_price) / (
                    my_dict.get('final_price') or self.final_price) * 100)
            vip_prices = [VipPrice(vip_type_id=item['vip_type_id'], discount_price=item['discount_price'],
                                   max_count_for_sale=item.get('max_count_for_sale', self.max_count_for_sale),
                                   discount_percent=dper,
                                   available_count_for_sale=item.get('available_count_for_sale',
                                                                     self.available_count_for_sale), storage_id=self.pk)
                          for item in
                          my_dict.get('vip_prices')]
            VipPrice.objects.bulk_create(vip_prices)
        if self.product.type == 4 and my_dict:  # package
            # {'is_package': True, 'items': [{'package_item_id':1, 'count': 5}, {'package_item_id':2, 'count': 10}]}
            self.items.clear()
            user = self.created_by
            package_items = [Package(**item, created_by=user, updated_by=user, package=self) for item in
                             my_dict.get('items')]
            Package.objects.bulk_create(package_items)
            self.discount_price = 0
            self.final_price = 0
            self.start_price = 0
            self.dimensions = {"width": 0, "height": 0, "length": 0, "weight": 0}
            for package_item in package_items:
                self.discount_price += package_item.package_item.discount_price * package_item.count
                self.start_price += package_item.package_item.start_price * package_item.count
                self.final_price += package_item.package_item.final_price * package_item.count
                self.dimensions = {"width": self.dimensions['width'] + package_item.package_item.dimensions['width'],
                                   "height": self.dimensions['height'] + package_item.package_item.dimensions['height'],
                                   "length": self.dimensions['length'] + package_item.package_item.dimensions['length'],
                                   "weight": self.dimensions['weight'] + package_item.package_item.dimensions['weight']}
            self.discount_percent = int(100 - self.discount_price / self.final_price * 100)
            try:
                self.supplier = package_items[0].package_item.supplier
            except Exception as e:
                print(e)
            self.save()

    def update_price(self):
        packages = list(self.packages.all().order_by('package_id').distinct('package_id')) + \
                   list(self.related_packages.all().order_by('package_id').distinct('package_id'))
        for package in packages:
            package = package.package
            package_records = Package.objects.filter(package=package)
            package.discount_price = 0
            package.final_price = 0
            for package_record in package_records:
                package.discount_price += package_record.package_item.discount_price * package_record.count
                package.final_price += package_record.package_item.final_price * package_record.count
            package.available_count_for_sale = min(
                package_records.all().values_list('package_item__available_count_for_sale', flat=True))
            package.available_count = min(
                package_records.all().values_list('package_item__available_count', flat=True))
            package.discount_percent = int(100 - package.discount_price / package.final_price * 100)
            package.save()

    def save(self, *args, **kwargs):
        admin = kwargs.get('admin', None)
        if admin:
            self.__dict__ = self.pre_process(self.__dict__, self.product.box_id)
            self.priority = Product.objects.filter(pk=self.product_id).count() - 1
        super().save()
        if admin:
            self.post_process(kwargs)

    def get_max_count(self):
        if (self.available_count_for_sale >= self.max_count_for_sale) and (self.max_count_for_sale != 0):
            return self.max_count_for_sale
        if self.available_count_for_sale > 1:
            return self.available_count_for_sale - 1
        return self.available_count_for_sale

    def is_available(self, count=1):
        max_count_for_sale = self.get_max_count()
        return self.available_count_for_sale >= count and max_count_for_sale >= count and \
               self.disable is False and self.product.disable is False

    product = models.ForeignKey(Product, on_delete=CASCADE, related_name='storages')
    # features = models.ManyToManyField(ProductFeature, through='StorageFeature', related_name="storages")
    features = models.ManyToManyField(ProductFeature, through='ProductFeatureStorage', related_name="storages")
    accessories = models.ManyToManyField("self", through='StorageAccessories', symmetrical=False,
                                         related_name="accessory_storages")
    items = models.ManyToManyField("self", through='Package', symmetrical=False, related_name="item_storages")
    features_percent = models.PositiveSmallIntegerField(default=0)
    available_count = models.PositiveIntegerField(default=0)
    sold_count = models.IntegerField(default=0)
    start_price = models.PositiveIntegerField(default=0)
    qty = models.CharField(max_length=255, null=True, blank=True, help_text="quantity")
    sku = models.CharField(max_length=255, null=True, blank=True, help_text="stock keeping unit")
    final_price = models.PositiveIntegerField(default=0)
    discount_price = models.PositiveIntegerField(default=0)
    shipping_cost = models.PositiveIntegerField(blank=True, null=True)
    booking_cost = models.PositiveIntegerField(default=0, blank=True)
    least_booking_time = models.PositiveIntegerField(default=48, blank=True)
    available_count_for_sale = models.PositiveIntegerField(default=0, verbose_name='Available count for sale')
    max_count_for_sale = models.PositiveSmallIntegerField(default=1)
    min_count_alert = models.PositiveSmallIntegerField(default=3)
    priority = models.PositiveSmallIntegerField(default=0)
    tax_type = models.PositiveSmallIntegerField(default=0, choices=tax_types)
    tax = models.PositiveIntegerField(default=0)
    discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Discount price percent')
    package_discount_price = models.PositiveSmallIntegerField(default=0)
    gender = models.BooleanField(blank=True, null=True)
    disable = models.BooleanField(default=True)
    unavailable = models.BooleanField(default=False)
    deadline = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    title = JSONField(default=multilanguage)
    # search = SearchVectorField(null=True)
    supplier = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True, related_name="products")
    invoice_description = JSONField(default=multilanguage)
    invoice_title = JSONField(default=multilanguage)
    vip_types = models.ManyToManyField(VipType, through='VipPrice', related_name="storages")
    dimensions = JSONField(help_text="{'weight': '', 'height': '', 'width': '', 'length': ''}",
                           validators=[validate_vip_price], default=dict, blank=True)
    max_shipping_time = models.PositiveIntegerField(default=0)
    settings = JSONField(default=dict, blank=True)
    media = models.ForeignKey(Media, on_delete=SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'storage'
        # ordering = ['-id']
        indexes = [BTreeIndex(fields=['deadline'])]


class Basket(Base):
    select = ['user'] + Base.select
    sync_levels = [(0, 'ready'), (1, 'reserved'), (2, 'canceled'), (3, 'done')]

    def __str__(self):
        return f"{self.user}"

    user = models.ForeignKey(User, on_delete=CASCADE, null=True, blank=True, related_name="baskets")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    count = models.PositiveIntegerField(default=0)
    products = models.ManyToManyField(Storage, through='BasketProduct', through_fields=('basket',
                                                                                        'storage'), symmetrical=False)
    description = models.TextField(blank=True, null=True)
    # active = models.BooleanField(default=True)
    sync = models.PositiveSmallIntegerField(choices=sync_levels, default=0)

    class Meta:
        db_table = 'basket'


class BasketProduct(MyModel):
    related = ['storage']
    select = ['storage', 'basket', 'vip_price', 'box'] + MyModel.select

    def __str__(self):
        return f"{self.id}"

    def validation(self):
        pass

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    storage = models.ForeignKey(Storage, on_delete=CASCADE, db_index=False, related_name="basket_products")
    # parent = models.ForeignKey("self", on_delete=CASCADE, db_index=False, related_name="accessories",
    #                            null=True, blank=True)
    accessory = models.ForeignKey(StorageAccessories, on_delete=CASCADE, db_index=False,
                                  related_name="basket_accessories",
                                  null=True, blank=True)
    # accessories = ArrayField(models.IntegerField(), size=5, default=list)
    basket = models.ForeignKey(Basket, on_delete=CASCADE, null=True, blank=True, related_name="basket_storages",
                               db_index=False)
    count = models.PositiveIntegerField(default=1)
    box = models.ForeignKey(Box, on_delete=PROTECT)
    features = JSONField(default=dict, help_text="{'name': 'feature name', 'value': 'feature value'}")
    vip_price = models.ForeignKey(to=VipPrice, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'basket_product'
        indexes = [BTreeIndex(fields=['basket', 'storage', 'accessory'])]
        unique_together = ('basket', 'storage', 'accessory')


class Blog(Base):
    select = ['box', 'media'] + Base.select

    def __str__(self):
        return self.title

    box = models.ForeignKey(Box, on_delete=CASCADE)
    title = JSONField(default=multilanguage)
    description = JSONField(null=True, blank=True)
    media = models.ForeignKey(Media, on_delete=CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'blog'


class BlogPost(Base):
    objects = MyQuerySet.as_manager()
    select = ['blog', 'media'] + Base.select

    def __str__(self):
        return self.permalink

    blog = models.ForeignKey(Blog, on_delete=CASCADE, blank=True, null=True)
    body = JSONField(blank=True, null=True)
    permalink = models.CharField(max_length=255, db_index=True, unique=True)
    media = models.ForeignKey(Media, on_delete=CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'blog_post'


class Comment(Base):
    select = ['user', 'reply_to', 'product', 'blog_post'] + Base.select
    types = [(1, 'q-a'), (2, 'rate')]
    choices = ('type',)

    def __str__(self):
        return f"{self.user}"

    def validation(self):
        try:
            if self.rate > 10 or self.type < 2:
                raise ValidationError(_('امتیاز باید بین 1 تا 10 باشد'))
        except TypeError:
            pass

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    _safedelete_policy = SOFT_DELETE_CASCADE
    text = models.TextField(null=True, blank=True)
    rate = models.PositiveSmallIntegerField(null=True, blank=True)
    satisfied = models.BooleanField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=CASCADE)
    reply_to = models.ForeignKey('self', on_delete=CASCADE, blank=True, null=True, related_name="replys")
    suspend = models.BooleanField(default=False)
    type = models.PositiveSmallIntegerField(choices=types)
    product = models.ForeignKey(Product, on_delete=CASCADE, null=True, blank=True, related_name="reviews")
    blog_post = models.ForeignKey(BlogPost, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'comments'


class Invoice(Base):
    objects = MyQuerySet.as_manager()
    select = ['basket', 'suspended_by', 'user', 'charity', 'post_invoice'] + Base.select
    statuss = ((1, 'pending'), (2, 'payed'), (3, 'canceled'), (4, 'rejected'), (5, 'sent'), (6, 'ready'))
    choices = ('status',)

    success_status = [2, 5, 6]

    def __str__(self):
        return f"{self.user}"

    def pre_process(self, my_dict):  # only for update
        if type(my_dict.get('status', None)) is str:
            try:
                my_dict['status'] = {'payed': 2, 'sent': 5, 'ready': 6}[my_dict['status']]
            except KeyError:
                pass
        return my_dict

    suspended_at = models.DateTimeField(blank=True, null=True, verbose_name='Suspended at')
    suspended_by = models.ForeignKey(User, on_delete=CASCADE, blank=True, null=True, verbose_name='Suspended by',
                                     related_name='invoice_suspended_by')
    cancel_at = models.DateTimeField(null=True, blank=True)
    cancel_by = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True, related_name='booking_cancel_by')
    reject_at = models.DateTimeField(null=True, blank=True)
    reject_by = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True, related_name='booking_reject_by')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True,
                                     related_name='booking_confirmation')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    user = models.ForeignKey(User, on_delete=CASCADE, related_name='invoices')
    sync_task = models.ForeignKey(PeriodicTask, on_delete=CASCADE, null=True, blank=True,
                                  related_name='invoice_sync_task')
    email_task = models.ForeignKey(PeriodicTask, on_delete=CASCADE, null=True, blank=True)
    basket = models.ForeignKey(to=Basket, on_delete=CASCADE, related_name='invoice', null=True)
    storages = models.ManyToManyField(Storage, through='InvoiceStorage')
    payed_at = models.DateTimeField(blank=True, null=True, verbose_name='Payed at')
    special_offer_id = models.BigIntegerField(blank=True, null=True, verbose_name='Special offer id')
    address = JSONField(null=True, blank=True)
    description = models.TextField(max_length=255, blank=True, null=True)
    amount = models.PositiveIntegerField()
    invoice_discount = models.PositiveIntegerField(null=True, blank=True)
    final_price = models.PositiveIntegerField(null=True, blank=True)
    reference_id = models.CharField(max_length=127, null=True, blank=True)
    sale_order_id = models.BigIntegerField(null=True, blank=True)
    ipg_res_code = models.PositiveIntegerField(null=True, blank=True)
    sale_reference_id = models.BigIntegerField(null=True, blank=True)
    card_holder = models.CharField(max_length=31, null=True, blank=True)
    final_amount = models.PositiveIntegerField(help_text='from bank', null=True, blank=True)
    # mt_profit = models.PositiveIntegerField(null=True, blank=True)
    # charity = models.PositiveIntegerField(null=True, blank=True)
    ipg = models.PositiveSmallIntegerField(default=1)
    expire = models.DateTimeField(default=next_half_hour)
    status = models.PositiveSmallIntegerField(default=1, choices=statuss)
    max_shipping_time = models.IntegerField(default=0)
    suppliers = models.ManyToManyField(User, through="InvoiceSuppliers", related_name='invoice_supplier')
    post_tracking_code = models.CharField(max_length=255, null=True, blank=True)
    post_invoice = models.ForeignKey("Invoice", on_delete=CASCADE, related_name='main_invoice', null=True, blank=True)
    charity = models.ForeignKey(Charity, on_delete=PROTECT, null=True, blank=True)
    details = JSONField(default=dict, help_text="{sender: ali, cart_postal_text: with love}")

    class Meta:
        db_table = 'invoice'
        indexes = [BTreeIndex(fields=['payed_at']), BTreeIndex(fields=['created_at']), BTreeIndex(fields=['expire'])]


class PaymentHistory(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.BigAutoField(auto_created=True, primary_key=True)
    description = models.TextField()
    reference_id = models.CharField(max_length=31)
    status = models.BooleanField(default=0)
    amount = models.PositiveIntegerField()
    invoice = models.ForeignKey(Invoice, on_delete=PROTECT, related_name="histories")
    created_at = models.DateTimeField(auto_now_add=True)


# todo disable value_added type (half)
# todo remove
class InvoiceSuppliers(MyModel):
    select = ['invoice', 'supplier'] + MyModel.select
    invoice = models.ForeignKey(Invoice, on_delete=CASCADE, db_index=False)
    supplier = models.ForeignKey(User, on_delete=CASCADE, db_index=False)
    amount = models.PositiveIntegerField()

    class Meta:
        db_table = 'supplier_invoice'
        indexes = [BTreeIndex(fields=['invoice', 'supplier'])]


class InvoiceStorage(Base):
    objects = MyQuerySet.as_manager()
    select = ['box', 'storage', 'invoice'] + Base.select
    table_select = ['storage', 'storage__product', 'invoice__user', 'invoice', 'storage__product__thumbnail',
                    'storage__supplier']
    table_prefetch = []
    prefetch = []

    def pre_process(self, my_dict):
        if my_dict.get('deliver_status'):
            try:
                my_dict['deliver_status'] = {'pending': 1, 'packing': 2, 'sending': 3, 'delivered': 4, 'referred': 5}[
                    my_dict['deliver_status']]
            except KeyError:
                pass
        return my_dict

    def post_process(self, my_dict):
        pass

    def save(self, *args, **kwargs):
        self.pre_process(self.__dict__)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.storage}"

    id = models.BigAutoField(auto_created=True, primary_key=True)
    key = models.CharField(max_length=31, unique=True, null=True, db_index=False)
    filename = models.CharField(max_length=255, null=True, blank=True)
    box = models.ForeignKey(Box, on_delete=PROTECT)
    tax = models.PositiveIntegerField(default=0)
    dev = models.PositiveIntegerField()
    admin = models.PositiveIntegerField()
    mt_profit = models.PositiveIntegerField()
    charity = models.PositiveIntegerField()
    # todo protect
    storage = models.ForeignKey(Storage, on_delete=CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=CASCADE, related_name='invoice_storages')
    count = models.PositiveIntegerField(default=1)
    final_price = models.PositiveIntegerField()
    total_price = models.PositiveIntegerField()
    start_price = models.PositiveIntegerField()
    discount = models.PositiveIntegerField()
    discount_price = models.PositiveIntegerField()
    discount_price_without_tax = models.PositiveIntegerField()
    # vip_discount_price = models.PositiveIntegerField(null=True, blank=True)
    deliver_status = models.PositiveSmallIntegerField(choices=deliver_status, default=1)
    details = JSONField(null=True, help_text="package/storage/product details")
    features = JSONField(default=list)

    # stodo change to invoice_storage
    class Meta:
        db_table = 'invoice_product'
        indexes = [HashIndex(fields=['key'])]


class DiscountCode(Base):
    types = [(1, 'product'), (2, 'basket'), (3, 'post')]
    choices = ('type',)

    select = ['storage', 'qr_code', 'invoice'] + Base.select
    storage = models.ForeignKey(Storage, on_delete=CASCADE, related_name='discount_code', null=True, blank=True)
    basket = models.ForeignKey(Basket, on_delete=CASCADE, related_name='discount_code', null=True, blank=True)
    qr_code = models.ForeignKey(Media, on_delete=PROTECT, null=True, blank=True)
    invoice = models.ForeignKey(Invoice, on_delete=CASCADE, related_name='discount_codes', null=True, blank=True)
    invoice_storage = models.ForeignKey(InvoiceStorage, on_delete=CASCADE, related_name='discount_code', null=True,
                                        blank=True)
    code = models.CharField(max_length=32)
    type = models.PositiveSmallIntegerField(choices=types, default=1)

    class Meta:
        db_table = 'discount_code'


class Menu(Base):
    select = ['media', 'parent', 'box'] + Base.select
    types = ((1, 'home'),)
    choices = ('type',)

    def __str__(self):
        return f"{self.name['fa']}"

    type = models.PositiveSmallIntegerField(choices=types)
    name = JSONField(default=multilanguage)
    media = models.ForeignKey(Media, on_delete=PROTECT, blank=True, null=True)
    url = models.CharField(max_length=25, null=True, blank=True)
    parent = models.ForeignKey("self", on_delete=CASCADE, null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=0)
    box = models.ForeignKey(Box, on_delete=PROTECT, null=True, blank=True)

    class Meta:
        db_table = 'menu'


class Rate(MyModel):
    select = ['user', 'storage'] + Base.select

    def __str__(self):
        return f"{self.rate}"

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    user = models.ForeignKey(User, on_delete=CASCADE)
    rate = models.FloatField()
    storage = models.ForeignKey(Storage, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'rate'


class Slider(Base):
    select = ['media', 'mobile_media', 'product'] + Base.select
    required_fields = ['title', 'media', 'mobile_media', 'type']
    required_multi_lang = ['title']
    fields = {'title': 'عنوان', 'media': 'تصویر', 'mobile_media': 'تصویر موبایل', 'type': 'نوع'}

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args)

    def __str__(self):
        return f"{self.title['fa']}"

    title = JSONField(default=multilanguage)
    product = models.ForeignKey(Product, on_delete=CASCADE, blank=True, null=True)
    media = models.ForeignKey(Media, on_delete=CASCADE, related_name='slider')
    mobile_media = models.ForeignKey(Media, on_delete=CASCADE, related_name='slider_mobile')
    type = models.CharField(default='home', max_length=255)
    url = models.URLField(null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=0, null=True, blank=True, help_text="need null value")

    class Meta:
        db_table = 'slider'


class SpecialOffer(Base):
    select = ['media', 'category', 'media'] + Base.select
    prefetch = ['user', 'product', 'not_accepted_products'] + Base.prefetch

    def __str__(self):
        return f"{self.name['fa']}"

    def validation(self):
        if self.discount_percent > 100 or self.vip_discount_percent > 100:
            raise ValidationError(_("درصد باید کوچکتر از 100 باشد"))

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    box = models.ForeignKey(Box, on_delete=CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=CASCADE, null=True, blank=True)
    media = models.ForeignKey(Media, on_delete=CASCADE)
    user = models.ManyToManyField(User, blank=True)
    product = models.ManyToManyField(Storage, related_name="special_offer_products", blank=True)
    not_accepted_products = models.ManyToManyField(Storage, related_name="special_offer_not_accepted_products",
                                                   blank=True)
    peak_price = models.PositiveIntegerField(verbose_name='Peak price', null=True, blank=True)
    discount_price = models.PositiveIntegerField(default=0, verbose_name='Discount price')
    vip_discount_price = models.PositiveIntegerField(default=0, verbose_name='Vip discount price')
    least_count = models.PositiveSmallIntegerField(default=1)
    discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Discount percent')
    vip_discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Vip discount percent')
    code = models.CharField(max_length=65, null=True, blank=True)
    start_date = models.DateTimeField(verbose_name='Start date', null=True, blank=True)
    end_date = models.DateTimeField(verbose_name='End date', null=True, blank=True)
    name = JSONField(default=multilanguage)

    class Meta:
        db_table = 'special_offer'


class SpecialProduct(Base):
    select = ['storage', 'thumbnail'] + Base.select
    filter = {"disable": False}

    required_fields = ['storage', 'box']
    related_fields = []
    remove_fields = []
    m2m = []
    required_m2m = []
    fields = {'مدیا'}

    def __str__(self):
        return f"{self.storage}"

    def save(self, *args, **kwargs):
        storage = self.storage
        storage.clean()
        print(self.storage.disable)
        if storage.disable and not self.deleted_by:
            raise ActivationError('اول باید انبار رو فعال کنی')
        super().save(*args)
        if self.deleted_by:
            return {'variant': 'warning',
                    'message': 'محصول ویژه این انبار غیرفعال شد :)'}

    storage = models.ForeignKey(Storage, on_delete=CASCADE, null=True, blank=True, related_name='special_products')
    thumbnail = models.ForeignKey(Media, on_delete=PROTECT, related_name='special_product_thumbnail', null=True,
                                  blank=True)
    box = models.ForeignKey(Box, on_delete=PROTECT, null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    name = JSONField(null=True, blank=True)

    class Meta:
        db_table = 'special_products'


class URL(models.Model):
    def __str__(self):
        return f"{self.shortlink}"

    url = models.URLField()
    shortlink = models.CharField(max_length=7, unique=True)

    class Meta:
        db_table = 'url'


class WishList(Base):
    select = ['user', 'product'] + Base.select

    def __str__(self):
        return f"{self.user}"

    user = models.ForeignKey(User, on_delete=CASCADE)
    # type = models.CharField(max_length=255, )
    notify = models.BooleanField(default=False)
    wish = models.BooleanField(default=True)
    product = models.ForeignKey(Product, on_delete=CASCADE, related_name='wishlists')

    class Meta:
        db_table = 'wishList'


class NotifyUser(MyModel):
    select = ['user', 'category'] + MyModel.select

    def __str__(self):
        return f"{self.user}"

    user = models.ForeignKey(User, on_delete=CASCADE)
    type = models.PositiveSmallIntegerField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=CASCADE)
    box = models.ForeignKey(Box, on_delete=CASCADE)

    class Meta:
        db_table = 'notify_user'


# ---------- Tourism ---------- #

class ResidenceType(Base):
    class Meta:
        db_table = 'residence_type'

    def __str__(self):
        return self.name['fa']

    name = JSONField(default=multilanguage)


class HousePrice(Base):
    def __str__(self):
        return f'{self.weekday}'

    def validation(self):
        if self.weekly_discount_percent > 100 or self.monthly_discount_percent > 100:
            raise ValidationError(_("درصد باید کوچکتر از 100 باشد"))

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    guest = models.PositiveIntegerField(default=0)
    eyd = models.PositiveIntegerField(default=0)
    weekend = models.PositiveIntegerField(default=0)
    weekday = models.PositiveIntegerField(default=0)
    peak = models.PositiveIntegerField(default=0)
    weekly_discount_percent = models.PositiveSmallIntegerField(default=0)
    monthly_discount_percent = models.PositiveSmallIntegerField(default=0)
    custom_price = JSONField(default=dict)

    class Meta:
        db_table = 'house_price'


class House(Base):
    select = ['product', 'price'] + Base.select
    prefetch = ['residence_type'] + Base.prefetch

    def __str__(self):
        return self.product.name['fa']

    cancel_rules = JSONField(default=multilanguage, blank=True)
    rules = JSONField(default=multilanguage, blank=True)
    product = models.OneToOneField(Product, on_delete=PROTECT)
    owner = models.ForeignKey(User, on_delete=CASCADE)
    state = models.ForeignKey(State, on_delete=PROTECT)
    city = models.ForeignKey(City, on_delete=PROTECT)
    price = models.OneToOneField(HousePrice, on_delete=PROTECT, null=True)
    facilities = JSONField(blank=True)
    meals = JSONField(default=default_meals)
    capacity = JSONField()
    residence_type = models.ManyToManyField(ResidenceType)
    rent_type = JSONField(default=multilanguage, blank=True)
    residence_area = JSONField(default=multilanguage, blank=True)
    bedroom = JSONField(blank=True)  # rooms, shared space, rakhte khab, description, ...
    safety = JSONField(blank=True)
    calender = JSONField(blank=True)
    notify_before_arrival = models.PositiveSmallIntegerField(default=0)  # days number
    future_booking_time = models.PositiveSmallIntegerField(default=7)  # future days with reserve availability
    max_guest = models.PositiveSmallIntegerField()

    class Meta:
        db_table = 'house'


class Booking(Base):
    select = ['user', 'house', 'product', 'invoice', 'confirmation_by', 'cancel_by', 'reject_by'] + Base.select
    types = Product.booking_types
    statuss = [(1, 'pending'), (2, 'sent'), (3, 'deliver'), (4, 'reject')]
    choices = ('statuss', 'types')

    def __str__(self):
        return f"{self.house}"

    type = models.PositiveSmallIntegerField(choices=types)
    location = JSONField(null=True)
    least_reserve_time = models.PositiveSmallIntegerField(default=5)
    people_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'book'


class Holiday(MyModel):

    def __str__(self):
        return self.occasion

    day_off = models.BooleanField(default=False)
    occasion = models.TextField(blank=True)
    date = models.DateField()

    class Meta:
        db_table = 'holiday'


# ---------- Proxy Models ---------- #
class Supplier(User):
    class Meta:
        proxy = True


@receiver(post_softdelete, sender=Media)
def submission_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(False)


m2m_footprint_required = [FeatureValue, ProductFeature]
append_on_priority = [FeatureValue]
