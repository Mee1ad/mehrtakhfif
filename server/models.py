import os
from PIL import Image
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField, ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import *
from django.db import models
from django.db.models import CASCADE, PROTECT, SET_NULL, Q, F
from django.db.utils import IntegrityError
from safedelete.signals import post_softdelete
from django.dispatch import receiver
from django.utils import timezone
from push_notifications.models import GCMDevice
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE, NO_DELETE
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult
from mehr_takhfif.settings import HOST, MEDIA_ROOT
import datetime
import pysnooper
from PIL import Image, ImageFilter
from safedelete.managers import SafeDeleteQueryset
from safedelete.config import DELETED_INVISIBLE
from operator import attrgetter
import pytz
from server.field_validation import *
from mtadmin.exception import *
from random import randint
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import FieldDoesNotExist
from push_notifications.models import APNSDevice, GCMDevice

product_types = [(1, 'service'), (2, 'product'), (3, 'tourism'), (4, 'package'), (5, 'package_item')]
deliver_status = [(1, 'pending'), (2, 'packing'), (3, 'sending'), (4, 'delivered'), (5, 'referred')]


def get_activation_warning_msg(field_name):
    messages = ['آیتم غیرفعال شد. ' + f'{field_name} مشکل داره']
    index = randint(0, 0)
    return messages[index]


def multilanguage():
    return {"fa": "",
            "en": "",
            "ar": ""}


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
    if instance.type in Media.has_placeholder:
        time = f'{time}-has-ph'
    # file_type = re.search('\\w+', instance.type)[0]
    file_format = os.path.splitext(instance.image.name)[-1]
    # todo make it with box name
    return f'boxes/{instance.box_id}/{date}/{instance.get_type_display()}/{time}{file_format}'


def reduce_image_quality(img):
    with Image.open(img) as img:
        x, y = img.size
        width = (60 / x)
        height = int((y * width))
        ph = img.resize((60, height), Image.ANTIALIAS)
        ph = ph.filter(ImageFilter.GaussianBlur(1.6))
    return ph


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
        [kwargs.pop(item, None) for item in remove_list]
        is_updated = super().update(**kwargs)
        if model == 'storage' and self:
            storage = self.first()
            storage.update_price()
            if kwargs.get('disable') is True:
                if storage.product.storages.count() <= 1:
                    storage.product.disable = True
                # storage.related_packages.update(package__disable=True)
                storage.cascade_disabling(storage, warning)

        elif model == 'product':
            product = self.first()
            storages = product.storages.all()
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
        features = Feature.objects.filter(pk__in=kwargs.get('features', []))
        category.feature_set.clear()
        category.feature_set.add(*features)
        return kwargs

    def storage_validation(self, **kwargs):
        # for storage and invoice_storage
        storage = self.first()
        kwargs = storage.pre_process(kwargs)
        storage.post_process(kwargs.get('remove_fields', None))
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

    @pysnooper.snoop()
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
        if warning:
            raise WarningMessage('آیا میدانستی: محصولات ویژه و پکیج هایی که شامل این انبار بودن هم غیرفعال میشن؟! 🤭')


class MyModel(models.Model):
    class Meta:
        abstract = True

    id = models.BigAutoField(auto_created=True, primary_key=True)
    # select = []
    # prefetch = []
    # related = []
    # filter = {}
    # serializer_exclude = ()
    # required_fields = []
    # required_multi_lang = []
    # related_fields = []
    # m2m = []
    # remove_fields = []
    # custom_m2m = {}
    # ordered_m2m = {}
    # required_m2m = []
    # fields = {}


class Ad(Base):
    select = ['media', 'storage']
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
    priority = models.PositiveSmallIntegerField(null=True, blank=True)
    media = models.ForeignKey("Media", on_delete=PROTECT, related_name='ad')
    mobile_media = models.ForeignKey("Media", on_delete=PROTECT, null=True, blank=True, related_name='ad_mobile')
    storage = models.ForeignKey("Storage", on_delete=PROTECT, blank=True, null=True)
    type = models.CharField(default='home', max_length=255)

    class Meta:
        db_table = 'ad'
        ordering = ['-id']


class User(AbstractUser):
    select = []
    prefetch = []
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

    first_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='First name')
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Last name')
    username = models.CharField(max_length=150, unique=True)
    phone = models.CharField(max_length=150, null=True, blank=True)
    language = models.CharField(max_length=7, default='fa')
    email = models.CharField(max_length=255, blank=True, null=True, validators=[validate_email])
    password = models.CharField(max_length=255, blank=True, null=True)
    gender = models.BooleanField(blank=True, null=True)  # True: man, False: woman
    updated_at = models.DateTimeField(blank=True, auto_now=True, verbose_name='Updated at')
    is_ban = models.BooleanField(default=False)
    shaba = models.CharField(max_length=255, null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False, verbose_name='Phone verified')
    is_superuser = models.BooleanField(default=False, verbose_name='Superuser')
    is_staff = models.BooleanField(default=False, verbose_name='Staff')
    is_supplier = models.BooleanField(default=False)
    is_verify = models.BooleanField(default=False)
    privacy_agreement = models.BooleanField(default=False)
    deposit_id = models.PositiveSmallIntegerField(null=True, blank=True)
    default_address = models.OneToOneField(to="Address", on_delete=SET_NULL, null=True, blank=True,
                                           related_name="user_default_address")
    vip_types = models.ManyToManyField(to="VipType", related_name="users")
    box_permission = models.ManyToManyField("Box", blank=True)
    email_verified = models.BooleanField(default=False, verbose_name='Email verified')
    subscribe = models.BooleanField(default=True)
    avatar = models.PositiveSmallIntegerField(null=True, blank=True)
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

    class Meta:
        db_table = 'user'
        ordering = ['-id']


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
        return self.name

    name = JSONField()
    media = models.CharField(max_length=255)

    class Meta:
        db_table = 'vip_type'
        ordering = ['-id']


class Client(MyModel):
    device_id = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    last_login_ip = models.CharField(max_length=31, null=True, blank=True)
    gcm_device = models.ForeignKey(GCMDevice, on_delete=CASCADE, related_name="client")

    class Meta:
        db_table = 'client'
        ordering = ['-id']


class State(MyModel):
    def __str__(self):
        return self.name

    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'state'
        ordering = ['-id']


class City(MyModel):
    def __str__(self):
        return self.name

    name = models.CharField(max_length=255)
    state = models.ForeignKey(State, on_delete=CASCADE)

    class Meta:
        db_table = 'city'
        ordering = ['-id']


class Address(MyModel):
    """
        Stores a single blog entry, related to :model:`auth.User` and
        :model:`server.Address`.
    """

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

    class Meta:
        db_table = 'address'
        ordering = ['-id']


class Box(Base):
    def __str__(self):
        return self.name['fa']

    name = JSONField(default=multilanguage)
    permalink = models.CharField(max_length=255, db_index=True, unique=True)
    owner = models.OneToOneField(User, on_delete=PROTECT)
    settings = JSONField(default=dict, blank=True)
    disable = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(default=0)
    media = models.ForeignKey("Media", on_delete=CASCADE, null=True, blank=True, related_name="box_image_box_id")

    class Meta:
        db_table = 'box'
        ordering = ['-id']
        permissions = [("has_access", "Can manage that box")]


class Media(Base):
    media_types = [(1, 'image'), (2, 'thumbnail'), (3, 'media'), (4, 'slider'), (5, 'ads'), (6, 'mobile_ads'),
                   (7, 'category'), (8, 'mobile_slider'), (100, 'video'), (200, 'audio')]
    no_box_type = [4, 5, 6, 8]
    media_sizes = {'thumbnail': (600, 372), 'media': (1280, 794), 'category': (800, 500), 'ads': (820, 300),
                   'mobile_ads': (500, 384), 'slider': (1920, 504), 'mobile_slider': (980, 860)}
    has_placeholder = [1, 2, 3, 4, 5]

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
                        print(width, height)
                        raise ValidationError(_('سایز عکس نامعتبر است'))
                except KeyError as e:
                    print(e)
        except ValueError:
            pass
        super().save(*args, **kwargs)
        if self.type in self.has_placeholder:
            ph = reduce_image_quality(self.image.path)
            name = self.image.name.replace('has-ph', 'ph')
            ph.save(f'{MEDIA_ROOT}/{name}', optimize=True, quality=80)

    image = models.FileField(upload_to=upload_to, null=True, blank=True)
    video = models.URLField(null=True, blank=True)
    audio = models.URLField(null=True, blank=True)
    title = JSONField(default=multilanguage)
    type = models.PositiveSmallIntegerField(choices=media_types)
    box = models.ForeignKey(Box, on_delete=models.CASCADE, null=True, blank=True, related_name="medias")

    class Meta:
        db_table = 'media'
        ordering = ['-id']


class Category(Base):
    objects = MyQuerySet.as_manager()
    prefetch = ['feature_set']
    serializer_exclude = ('box',)
    required_fields = []
    related_fields = []
    m2m = []
    required_m2m = []
    fields = {}

    def clean(self):
        if not self.products.all():
            self.make_item_disable(self)
            raise ActivationError(get_activation_warning_msg('محصولات'))
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

    parent = models.ForeignKey("self", on_delete=CASCADE, null=True, blank=True)
    box = models.ForeignKey(Box, on_delete=CASCADE)
    name = JSONField(default=multilanguage)
    permalink = models.CharField(max_length=255, db_index=True, unique=True, null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=0)
    disable = models.BooleanField(default=True)
    media = models.ForeignKey(Media, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'category'
        ordering = ['-id']
        indexes = [GinIndex(fields=['name'])]


class Feature(Base):
    objects = MyQuerySet.as_manager()

    def __str__(self):
        return f"{self.id}"

    def validation(self, kwargs):
        kwargs['type'] = {'bool': 1, 'single': 2, 'multi': 3}[kwargs.get('type', None)]
        if kwargs['type'] > 3:
            raise ValidationError(_('invalid type'))
        return kwargs

    def save(self, *args, **kwargs):
        self.validation(self.__dict__)
        super().save(*args, **kwargs)

    name = JSONField(default=multilanguage)
    type = models.PositiveSmallIntegerField(default=1, choices=((1, 'bool'), (2, 'single'), (3, 'multi')))
    value = JSONField(default=feature_value)
    # todo move manytomanyfield to category
    category = models.ManyToManyField(Category)
    box = models.ForeignKey(Box, on_delete=CASCADE, blank=True, null=True)
    icon = models.CharField(default='default', max_length=255)

    class Meta:
        db_table = 'feature'
        ordering = ['-id']


class Tag(Base):
    objects = MyQuerySet.as_manager()

    def __str__(self):
        return f"{self.name['fa']}"

    def validation(self, kwargs):
        permalink_validation(kwargs.get('permalink', 'pass'))
        name = kwargs['name']
        if Tag.objects.filter((Q(name__en=name['en']) & ~Q(name__en="") & ~Q(id=kwargs['id'])) |
                              (Q(name__fa=name['fa']) & ~Q(name__fa="") & ~Q(id=kwargs['id'])) |
                              (Q(name__ar=name['ar']) & ~Q(name__ar="") & ~Q(id=kwargs['id']))).count() > 0:
            raise IntegrityError("DETAIL:  Key (name)=() already exists.")
        return kwargs

    def save(self, *args, **kwargs):
        self.__dict__ = self.validation(self.__dict__)
        super().save(*args, **kwargs)

    permalink = models.CharField(max_length=255, db_index=True, unique=True)
    name = JSONField(default=multilanguage)

    class Meta:
        db_table = 'tag'
        ordering = ['-id']
        indexes = [GinIndex(fields=['name'])]


class TagGroupTag(MyModel):
    taggroup = models.ForeignKey("TagGroup", on_delete=PROTECT)
    tag = models.ForeignKey(Tag, on_delete=PROTECT)
    show = models.BooleanField(default=False)

    class Meta:
        db_table = 'tag_group_tags'
        ordering = ['-id']


class TagGroup(Base):
    # objects = MyQuerySet.as_manager()

    m2m = {'tags': TagGroupTag}

    def __str__(self):
        return f"{self.name['fa']}"

    box = models.ForeignKey(Box, on_delete=PROTECT)
    name = JSONField(default=multilanguage)
    tags = models.ManyToManyField(Tag, through="TagGroupTag", related_name='groups')

    class Meta:
        db_table = 'tag_group'
        ordering = ['-id']


class Brand(Base):
    objects = MyQuerySet.as_manager()

    def validation(self, kwargs):
        self.permalink = self.permalink.lower()
        name = kwargs['name']
        if Brand.objects.filter((Q(name__en=name['en']) & ~Q(name__en="") & ~Q(id=kwargs['id'])) |
                                (Q(name__fa=name['fa']) & ~Q(name__fa="") & ~Q(id=kwargs['id'])) |
                                (Q(name__ar=name['ar']) & ~Q(name__ar="") & ~Q(id=kwargs['id']))).count() > 0:
            raise IntegrityError("DETAIL:  Key (name)=() already exists.")
        return kwargs

    def save(self, *args, **kwargs):
        self.validation(self.__dict__)
        super().save(*args, **kwargs)

    name = JSONField(default=multilanguage)
    permalink = models.CharField(max_length=255, db_index=True, unique=True)

    class Meta:
        db_table = 'brand'
        ordering = ['-id']


class ProductTag(MyModel):
    product = models.ForeignKey("Product", on_delete=PROTECT)
    tag = models.ForeignKey(Tag, on_delete=PROTECT)
    show = models.BooleanField(default=False)

    class Meta:
        db_table = 'product_tag'
        ordering = ['-id']


class ProductMedia(MyModel):
    related = ['storage']

    def __str__(self):
        return f"{self.id}"

    product = models.ForeignKey("Product", on_delete=PROTECT)
    media = models.ForeignKey(Media, on_delete=PROTECT)
    priority = models.PositiveSmallIntegerField(null=True)

    class Meta:
        db_table = 'product_media'
        ordering = ['-id']


class Product(Base):
    objects = MyQuerySet.as_manager()
    select = ['category', 'box', 'thumbnail']
    prefetch = ['tags', 'media']
    filter = {"verify": True, "disable": False}

    required_fields = ['thumbnail', 'description']
    related_fields = []
    remove_fields = []
    custom_m2m = {'tags': ProductTag}
    ordered_m2m = {'media': ProductMedia}
    m2m = ['categories', 'cities', 'tag_groups']
    required_m2m = ['categories', 'media']
    fields = {'thumbnail': 'تامبنیل', 'categories': 'دسته بندی', 'tags': 'تگ', 'media': 'مدیا'}

    def pre_process(self, my_dict):
        if (self.review is not None) and (my_dict.get('review') != self.review):
            my_dict['check_review'] = False
        if my_dict.get('type'):
            try:
                my_dict['type'] = {'service': 1, 'product': 2, 'tourism': 3, 'package': 4, 'package_item': 5}[
                    my_dict['type']]
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
        if self.review is not None:
            self.make_item_disable(self)
            raise ActivationError('بنظر بهزاد، محصول اطلاعات صحیحی نداره!')
        # todo for now
        Product.objects.filter(pk=self.pk).update(verify=True)

    def assign_default_value(self):
        storages = self.storages.filter(available_count_for_sale__gt=0)
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
        return f"{self.name['fa']}"

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

    categories = models.ManyToManyField(Category, related_name="products")
    box = models.ForeignKey(Box, on_delete=PROTECT)
    brand = models.ForeignKey(Brand, on_delete=PROTECT, null=True, blank=True)
    thumbnail = models.ForeignKey(Media, on_delete=PROTECT, related_name='product_thumbnail', null=True, blank=True)
    cities = models.ManyToManyField(City)
    default_storage = models.OneToOneField(null=True, blank=True, to="Storage", on_delete=CASCADE,
                                           related_name='product_default_storage')
    tags = models.ManyToManyField(Tag, through="ProductTag", related_name='products')
    tag_groups = models.ManyToManyField(TagGroup, related_name='products')
    media = models.ManyToManyField(Media, through='ProductMedia')
    income = models.BigIntegerField(default=0)
    profit = models.PositiveIntegerField(default=0)
    rate = models.PositiveSmallIntegerField(default=0)
    disable = models.BooleanField(default=True)
    verify = models.BooleanField(default=False)
    manage = models.BooleanField(default=True)
    reservable = models.BooleanField(default=False)
    breakable = models.BooleanField(default=False)
    type = models.PositiveSmallIntegerField(choices=product_types, validators=[validate_product_type])
    permalink = models.CharField(max_length=255, db_index=True, unique=True)

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
    review = models.TextField(null=True, blank=True)
    check_review = models.BooleanField(default=False)

    # home_buissiness =
    # support_description =
    class Meta:
        db_table = 'product'
        ordering = ['-updated_at']


class FeatureStorage(MyModel):
    related = ['storage']

    def __str__(self):
        return f"{self.id}"

    feature = models.ForeignKey(Feature, on_delete=PROTECT)
    storage = models.ForeignKey("Storage", on_delete=PROTECT)
    value = JSONField(default=feature_value_storage)

    class Meta:
        db_table = 'feature_storage'
        ordering = ['-id']


class Package(Base):
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
        ordering = ['-id']


class VipPrice(MyModel):

    def __str__(self):
        return f"{self.storage.title['fa']}"

    vip_type = models.ForeignKey(VipType, on_delete=PROTECT)
    storage = models.ForeignKey("Storage", on_delete=PROTECT)
    discount_price = models.PositiveIntegerField()
    discount_percent = models.PositiveSmallIntegerField()
    max_count_for_sale = models.PositiveSmallIntegerField(default=1)
    available_count_for_sale = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'vip_price'
        ordering = ['-id']


class Storage(Base):
    objects = MyQuerySet.as_manager()
    select = ['product', 'product__thumbnail']
    prefetch = ['product__media', 'feature']

    required_fields = ['supplier', 'dimensions']
    related_fields = []
    m2m = []
    remove_fields = ['vip_prices', 'items']  # handle in post_process
    custom_m2m = {'features': FeatureStorage}
    required_m2m = []
    fields = {'supplier': 'تامین کننده', 'dimensions': 'ابعاد'}

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
            if not self.dimensions.get('width') or not self.dimensions.get('height') or not self.dimensions.get(
                    'length') or not self.dimensions.get('weight'):
                self.make_item_disable(self, warning=False)
                raise ActivationError(get_activation_warning_msg('ابعاد'))
        else:
            self.required_fields = ['dimensions']
            if Storage.objects.get(pk=self.pk).items.filter(disable=True):
                self.make_item_disable(self)
                raise ActivationError(get_activation_warning_msg('یکی از انبار ها'))
        super().clean()

    def __str__(self):
        return f"{self.product}"

    def pre_process(self, my_dict):
        [my_dict.pop(field, None) for field in self.remove_fields]
        if type(my_dict.get('start_time')) is int or type(my_dict.get('start_time')) is float:
            my_dict['start_time'] = datetime.datetime.utcfromtimestamp(my_dict['start_time']).replace(tzinfo=pytz.utc)
        if type(my_dict.get('deadline', None)) is int or type(my_dict.get('deadline')) is float:
            my_dict['deadline'] = datetime.datetime.utcfromtimestamp(my_dict['deadline']).replace(tzinfo=pytz.utc)
        if not my_dict.get('deadline', None):
            my_dict['deadline'] = None
        if type(my_dict.get('tax_type')) is str:
            my_dict['tax_type'] = {'has_not': 1, 'from_total_price': 2, 'from_profit': 3}[my_dict['tax_type']]
        if my_dict.get('discount_price'):
            my_dict['discount_percent'] = int(100 - my_dict['discount_price'] / my_dict['final_price'] * 100)
        if my_dict.get('features', None) and not my_dict.get('features_percent', None):
            # todo debug
            # todo feature: add default_selected_value for feature
            pass
            # raise ValidationError('درصد ویژگی ها نامعتبر است')

        if my_dict.get('priority', None) == 0 and my_dict.get('disable', None):
            my_dict['manage'] = True
        return my_dict

    def post_process(self, my_dict):
        if my_dict is None:
            return True
        if self.product.manage or self.product.default_storage.available_count_for_sale < 1:
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
        if self.product.type == 4:  # package
            # {'is_package': True, 'items': [{'package_item_id':1, 'count': 5}, {'package_item_id':2, 'count': 10}]}
            self.items.clear()
            user = self.created_by
            package_items = [Package(**item, created_by=user, updated_by=user, package=self) for item in
                             my_dict.get('items')]
            Package.objects.bulk_create(package_items)
            self.discount_price = 0
            self.final_price = 0
            self.dimensions = {"width": 0, "height": 0, "length": 0, "weight": 0}
            for package_item in package_items:
                self.discount_price += package_item.package_item.discount_price * package_item.count
                self.final_price += package_item.package_item.final_price * package_item.count
                self.dimensions = {"width": self.dimensions['width'] + package_item.package_item.dimensions['width'],
                                   "height": self.dimensions['height'] + package_item.package_item.dimensions['height'],
                                   "length": self.dimensions['length'] + package_item.package_item.dimensions['length'],
                                   "weight": self.dimensions['weight'] + package_item.package_item.dimensions['weight']}
            self.discount_percent = int(100 - self.discount_price / self.final_price * 100)
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
        self.__dict__ = self.pre_process(self.__dict__)
        self.priority = Product.objects.filter(pk=self.product_id).count() - 1
        super().save(*args)
        self.post_process(kwargs)

    product = models.ForeignKey(Product, on_delete=PROTECT, related_name='storages')
    features = models.ManyToManyField(Feature, through='FeatureStorage', related_query_name="features")
    items = models.ManyToManyField("self", through='Package', symmetrical=False)
    features_percent = models.PositiveSmallIntegerField(default=0)
    available_count = models.PositiveIntegerField(default=0, verbose_name='Available count')
    sold_count = models.PositiveIntegerField(default=0, verbose_name='Sold count')
    start_price = models.PositiveIntegerField(default=0, verbose_name='Start price')
    qty = models.CharField(max_length=255, null=True, blank=True, help_text="quantity")
    sku = models.CharField(max_length=255, null=True, blank=True, help_text="stock keeping unit")
    final_price = models.PositiveIntegerField(default=0, verbose_name='Final price')
    discount_price = models.PositiveIntegerField(default=0, verbose_name='Discount price')
    shipping_cost = models.PositiveIntegerField(null=True, blank=True)
    available_count_for_sale = models.PositiveIntegerField(default=0, verbose_name='Available count for sale')
    max_count_for_sale = models.PositiveSmallIntegerField(default=1)
    min_count_alert = models.PositiveSmallIntegerField(default=5)
    priority = models.PositiveSmallIntegerField(default=0)
    tax_type = models.PositiveSmallIntegerField(default=0,  # turn to int in pre process
                                                choices=[(1, 'has_not'), (2, 'from_total_price'), (3, 'from_profit')])
    tax = models.PositiveIntegerField(default=0)
    discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Discount price percent')
    package_discount_price = models.PositiveSmallIntegerField(default=0)
    gender = models.BooleanField(blank=True, null=True)
    disable = models.BooleanField(default=True)
    deadline = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    title = JSONField(default=multilanguage)
    supplier = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True)
    invoice_description = JSONField(default=multilanguage)
    invoice_title = JSONField(default=multilanguage)
    vip_prices = models.ManyToManyField(VipType, through='VipPrice', related_name="storages")
    dimensions = JSONField(help_text="{'weight': '', 'height: '', 'width': '', 'length': ''}",
                           validators=[validate_vip_price], default=dict)
    max_shipping_time = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'storage'
        ordering = ['-id']


class Basket(Base):
    prefetch = ['products']

    def __str__(self):
        return f"{self.user}"

    user = models.ForeignKey(User, on_delete=CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    count = models.PositiveIntegerField(default=0)
    products = models.ManyToManyField(Storage, through='BasketProduct')
    description = models.TextField(blank=True, null=True)
    # active = models.BooleanField(default=True)
    sync = models.CharField(max_length=255, choices=[(0, 'ready'), (1, 'reserved'),
                                                     (2, 'canceled'), (3, 'done')], default=0)

    class Meta:
        db_table = 'basket'
        ordering = ['-id']


class BasketProduct(MyModel):
    related = ['storage']

    def __str__(self):
        return f"{self.id}"

    def validation(self):
        for feature in self.features:
            try:
                item = FeatureStorage.objects.get(pk=feature['fsid'])
                item = Feature.objects.get(pk=item.feature_id)
                ids = [v.get('id') for v in item.value]
                if not set(feature['fvid']).issubset(ids):
                    raise ValidationError(_('invalid feature_value_id'))
            except Feature.DoesNotExist:
                raise ValidationError(_('invalid feature_id'))
            except FeatureStorage.DoesNotExist:
                raise ValidationError(_('invalid feature_storage_id'))
            except Exception as e:
                print(e)
                raise ValidationError(_('invalid data'))

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    storage = models.ForeignKey(Storage, on_delete=PROTECT)
    basket = models.ForeignKey(Basket, on_delete=PROTECT, null=True, blank=True)
    count = models.PositiveIntegerField(default=1)
    box = models.ForeignKey(Box, on_delete=PROTECT)
    features = JSONField(default=list)
    vip_price = models.ForeignKey(to=VipPrice, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'basket_product'
        ordering = ['-id']


class Blog(Base):
    def __str__(self):
        return self.title

    box = models.ForeignKey(Box, on_delete=CASCADE)
    title = JSONField(default=multilanguage)
    description = JSONField(null=True, blank=True)
    media = models.ForeignKey(Media, on_delete=CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'blog'
        ordering = ['-id']


class BlogPost(Base):
    objects = MyQuerySet.as_manager()

    def __str__(self):
        return self.permalink

    blog = models.ForeignKey(Blog, on_delete=CASCADE, blank=True, null=True)
    body = JSONField(blank=True, null=True)
    permalink = models.CharField(max_length=255, db_index=True, unique=True)
    media = models.ForeignKey(Media, on_delete=CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'blog_post'
        ordering = ['-id']


class Comment(Base):
    def __str__(self):
        return f"{self.user}"

    def validation(self):
        try:
            if self.rate > 10 or self.type > 1:
                raise ValidationError(_('invalid value for rate or type'))
        except TypeError:
            pass

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True)
    text = models.TextField(null=True, blank=True)
    rate = models.PositiveSmallIntegerField(null=True, blank=True)
    satisfied = models.BooleanField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=CASCADE)
    reply_to = models.ForeignKey('self', on_delete=CASCADE, blank=True, null=True, related_name="replys")
    suspend = models.BooleanField(default=False)
    type = models.PositiveSmallIntegerField(choices=[(1, 'q-a'), (2, 'rate')])
    product = models.ForeignKey(Product, on_delete=CASCADE, null=True, blank=True)
    blog_post = models.ForeignKey(BlogPost, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'comments'
        ordering = ['-id']


class Invoice(Base):
    objects = MyQuerySet.as_manager()
    select = ['basket']

    def __str__(self):
        return f"{self.user}"

    def pre_process(self, my_dict):  # only for update
        if type(my_dict.get('status')) is str:
            try:
                my_dict['status'] = {'payed': 2, 'sent': 6}[my_dict['status']]
            except KeyError:
                pass
        return my_dict

    suspended_at = models.DateTimeField(blank=True, null=True, verbose_name='Suspended at')
    suspended_by = models.ForeignKey(User, on_delete=CASCADE, blank=True, null=True, verbose_name='Suspended by',
                                     related_name='invoice_suspended_by')
    user = models.ForeignKey(User, on_delete=CASCADE)
    sync_task = models.ForeignKey(PeriodicTask, on_delete=CASCADE, null=True, blank=True,
                                  related_name='invoice_sync_task')
    email_task = models.ForeignKey(PeriodicTask, on_delete=CASCADE, null=True, blank=True)
    basket = models.ForeignKey(to=Basket, on_delete=PROTECT, related_name='invoice_basket', null=True)
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
    sale_reference_id = models.BigIntegerField(null=True, blank=True)
    card_holder = models.CharField(max_length=31, null=True, blank=True)
    final_amount = models.PositiveIntegerField(help_text='from bank', null=True, blank=True)
    mt_profit = models.PositiveIntegerField(null=True, blank=True)
    ha_profit = models.PositiveIntegerField(null=True, blank=True)
    ipg = models.PositiveSmallIntegerField(default=1)
    expire = models.DateTimeField(null=True, blank=True)
    status = models.PositiveSmallIntegerField(default=1, choices=((1, 'pending'), (2, 'payed'), (3, 'canceled'),
                                                                  (4, 'rejected'), (5, 'sent')))
    max_shipping_time = models.IntegerField(default=0)
    suppliers = models.ManyToManyField(User, through="InvoiceSuppliers", related_name='invoice_supplier')
    post_tracking_code = models.CharField(max_length=255, null=True, blank=True)
    post_invoice = models.ForeignKey("Invoice", on_delete=CASCADE, related_name='main_invoice', null=True, blank=True)

    class Meta:
        db_table = 'invoice'
        ordering = ['-id']


# todo disable value_added type (half)
class InvoiceSuppliers(MyModel):
    invoice = models.ForeignKey(Invoice, on_delete=CASCADE)
    supplier = models.ForeignKey(User, on_delete=CASCADE)
    amount = models.PositiveIntegerField()

    class Meta:
        db_table = 'supplier_invoice'
        ordering = ['-id']


class InvoiceStorage(Base):
    objects = MyQuerySet.as_manager()

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
    key = models.CharField(max_length=31, unique=True, null=True, db_index=True)
    filename = models.CharField(max_length=255, null=True, blank=True)
    box = models.ForeignKey(Box, on_delete=CASCADE)
    tax = models.PositiveIntegerField()
    storage = models.ForeignKey(Storage, on_delete=PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=PROTECT, related_name='invoice_storages')
    count = models.PositiveIntegerField(default=1)
    final_price = models.PositiveIntegerField()
    total_price = models.PositiveIntegerField()
    start_price = models.PositiveIntegerField()
    discount = models.PositiveIntegerField()
    discount_price = models.PositiveIntegerField()
    discount_price_without_tax = models.PositiveIntegerField()
    discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Discount price percent')
    # vip_discount_price = models.PositiveIntegerField(verbose_name='Discount price', default=0)
    # vip_discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Discount price percent')
    deliver_status = models.PositiveSmallIntegerField(choices=deliver_status, default=1)

    details = JSONField(null=True, help_text="package/storage/product details")
    features = JSONField(default=list)

    # stodo change to invoice_storage
    class Meta:
        db_table = 'invoice_product'
        ordering = ['-id']


class DiscountCode(Base):
    storage = models.ForeignKey(Storage, on_delete=PROTECT, related_name='discount_code')
    qr_code = models.ForeignKey(Media, on_delete=PROTECT, null=True, blank=True)
    invoice = models.ForeignKey(Invoice, on_delete=PROTECT, null=True, blank=True)
    code = models.CharField(max_length=32, default="")

    class Meta:
        db_table = 'discount_code'
        ordering = ['-id']


class Menu(Base):
    select = ['media', 'parent']

    def __str__(self):
        return f"{self.name['fa']}"

    type = models.PositiveSmallIntegerField(choices=((1, 'home'),))
    name = JSONField(default=multilanguage)
    media = models.ForeignKey(Media, on_delete=PROTECT, blank=True, null=True)
    url = models.CharField(max_length=25, null=True, blank=True)
    parent = models.ForeignKey("self", on_delete=CASCADE, null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=0)
    box = models.ForeignKey(Box, on_delete=PROTECT, null=True, blank=True)

    class Meta:
        db_table = 'menu'
        ordering = ['-id']


class Rate(MyModel):

    def __str__(self):
        return f"{self.rate}"

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    user = models.ForeignKey(User, on_delete=CASCADE)
    rate = models.FloatField()
    storage = models.ForeignKey(Storage, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'rate'
        ordering = ['-id']


class Slider(Base):
    select = ['media']
    required_fields = ['title', 'media', 'mobile_media', 'type']
    equired_multi_lang = ['title']
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
    priority = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'slider'
        ordering = ['-id']


class SpecialOffer(Base):
    select = ['media']

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
        ordering = ['-id']


class SpecialProduct(Base):
    select = ['storage', 'thumbnail']
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
        if storage.disable and not self.deleted_by:
            raise ActivationError('اول باید انبار رو فعال کنی')
        super().save(*args)
        if self.deleted_by:
            return {'variant': 'warning',
                    'message': 'این انبار محصول ویژه هم داشت که دیگه نداره، چون غیرفعالش کردی تقصیر خودته :)'}

    storage = models.ForeignKey(Storage, on_delete=CASCADE, null=True, blank=True, related_name='special_products')
    thumbnail = models.ForeignKey(Media, on_delete=PROTECT, related_name='special_product_thumbnail', null=True,
                                  blank=True)
    box = models.ForeignKey(Box, on_delete=PROTECT, null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    name = JSONField(null=True, blank=True)

    class Meta:
        db_table = 'special_products'
        ordering = ['-id']


class WishList(Base):
    def __str__(self):
        return f"{self.user}"

    user = models.ForeignKey(User, on_delete=CASCADE)
    # type = models.CharField(max_length=255, )
    notify = models.BooleanField(default=False)
    product = models.ForeignKey(Product, on_delete=CASCADE)

    class Meta:
        db_table = 'wishList'
        ordering = ['-id']


class NotifyUser(MyModel):

    def __str__(self):
        return f"{self.user}"

    user = models.ForeignKey(User, on_delete=CASCADE)
    type = models.PositiveSmallIntegerField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=CASCADE)
    box = models.ForeignKey(Box, on_delete=CASCADE)

    class Meta:
        db_table = 'notify_user'
        ordering = ['-id']


# ---------- Tourism ---------- #

class ResidenceType(Base):
    class Meta:
        db_table = 'residence_type'
        ordering = ['-id']

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
        ordering = ['-id']


class House(Base):
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
        ordering = ['-id']


class Booking(Base):
    def __str__(self):
        return f"{self.house}"

    user = models.ForeignKey(User, on_delete=PROTECT, related_name='booking_user')
    house = models.ForeignKey(House, on_delete=PROTECT, null=True)
    product = models.ForeignKey(Product, on_delete=PROTECT, null=True)
    address = models.TextField(null=True)
    location = JSONField(null=True)
    status = models.PositiveSmallIntegerField(choices=[(1, 'pending'), (2, 'sent'), (3, 'deliver'), (4, 'reject')],
                                              default=1)
    invoice = models.ForeignKey(Invoice, on_delete=PROTECT, null=True, blank=True)
    confirmation_date = models.DateTimeField(null=True, blank=True)
    confirmation_by = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True,
                                        related_name='booking_confirmation')
    confirm = models.BooleanField(default=False)
    people_count = models.PositiveSmallIntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    cancel_at = models.DateTimeField(null=True, blank=True)
    cancel_by = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True, related_name='booking_cancel_by')
    reject_at = models.DateTimeField(null=True, blank=True)
    reject_by = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True, related_name='booking_reject_by')

    class Meta:
        db_table = 'book'
        ordering = ['-id']


class Holiday(MyModel):

    def __str__(self):
        return self.occasion

    day_off = models.BooleanField(default=False)
    occasion = models.TextField(blank=True)
    date = models.DateField()

    class Meta:
        db_table = 'holiday'
        ordering = ['-id']


@receiver(post_softdelete, sender=Media)
def submission_delete(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(False)
