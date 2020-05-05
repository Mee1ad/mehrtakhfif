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

media_types = [(1, 'image'), (2, 'thumbnail'), (3, 'media'), (4, 'slider'), (5, 'ads'), (6, 'avatar')]
has_placeholder = [1, 2, 3, 4, 5]


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
    if instance.type == 7:  # avatar
        return f'avatar/{filename}'
    date = timezone.now().strftime("%Y-%m-%d")
    time = timezone.now().strftime("%H-%M-%S-%f")[:-4]
    if instance.type in has_placeholder:
        time = f'{time}-has-ph'
    # file_type = re.search('\\w+', instance.type)[0]
    file_format = os.path.splitext(instance.image.name)[-1]
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
            raise ValidationError('list item is not dict')
        return True
    raise ValidationError('data is not list')


def default_meals():
    return {'Breakfast': False, 'Lunch': False, 'Dinner': False}


def permalink_validation(permalink):
    pattern = '^[A-Za-z0-9\u0591-\u07FF\uFB1D-\uFDFD\uFE70-\uFEFC][A-Za-z0-9-\u0591-\u07FF\uFB1D-\uFDFD\uFE70-\uFEFC]*$'
    permalink = permalink
    if permalink and not re.match(pattern, permalink):
        raise ValidationError("پیوند یکتا نامعتبر است")
    return permalink.lower()


class MyQuerySet(SafeDeleteQueryset):
    _safedelete_visibility = DELETED_INVISIBLE
    _safedelete_visibility_field = 'pk'
    _queryset_class = SafeDeleteQueryset

    def update(self, *args, **kwargs):
        if not self:
            return True
        remove_list = ['id', 'box_id', 'tags', 'features', 'categories']
        validations = {'storage': self.storage_validation, 'category': self.category_validation,
                       'product': self.product_validation}
        if isinstance(self[0], Product):
            remove_list += ['media']
        if kwargs.get('validation', None):
            kwargs.pop('validation')
            model = self[0].__class__.__name__.lower()
            validations.update(dict.fromkeys(['feature', 'brand', 'tag'], self.default_validation))
            kwargs = validations[model](**kwargs)
        [kwargs.pop(item, None) for item in remove_list]
        return super().update(**kwargs)

    def category_validation(self, **kwargs):
        category = self.first()
        permalink_validation(kwargs.get('permalink', 'pass'))
        pk = kwargs.get('id')
        parent_id = kwargs.get('parent_id')
        if (pk == parent_id and pk is not None) or Category.objects.filter(pk=parent_id, parent_id=pk).exists():
            raise ValidationError("والد نامعتبر است")
        if not category.media and kwargs.get('disable') is False:
            raise ValidationError('قبل از فعالسازی تصویر دسته بندی را مشخص کنید')
        features = Feature.objects.filter(pk__in=kwargs.get('features', []))
        category.feature_set.clear()
        category.feature_set.add(*features)
        return kwargs

    def storage_validation(self, **kwargs):
        storage = self.first()
        if kwargs.get('is_manage', None):
            kwargs.pop('is_manage')
            return kwargs
        if 'priority' in kwargs:
            if storage.disable is True and kwargs['priority'] == 0:
                raise ValidationError('انبار پیش فرض باید فعال باشد')
            return kwargs
        try:
            kwargs = storage.validation(kwargs)
        except KeyError:
            try:
                if storage.deadline < timezone.now() and kwargs['disable'] is False:
                    raise ValidationError("لطفا زمان ددلاین محصول رو افزایش دهید")
            except TypeError:
                pass
            return {'disable': kwargs['disable']}
        if kwargs.get('features', None):
            storage.features.clear()
            feature_storages = [FeatureStorage(feature_id=item['feature_id'], value=item['value'],
                                               storage_id=storage.pk) for item in kwargs['features']]
            FeatureStorage.objects.bulk_create(feature_storages)
        if kwargs.get('manage', None):
            item = self.first()
            item.product.assign_default_value(item.product_id)
        return kwargs

    def activation_validation(self, obj, kwargs):
        obj_dict = obj.__dict__
        if kwargs.get('disable') is False:
            for field1 in obj.activation_required_fields:
                if not obj_dict[field1]:
                    raise ValidationError(f'check {field1} before activation')
            for field2 in obj.activation_required_m2m_fields:
                if not getattr(obj, field2).all():
                    raise ValidationError(f'check {field2} before activation')
            return kwargs
        if obj.disable is False and not kwargs.get('disable'):
            for field1 in obj.activation_required_fields:
                if not kwargs.get(field1):
                    raise ValidationError(f'make item disable before editing {field1}')
            for field2 in obj.kwargs_required_m2m:
                if not kwargs.get(field2):
                    raise ValidationError(f'make item disable before editing {field2}')

    def product_validation(self, **kwargs):
        product = self.first()
        self.activation_validation(product, kwargs)
        if product.disable is False and not product.storages.filter(disable=False):
            kwargs['disable'] = True
        if kwargs.get('storages_id', None):
            [Storage.objects.filter(pk=pk).update(priority=kwargs['storages_id'].index(pk), is_manage=True)
             for pk in kwargs.get('storages_id', [])]
            kwargs.pop('storages_id')
            return kwargs
        if (not product.thumbnail or not product.media.all() or not product.category.all()) \
                and kwargs.get('disable') is False:
            raise ValidationError('لطفا تصاویر و دسته بندی محصول را بررسی کنید')
        if product.disable is False and (kwargs.get('thumbnail', '') is None or kwargs.get('media') is []
                                         or kwargs.get('tag') is [] or kwargs.get('category') is []):
            raise ValidationError('محصول فعال است. برای اعمال تغییرات ابتدا محصول را غیرفعال نمایید')
        permalink_validation(kwargs.get('permalink', 'pass'))
        default_storage_id = kwargs.get('default_storage_id')
        pk = kwargs.get('id')
        if default_storage_id:
            new_default_storage = Storage.objects.filter(pk=default_storage_id)
            Storage.objects.filter(product_id=pk, priority__lt=new_default_storage.first().priority) \
                .order_by('priority').update(priority=F('priority') + 1)
            new_default_storage.update(priority=0)
        if kwargs.get('tags', None) is not None and kwargs.get('categories') is not None \
                and kwargs.get('media') is not None:
            tags = Tag.objects.filter(pk__in=kwargs.get('tags', []))
            if not tags:
                raise ValidationError('لطفا حداقل 3 تگ را انتخاب کنید')
            categories = Category.objects.filter(pk__in=kwargs.get('categories', []))
            if not categories:
                raise ValidationError('لطفا دسته بندی را انتخاب کنید')
            product.tags.clear()
            product.tags.add(*tags)
            product.category.clear()
            product.category.add(*categories)
            product.media.clear()
            p_medias = [ProductMedia(product=product, media_id=pk, priority=kwargs['media'].index(pk)) for pk in
                        kwargs.get('media', [])]
            ProductMedia.objects.bulk_create(p_medias)
        if kwargs.get('manage', None):
            item = self.first()
            item.assign_default_value()
        return kwargs

    # todo advance disabler for product storage category

    def default_validation(self, **kwargs):
        item = self.first()
        return item.validation(kwargs)


class Base(SafeDeleteModel):
    # related_query_name = "%(app_label)s_%(class)ss" for many to many
    class Meta:
        abstract = True

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=PROTECT, related_name="%(app_label)s_%(class)s_created_by")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('User', on_delete=PROTECT, related_name="%(app_label)s_%(class)s_updated_by")
    deleted_by = models.ForeignKey('User', on_delete=PROTECT, null=True, blank=True,
                                   related_name="%(app_label)s_%(class)s_deleted_by")

    def safe_delete(self, user_id):
        i = 1
        while True:
            try:
                self.permalink = f"{self.permalink}-deleted-{i}"
                self.deleted_by_id = user_id
                self.save()
                break
            except IntegrityError:
                i += 1
            except AttributeError:
                self.deleted_by_id = user_id
                self.save()
                break
        self.delete()

    def get_name_fa(self):
        try:
            return self.name['fa']
        except Exception:
            pass


class User(AbstractUser):

    def __str__(self):
        return self.username

    def get_avatar(self):
        try:
            return HOST + self.avatar.image.url
        except Exception:
            pass

    def validation(self, kwargs):
        pass

    def save(self, *args, **kwargs):
        self.validation(self.__dict__)
        self.full_clean()
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
    is_vip = models.BooleanField(default=False)
    is_supplier = models.BooleanField(default=False)
    is_verify = models.BooleanField(default=False)
    privacy_agreement = models.BooleanField(default=False)
    deposit_id = models.PositiveSmallIntegerField(null=True, blank=True)
    default_address = models.OneToOneField(to="Address", on_delete=SET_NULL, null=True, blank=True,
                                           related_name="user_default_address")
    box_permission = models.ManyToManyField("Box")
    email_verified = models.BooleanField(default=False, verbose_name='Email verified')
    subscribe = models.BooleanField(default=True)
    avatar = models.ForeignKey("Media", on_delete=SET_NULL, null=True, blank=True)
    meli_code = models.CharField(max_length=15, blank=True, null=True, verbose_name='National code')
    wallet_credit = models.IntegerField(default=0)
    suspend_expire_date = models.DateTimeField(blank=True, null=True, verbose_name='Suspend expire date')
    activation_code = models.CharField(max_length=127, null=True, blank=True)
    activation_expire = models.DateTimeField(null=True, blank=True)
    token = models.CharField(max_length=255, unique=True, null=True, blank=True)
    token_expire = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=PROTECT, related_name="%(app_label)s_%(class)s_created_by",
                                   null=True, blank=True)
    updated_by = models.ForeignKey('User', on_delete=PROTECT, related_name="%(app_label)s_%(class)s_updated_by",
                                   null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user'
        ordering = ['-id']


class Client(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True)
    device_id = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255)
    last_login_ip = models.CharField(max_length=31)

    class Meta:
        ordering = ['-id']


class State(models.Model):
    def __str__(self):
        return self.name

    id = models.AutoField(auto_created=True, primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'state'
        ordering = ['-id']


class City(models.Model):
    def __str__(self):
        return self.name

    id = models.AutoField(auto_created=True, primary_key=True)
    name = models.CharField(max_length=255)
    state = models.ForeignKey(State, on_delete=CASCADE)

    class Meta:
        db_table = 'city'
        ordering = ['-id']


class Address(models.Model):
    """
        Stores a single blog entry, related to :model:`auth.User` and
        :model:`server.Address`.
    """

    def __str__(self):
        return self.city.name

    def validation(self):
        if not City.objects.filter(pk=self.city.pk, state=self.state).exists():
            raise ValidationError('شهر یا استان نامعتبر است')

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    id = models.BigAutoField(auto_created=True, primary_key=True)
    state = models.ForeignKey(State, on_delete=PROTECT)
    city = models.ForeignKey(City, on_delete=PROTECT)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    postal_code = models.CharField(max_length=15, verbose_name='Postal code')
    address = models.TextField()
    location = JSONField(null=True)
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
    media = models.ForeignKey("Media", on_delete=CASCADE, null=True, blank=True, related_name="box_image_box_id")

    class Meta:
        db_table = 'box'
        ordering = ['-id']
        permissions = [("has_access", "Can manage that box")]


class Media(Base):
    def __str__(self):
        try:
            return self.title['fa']
        except KeyError:
            return self.title['user_id']

    def save(self, *args, **kwargs):
        sizes = {'thumbnail': (600, 372), 'media': (1280, 794), 'category': (800, 400)}
        try:
            with Image.open(self.image) as im:
                try:
                    width, height = im.size
                    if (width, height) != sizes[self.get_type_display()]:
                        raise ValidationError('سایز عکس نامعتبر است')
                except KeyError as e:
                    print(e)
        except ValueError:
            pass
        self.validation()
        super().save(*args, **kwargs)
        if self.type in has_placeholder:
            ph = reduce_image_quality(self.image.path)
            name = self.image.name.replace('has-ph', 'ph')
            ph.save(f'{MEDIA_ROOT}/{name}', optimize=True, quality=80)

    choices = [(1, 'image'), (2, 'thumbnail'), (3, 'media'), (4, 'slider'),
               (5, 'ads'), (6, 'avatar'), (7, 'category'), (100, 'video'), (200, 'audio')]
    image = models.FileField(upload_to=upload_to, null=True, blank=True)
    video = models.URLField(null=True, blank=True)
    audio = models.URLField(null=True, blank=True)
    title = JSONField(default=multilanguage)
    type = models.PositiveSmallIntegerField(choices=choices)
    box = models.ForeignKey(Box, on_delete=models.CASCADE, null=True, blank=True, related_name="medias")

    def validation(self):
        if self.type > len(self.choices):
            raise ValidationError('invalid type')

    class Meta:
        db_table = 'media'
        ordering = ['-id']


class Category(Base):
    objects = MyQuerySet.as_manager()
    prefetch = ['feature_set']

    def __str__(self):
        return f"{self.name['fa']}"

    def validation(self):
        permalink_validation(self.permalink)
        if self.parent is None and self.permalink is None:
            raise ValidationError("اگر این یک دسته بندی خارجی است باید دسته بندی والد انتخاب شود")

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)
        pk = self.id
        parent_id = self.parent_id
        if Category.objects.filter(pk=parent_id, parent_id=pk).exists():
            self.parent = None
            self.save()
            raise ValidationError("والد نامعتبر است")

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
            raise ValidationError('invalid type')
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


class Product(Base):
    objects = MyQuerySet.as_manager()
    select = ['category', 'box', 'thumbnail']
    prefetch = ['tags', 'media']
    filter = {"verify": True, "disable": False}
    activation_required_fields = ['thumbnail_id']
    activation_required_m2m_fields = ['category', 'tags', 'media']
    kwargs_required_m2m = ['categories', 'tags', 'media']

    def assign_default_value(self):
        storages = self.storages.all()
        Product.objects.filter(pk=self.pk).update(default_storage=min(storages, key=attrgetter('discount_price')))

    def validation(self):
        permalink_validation(self.permalink)

    def save(self, *args, **kwargs):
        if kwargs.get('validation', True):
            self.validation()
        kwargs.get('validation', None)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name['fa']}"

    def get_name_en(self):
        return self.name['en']

    def get_name_ar(self):
        return self.name['ar']

    def get_category_fa(self):
        try:
            return self.category.all().first().name['fa']
        except Exception:
            pass

    def get_category_en(self):
        return self.category.name['en']

    def get_category_ar(self):
        return self.category.name['ar']

    def get_thumbnail(self):
        try:
            return HOST + self.thumbnail.image.url
        except Exception:
            pass

    # def save(self):
    #     self.slug = slugify(self.title)
    #     super(Post, self).save()

    category = models.ManyToManyField(Category, related_query_name="categories", related_name="categories")
    box = models.ForeignKey(Box, on_delete=PROTECT)
    brand = models.ForeignKey(Brand, on_delete=PROTECT, null=True, blank=True)
    thumbnail = models.ForeignKey(Media, on_delete=PROTECT, related_name='product_thumbnail', null=True, blank=True)
    city = models.ForeignKey(City, on_delete=CASCADE, null=True, blank=True)
    default_storage = models.OneToOneField(null=True, blank=True, to="Storage", on_delete=CASCADE,
                                           related_name='product_default_storage')
    tags = models.ManyToManyField(Tag, through="ProductTag", related_name='products')
    media = models.ManyToManyField(Media, through='ProductMedia')
    income = models.BigIntegerField(default=0)
    profit = models.PositiveIntegerField(default=0)
    rate = models.PositiveSmallIntegerField(default=0)
    disable = models.BooleanField(default=True)
    verify = models.BooleanField(default=False)
    manage = models.BooleanField(default=True)
    type = models.PositiveSmallIntegerField(choices=[(1, 'service'), (2, 'product'), (3, 'tourism'), (4, 'package'),
                                                     (5, 'package_item')])
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

    # home_buissiness =
    # support_description =
    class Meta:
        db_table = 'product'
        ordering = ['-updated_at']


class ProductTag(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True)
    product = models.ForeignKey(Product, on_delete=PROTECT)
    tag = models.ForeignKey(Tag, on_delete=PROTECT)
    show = models.BooleanField(default=False)

    class Meta:
        db_table = 'product_tag'
        ordering = ['-id']


class ProductMedia(models.Model):
    related = ['storage']

    def __str__(self):
        return f"{self.id}"

    id = models.BigAutoField(auto_created=True, primary_key=True)
    product = models.ForeignKey(Product, on_delete=PROTECT)
    media = models.ForeignKey(Media, on_delete=PROTECT)
    priority = models.PositiveSmallIntegerField(null=True)

    class Meta:
        db_table = 'product_media'
        ordering = ['-id']


class Storage(Base):
    objects = MyQuerySet.as_manager()
    select = ['product', 'product__thumbnail']
    prefetch = ['product__media', 'feature']
    activation_required_fields = ['supplier']

    def __str__(self):
        return f"{self.product}"

    def validation(self, my_dict):
        my_dict['start_time'] = datetime.datetime.utcfromtimestamp(
            my_dict.get('start_time') or timezone.now().timestamp()).replace(tzinfo=pytz.utc)
        if my_dict.get('deadline', None):
            my_dict['deadline'] = datetime.datetime.utcfromtimestamp(my_dict['deadline']).replace(tzinfo=pytz.utc)
        if not my_dict.get('deadline', None):
            my_dict['deadline'] = None
        my_dict['tax_type'] = {'has_not': 1, 'from_total_price': 2, 'from_profit': 3}[my_dict['tax_type']]
        my_dict['discount_percent'] = int(100 - my_dict['discount_price'] / my_dict['final_price'] * 100)
        my_dict['vip_discount_percent'] = int(100 - my_dict.get('vip_discount_price') / my_dict['final_price'] * 100)
        if my_dict.get('features', None) and not my_dict.get('features_percent', None):
            # todo debug
            # todo feature: add default_selected_value for feature
            pass
            # raise ValidationError('درصد ویژگی ها نامعتبر است')
        if my_dict['available_count'] < my_dict['available_count_for_sale'] or my_dict['available_count'] < my_dict[
            'max_count_for_sale'] or \
                my_dict['available_count'] < my_dict['vip_max_count_for_sale']:
            raise ValidationError("تعداد نامعتبر است")
        my_dict['tax'] = {1: 0, 2: my_dict['discount_price'] * 0.09,
                          3: (my_dict['discount_price'] - my_dict['start_price']) * 0.09}[my_dict['tax_type']]
        supplier = User.objects.filter(pk=my_dict.get('supplier_id'), is_supplier=True).first()
        if supplier and supplier.is_verify is False:
            my_dict['disable'] = True
        if my_dict.get('priority', None) == 0 and my_dict.get('disable', None):
            my_dict['manage'] = True
        if my_dict.get('features_percent', 0) > 100 or my_dict['discount_percent'] > 100 or \
                my_dict['vip_discount_percent'] > 100:
            raise ValidationError("درصد باید کوچکتر از 100 باشد")
        if my_dict['discount_price'] < my_dict['start_price']:
            raise ValidationError("قیمت با تخفیف باید بزرگتر از قیمت اولیه باشد")
        return my_dict

    def save(self, *args, **kwargs):
        if kwargs.get('validation', True):
            self.__dict__ = self.validation(self.__dict__)
        kwargs.pop('validation', None)
        super().save(*args, **kwargs)
        if self.product.manage:
            self.product.assign_default_value()

    product = models.ForeignKey(Product, on_delete=PROTECT, related_name='storages')
    features = models.ManyToManyField(Feature, through='FeatureStorage', related_query_name="features")
    items = models.ManyToManyField("self", through='Package', symmetrical=False)
    features_percent = models.PositiveSmallIntegerField(default=0)
    available_count = models.PositiveIntegerField(verbose_name='Available count')
    sold_count = models.PositiveIntegerField(default=0, verbose_name='Sold count')
    start_price = models.PositiveIntegerField(verbose_name='Start price')
    final_price = models.PositiveIntegerField(verbose_name='Final price')
    discount_price = models.PositiveIntegerField(verbose_name='Discount price')
    vip_discount_price = models.PositiveIntegerField(verbose_name='Discount vip price')
    transportation_price = models.PositiveIntegerField(default=0)
    available_count_for_sale = models.PositiveIntegerField(verbose_name='Available count for sale')
    max_count_for_sale = models.PositiveSmallIntegerField(default=1)
    vip_max_count_for_sale = models.PositiveSmallIntegerField(default=1)
    min_count_alert = models.PositiveSmallIntegerField(default=5)
    priority = models.PositiveSmallIntegerField(default=0)
    tax_type = models.PositiveSmallIntegerField(
        choices=[(1, 'has_not'), (2, 'from_total_price'), (3, 'from_profit')])
    tax = models.PositiveIntegerField(default=0)
    discount_percent = models.PositiveSmallIntegerField(verbose_name='Discount price percent')
    vip_discount_percent = models.PositiveSmallIntegerField(verbose_name='Discount vip price percent')
    gender = models.BooleanField(blank=True, null=True)
    disable = models.BooleanField(default=False)

    deadline = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField()
    title = JSONField(default=multilanguage)
    supplier = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True)
    invoice_description = JSONField(default=multilanguage)
    invoice_title = JSONField(default=multilanguage)

    class Meta:
        db_table = 'storage'
        ordering = ['-id']


class Package(Base):
    def validation(self):
        if self.discount_percent > 100:
            raise ValidationError("درصد باید کوچکتر از 100 باشد")

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    package = models.ForeignKey(Storage, on_delete=PROTECT, related_name="package")
    package_item = models.ForeignKey(Storage, on_delete=PROTECT, related_name="package_item")
    count = models.PositiveSmallIntegerField(default=1)
    discount_percent = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'package'
        ordering = ['-id']


class FeatureStorage(models.Model):
    related = ['storage']

    def __str__(self):
        return f"{self.id}"

    id = models.BigAutoField(auto_created=True, primary_key=True)
    feature = models.ForeignKey(Feature, on_delete=PROTECT)
    storage = models.ForeignKey(Storage, on_delete=PROTECT)
    value = JSONField(default=feature_value_storage)

    class Meta:
        db_table = 'feature_storage'
        ordering = ['-id']


# todo every feature at least must have 2 price
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
    sync = models.CharField(max_length=255, choices=[('false', 0), ('reserved', 1),
                                                     ('canceled', 2), ('done', 3)], default='false')

    class Meta:
        db_table = 'basket'
        ordering = ['-id']


class BasketProduct(models.Model):
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
                    raise ValidationError('invalid feature_value_id')
            except Feature.DoesNotExist:
                raise ValidationError('invalid feature_id')
            except FeatureStorage.DoesNotExist:
                raise ValidationError('invalid feature_storage_id')
            except Exception as e:
                print(e)
                raise ValidationError('invalid data')

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    id = models.BigAutoField(auto_created=True, primary_key=True)
    storage = models.ForeignKey(Storage, on_delete=PROTECT)
    basket = models.ForeignKey(Basket, on_delete=PROTECT, null=True, blank=True)
    count = models.PositiveIntegerField(default=1)
    box = models.ForeignKey(Box, on_delete=PROTECT)
    features = JSONField(default=list)

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
        if self.rate > 10 or self.type > 2:
            raise ValidationError('invalid value for rate or type')

    def save(self, *args, **kwargs):
        self.validation()
        super().save(*args, **kwargs)

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True)
    text = models.TextField(null=True, blank=True)
    rate = models.PositiveSmallIntegerField(default=0, null=True)
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
    select = ['basket']

    def __str__(self):
        return f"{self.user}"

    suspended_at = models.DateTimeField(blank=True, null=True, verbose_name='Suspended at')
    suspended_by = models.ForeignKey(User, on_delete=CASCADE, blank=True, null=True, verbose_name='Suspended by',
                                     related_name='invoice_suspended_by')
    user = models.ForeignKey(User, on_delete=CASCADE)
    sync_task = models.ForeignKey(PeriodicTask, on_delete=CASCADE, null=True, blank=True,
                                  related_name='invoice_sync_task')
    email_task = models.ForeignKey(PeriodicTask, on_delete=CASCADE, null=True, blank=True)
    basket = models.OneToOneField(to=Basket, on_delete=PROTECT, related_name='invoice_basket', null=True)
    storages = models.ManyToManyField(Storage, through='InvoiceStorage')
    payed_at = models.DateTimeField(blank=True, null=True, verbose_name='Payed at')
    special_offer_id = models.BigIntegerField(blank=True, null=True, verbose_name='Special offer id')
    address = models.ForeignKey(to=Address, null=True, blank=True, on_delete=PROTECT)
    description = models.TextField(max_length=255, blank=True, null=True)
    amount = models.PositiveIntegerField()
    final_price = models.PositiveIntegerField()
    reference_id = models.CharField(max_length=127, null=True, blank=True)
    sale_order_id = models.BigIntegerField(null=True, blank=True)
    sale_reference_id = models.BigIntegerField(null=True, blank=True)
    card_holder = models.CharField(max_length=31, null=True, blank=True)
    final_amount = models.PositiveIntegerField(null=True, blank=True)
    ipg = models.PositiveSmallIntegerField(default=1)
    expire = models.DateTimeField(null=True, blank=True)
    status = models.PositiveSmallIntegerField(default=1, choices=((1, 'pending'), (2, 'payed'), (3, 'canceled'),
                                                                  (4, 'rejected')))
    suppliers = models.ManyToManyField(User, through="InvoiceSuppliers", related_name='invoice_supplier')

    class Meta:
        db_table = 'invoice'
        ordering = ['-id']


class InvoiceSuppliers(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=CASCADE)
    supplier = models.ForeignKey(User, on_delete=CASCADE)
    amount = models.PositiveIntegerField()

    class Meta:
        db_table = 'supplier_invoice'
        ordering = ['-id']


class InvoiceStorage(models.Model):
    def __str__(self):
        return f"{self.storage}"

    id = models.BigAutoField(auto_created=True, primary_key=True)
    key = models.CharField(max_length=31, unique=True, null=True, db_index=True)
    filename = models.CharField(max_length=255, null=True, blank=True)
    box = models.ForeignKey(Box, on_delete=CASCADE)
    storage = models.ForeignKey(Storage, on_delete=PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=PROTECT)
    count = models.PositiveIntegerField(default=1)
    tax = models.PositiveIntegerField(default=0)
    final_price = models.PositiveIntegerField(verbose_name='Final price')
    discount_price = models.PositiveIntegerField(verbose_name='Discount price', default=0)
    discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Discount price percent')
    vip_discount_price = models.PositiveIntegerField(verbose_name='Discount price', default=0)
    vip_discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Discount price percent')
    details = JSONField(null=True, help_text="package/storage/product details")
    features = JSONField(null=True)

    # todo change to invoice_storage
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


class Rate(models.Model):
    def __str__(self):
        return f"{self.rate}"

    id = models.BigAutoField(auto_created=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    user = models.ForeignKey(User, on_delete=CASCADE)
    rate = models.FloatField()
    storage = models.ForeignKey(Storage, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'rate'
        ordering = ['-id']


class Slider(Base):
    select = ['media']

    def __str__(self):
        return f"{self.title['fa']}"

    title = JSONField(default=multilanguage)
    product = models.ForeignKey(Product, on_delete=CASCADE, blank=True, null=True)
    media = models.ForeignKey(Media, on_delete=CASCADE)
    type = models.PositiveSmallIntegerField(null=True, blank=True, choices=((1, 'home'),))
    link = models.URLField(null=True, blank=True)

    class Meta:
        db_table = 'slider'
        ordering = ['-id']


class SpecialOffer(Base):
    select = ['media']

    def __str__(self):
        return f"{self.name['fa']}"

    def validation(self):
        if self.discount_percent > 100 or self.vip_discount_percent > 100:
            raise ValidationError("درصد باید کوچکتر از 100 باشد")

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
    peak_price = models.PositiveIntegerField(verbose_name='Peak price')
    discount_price = models.PositiveIntegerField(default=0, verbose_name='Discount price')
    vip_discount_price = models.PositiveIntegerField(default=0, verbose_name='Vip discount price')
    least_count = models.PositiveSmallIntegerField(default=1)
    discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Discount percent')
    vip_discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Vip discount percent')
    code = models.CharField(max_length=65)
    start_date = models.DateTimeField(verbose_name='Start date')
    end_date = models.DateTimeField(verbose_name='End date')
    name = JSONField(default=multilanguage)

    class Meta:
        db_table = 'special_offer'
        ordering = ['-id']


class SpecialProduct(Base):
    select = ['storage', 'thumbnail']

    def __str__(self):
        return f"{self.storage}"

    storage = models.ForeignKey(Storage, on_delete=CASCADE, null=True, blank=True)
    thumbnail = models.ForeignKey(Media, on_delete=PROTECT, related_name='special_product_thumbnail')
    box = models.ForeignKey(Box, on_delete=PROTECT, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=CASCADE, null=True, blank=True)
    # media = models.ForeignKey(Media, on_delete=CASCADE, null=True, blank=True)
    special = models.BooleanField(default=False, null=True, blank=True)
    # type = models.PositiveSmallIntegerField(choices=[(1, 'service'), (2, 'product'), (3, 'code')])
    url = models.URLField(null=True, blank=True)
    name = JSONField(default=multilanguage, null=True, blank=True)
    label_name = JSONField(default=multilanguage, null=True, blank=True)
    # product = models.ForeignKey(Product, on_delete=CASCADE, null=True, blank=True)
    description = JSONField(default=multilanguage)

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


class NotifyUser(models.Model):
    def __str__(self):
        return f"{self.user}"

    id = models.BigAutoField(auto_created=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=CASCADE)
    type = models.PositiveSmallIntegerField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=CASCADE)
    box = models.ForeignKey(Box, on_delete=CASCADE)

    class Meta:
        db_table = 'notify_user'
        ordering = ['-id']


class Ad(models.Model):
    select = ['media', 'storage']

    def __str__(self):
        return self.title['fa']

    id = models.BigAutoField(auto_created=True, primary_key=True)
    title = JSONField(default=multilanguage)
    url = models.CharField(max_length=255, null=True, blank=True)
    media = models.ForeignKey(Media, on_delete=PROTECT)
    storage = models.ForeignKey(Storage, on_delete=PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'ad'
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
            raise ValidationError("درصد باید کوچکتر از 100 باشد")

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


class Holiday(models.Model):
    def __str__(self):
        return self.occasion

    id = models.AutoField(auto_created=True, primary_key=True)
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
