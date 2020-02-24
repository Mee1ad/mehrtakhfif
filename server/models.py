import os
from PIL import Image
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField, ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import *
from django.db import models
from django.db.models import CASCADE, PROTECT, SET_NULL
from safedelete.signals import post_softdelete
from django.dispatch import receiver
from django.utils import timezone
from push_notifications.models import GCMDevice
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE, NO_DELETE
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult
from mehr_takhfif.settings import HOST
import datetime
import pysnooper


def multilanguage():
    return {"fa": "",
            "en": "",
            "ar": ""}


def feature_value():
    return [{"id": 0, "fa": "", "en": "", "ar": ""}]


def feature_value_storage():
    return {"bool": {"fid": 1, "sid": 1, "value": [{"fvid": 1, "price": 5000}]}}


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
    # file_type = re.search('\\w+', instance.type)[0]
    file_format = os.path.splitext(instance.file.name)[-1]
    return f'boxes/{instance.box_id}/{date}/{instance.get_type_display()}/{time}{file_format}'


class MyManager(models.Manager):
    def safe_delete(self, user_id, **kwargs):
        try:
            pass
        except Exception:
            pass


class User(AbstractUser):

    def __str__(self):
        return self.username

    first_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='First name',
                                  validators=[validate_slug])
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Last name',
                                 validators=[validate_slug])
    username = models.CharField(max_length=150, unique=True)
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
    privacy_agreement = models.BooleanField(default=False)
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
    admin_token = models.CharField(max_length=255, unique=True, null=True, blank=True)
    token = models.CharField(max_length=255, unique=True, null=True, blank=True)
    token_expire = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user'
        ordering = ['-id']


class Base(SafeDeleteModel):
    # related_query_name = "%(app_label)s_%(class)ss" for many to many
    class Meta:
        abstract = True

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=PROTECT, related_name="%(app_label)s_%(class)s_created_by")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=PROTECT, related_name="%(app_label)s_%(class)s_updated_by")
    deleted_by = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True,
                                   related_name="%(app_label)s_%(class)s_deleted_by")


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

    id = models.BigAutoField(auto_created=True, primary_key=True)
    state = models.ForeignKey(State, on_delete=PROTECT)
    city = models.ForeignKey(City, on_delete=PROTECT)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    postal_code = models.CharField(max_length=15, verbose_name='Postal code')
    address = models.TextField()
    location = JSONField(null=True)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    active = models.BooleanField(default=False)

    class Meta:
        db_table = 'address'
        ordering = ['-id']


class Box(Base):
    def __str__(self):
        return self.name['fa']

    objects = MyManager()
    name = JSONField(default=multilanguage)
    permalink = models.CharField(max_length=255, db_index=True, unique=True)
    admin = models.OneToOneField(User, on_delete=PROTECT)

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
        sizes = {'thumbnail': (350, 217)}
        im = Image.open(self.file)
        width, height = im.size
        # if (width, height) != sizes[self.get_type_display()]:
        #     raise ValidationError
        super().save(*args, **kwargs)

    file = models.FileField(upload_to=upload_to)
    title = JSONField(default=multilanguage)
    type = models.PositiveSmallIntegerField(choices=[(1, 'image'), (2, 'thumbnail'), (3, 'audio'),
                                                     (4, 'slider'), (5, 'ads'), (6, 'avatar'), (7, 'media')])
    box = models.ForeignKey(Box, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'media'
        ordering = ['-id']


class Category(Base):
    prefetch = ['feature_set']

    def __str__(self):
        return f"{self.name['fa']}"

    parent = models.ForeignKey("self", on_delete=CASCADE, null=True, blank=True)
    box = models.ForeignKey(Box, on_delete=CASCADE)
    name = JSONField(default=multilanguage)
    permalink = models.CharField(max_length=255, db_index=True, unique=True)
    priority = models.SmallIntegerField(default=0)
    disable = models.BooleanField(default=False)
    media = models.ForeignKey(Media, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'category'
        ordering = ['-id']
        indexes = [GinIndex(fields=['name'])]


class Feature(Base):
    def __str__(self):
        return f"{self.id}"

    name = JSONField(default=multilanguage)
    type = models.CharField(max_length=255, choices=((1, 'bool'), (2, 'single'), (3, 'multi')))
    value = JSONField(default=feature_value)
    category = models.ManyToManyField(Category)
    box = models.ForeignKey(Box, on_delete=CASCADE, blank=True, null=True)
    icon = models.CharField(default='default', max_length=255)

    class Meta:
        db_table = 'feature'
        ordering = ['-id']


class Tag(Base):
    def __str__(self):
        return f"{self.name['fa']}"

    permalink = models.CharField(max_length=255, db_index=True, unique=True)
    name = JSONField(default=multilanguage)

    class Meta:
        db_table = 'tag'
        ordering = ['-id']
        indexes = [GinIndex(fields=['name'])]


class Brand(Base):
    name = JSONField(default=multilanguage)

    class Meta:
        db_table = 'brand'
        ordering = ['-id']


class Product(Base):
    select = ['category', 'box', 'thumbnail']
    prefetch = ['tag', 'media']
    filter = {"verify": True, "disable": False}

    def __str__(self):
        return f"{self.name['fa']}"

    def get_name_fa(self):
        return self.name['fa']

    def get_name_en(self):
        return self.name['en']

    def get_name_ar(self):
        return self.name['ar']

    def get_category_fa(self):
        return self.category.name['fa']

    def get_category_en(self):
        return self.category.name['en']

    def get_category_ar(self):
        return self.category.name['ar']

    def get_thumbnail(self):
        return HOST + self.thumbnail.file.url

    # def save(self):
    #     self.slug = slugify(self.title)
    #     super(Post, self).save()

    category = models.ForeignKey(Category, on_delete=CASCADE)
    box = models.ForeignKey(Box, on_delete=PROTECT)
    brand = models.ForeignKey(Brand, on_delete=PROTECT)
    thumbnail = models.ForeignKey(Media, on_delete=PROTECT, related_name='product_thumbnail')
    city = models.ForeignKey(City, on_delete=CASCADE, null=True, blank=True)
    default_storage = models.OneToOneField(null=True, blank=True, to="Storage", on_delete=CASCADE,
                                           related_name='product_default_storage')
    tag = models.ManyToManyField(Tag)
    media = models.ManyToManyField(Media)
    income = models.BigIntegerField(default=0)
    profit = models.BigIntegerField(default=0)
    rate = models.PositiveSmallIntegerField(default=0)
    disable = models.BooleanField(default=True)
    verify = models.BooleanField(default=False)
    type = models.PositiveSmallIntegerField(choices=[(1, 'service'), (2, 'product'), (3, 'code')])
    permalink = models.CharField(max_length=255, db_index=True, unique=True)

    name = JSONField(default=multilanguage)
    # name = pg_search.SearchVectorField(null=True)
    short_description = JSONField(default=multilanguage)
    description = JSONField(default=multilanguage)
    location = JSONField(null=True, blank=True)
    address = JSONField(null=True, blank=True)
    short_address = JSONField(null=True, blank=True)
    properties = JSONField(default=product_properties)
    details = JSONField(default=product_details)

    # home_buissiness =
    # support_description =
    class Meta:
        db_table = 'product'
        ordering = ['-updated_at']


class DiscountCode(Base):
    box = models.ForeignKey(Box, on_delete=PROTECT)
    product = models.ForeignKey(Product, on_delete=PROTECT, null=True, blank=True)
    special_product = models.ForeignKey("SpecialProduct", on_delete=PROTECT, null=True, blank=True)
    special_offer = models.ForeignKey("SpecialOffer", on_delete=PROTECT, null=True, blank=True)
    available = models.BooleanField(default=True)

    class Meta:
        db_table = 'discount_code'
        ordering = ['-id']


class Storage(Base):
    select = ['product', 'product__thumbnail']
    prefetch = ['product__media', 'feature']

    def __str__(self):
        return f"{self.product}"

    def save(self, *args, **kwargs):
        if self.discount_price < self.start_price:
            raise ValidationError("discount price is less than start price")
        super().save(*args, **kwargs)

    product = models.ForeignKey(Product, on_delete=PROTECT)
    feature = models.ManyToManyField(Feature, blank=True, through='FeatureStorage')
    available_count = models.BigIntegerField(verbose_name='Available count')
    sold_count = models.BigIntegerField(default=0, verbose_name='Sold count')
    start_price = models.BigIntegerField(verbose_name='Start price')
    final_price = models.BigIntegerField(verbose_name='Final price')
    discount_price = models.BigIntegerField(verbose_name='Discount price')
    vip_discount_price = models.BigIntegerField(verbose_name='Discount vip price')
    transportation_price = models.IntegerField(default=0)
    available_count_for_sale = models.IntegerField(verbose_name='Available count for sale')
    max_count_for_sale = models.IntegerField(default=1)
    priority = models.IntegerField(default=0)
    tax = models.IntegerField(default=0)
    discount_percent = models.PositiveSmallIntegerField(verbose_name='Discount price percent')
    vip_discount_percent = models.PositiveSmallIntegerField(verbose_name='Discount vip price percent')
    gender = models.BooleanField(blank=True, null=True)
    disable = models.BooleanField(default=False)
    deadline = models.DateTimeField(default=next_month)
    start_time = models.DateTimeField(auto_now_add=True)
    title = JSONField(default=multilanguage)
    supplier = models.ManyToManyField(User, through='StorageSupplier')

    class Meta:
        db_table = 'storage'
        ordering = ['-id']


class StorageSupplier(models.Model):
    id = models.AutoField(auto_created=True, primary_key=True)
    user = models.ForeignKey(User, on_delete=PROTECT)
    storage = models.ForeignKey(Storage, on_delete=PROTECT)
    percent = models.PositiveSmallIntegerField()

    class Meta:
        db_table = 'storage_supplier'
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


class Basket(Base):
    prefetch = ['products']

    def __str__(self):
        return f"{self.user}"

    user = models.ForeignKey(User, on_delete=CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    count = models.IntegerField(default=0)
    products = models.ManyToManyField(Storage, through='BasketProduct')
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    sync = models.CharField(max_length=255, choices=[('false', 0), ('reserved', 1),
                                                     ('canceled', 2), ('done', 3)], default='false')

    class Meta:
        db_table = 'basket'
        ordering = ['-id']


class BasketProduct(models.Model):
    related = ['storage']

    def __str__(self):
        return f"{self.id}"

    id = models.BigAutoField(auto_created=True, primary_key=True)
    storage = models.ForeignKey(Storage, on_delete=PROTECT)
    basket = models.ForeignKey(Basket, on_delete=PROTECT)
    count = models.IntegerField(default=1)
    box = models.ForeignKey(Box, on_delete=PROTECT)
    feature = JSONField(default=list)

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

    def clean(self):
        Comment.objects.filter(user=self.user, type=self.type)

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True)
    text = models.TextField(null=True, blank=True)
    rate = models.PositiveSmallIntegerField(default=0, null=True)
    satisfied = models.BooleanField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=CASCADE)
    reply_to = models.ForeignKey('self', on_delete=CASCADE, blank=True, null=True)
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
    task = models.OneToOneField(PeriodicTask, on_delete=CASCADE, null=True, blank=True)
    basket = models.OneToOneField(to=Basket, on_delete=PROTECT, related_name='invoice_to_basket')
    storages = models.ManyToManyField(Storage, through='InvoiceStorage')
    payed_at = models.DateTimeField(blank=True, null=True, verbose_name='Payed at')
    type = models.PositiveSmallIntegerField(blank=True, null=True)
    special_offer_id = models.BigIntegerField(blank=True, null=True, verbose_name='Special offer id')
    address = models.ForeignKey(to=Address, null=True, blank=True, on_delete=PROTECT)
    description = models.TextField(max_length=255, blank=True, null=True)
    amount = models.IntegerField()
    final_price = models.IntegerField()
    tax = models.IntegerField()
    reference_id = models.CharField(max_length=127, null=True, blank=True)
    sale_order_id = models.IntegerField(null=True, blank=True)
    sale_reference_id = models.IntegerField(null=True, blank=True)
    card_holder = models.CharField(max_length=31, null=True, blank=True)
    final_amount = models.IntegerField(null=True, blank=True)
    ipg = models.SmallIntegerField(default=1)
    expire = models.DateTimeField(null=True, blank=True)
    status = models.PositiveSmallIntegerField(default=1, choices=((1, 'pending'), (2, 'payed'), (3, 'canceled'),
                                                                  (4, 'rejected'), (5, 'new_invoice')))

    class Meta:
        db_table = 'invoice'
        ordering = ['-id']


class InvoiceStorage(models.Model):
    def __str__(self):
        return f"{self.storage}"

    id = models.BigAutoField(auto_created=True, primary_key=True)
    box = models.ForeignKey(Box, on_delete=CASCADE)
    storage = models.ForeignKey(Storage, on_delete=PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=PROTECT)
    count = models.SmallIntegerField(default=1)
    tax = models.IntegerField(default=0)
    final_price = models.BigIntegerField(verbose_name='Final price')
    discount_price = models.BigIntegerField(verbose_name='Discount price', default=0)
    discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Discount price percent')
    vip_discount_price = models.BigIntegerField(verbose_name='Discount price', default=0)
    vip_discount_percent = models.PositiveSmallIntegerField(default=0, verbose_name='Discount price percent')

    class Meta:
        db_table = 'invoice_product'
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
    priority = models.SmallIntegerField(default=0)
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

    box = models.ForeignKey(Box, on_delete=CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=CASCADE, null=True, blank=True)
    media = models.ForeignKey(Media, on_delete=CASCADE)
    user = models.ManyToManyField(User, blank=True)
    product = models.ManyToManyField(Storage, related_name="special_offer_products", blank=True)
    not_accepted_products = models.ManyToManyField(Storage, related_name="special_offer_not_accepted_products",
                                                   blank=True)
    peak_price = models.BigIntegerField(verbose_name='Peak price')
    discount_price = models.IntegerField(default=0, verbose_name='Discount price')
    vip_discount_price = models.IntegerField(default=0, verbose_name='Vip discount price')
    least_count = models.IntegerField(default=1)
    discount_percent = models.SmallIntegerField(default=0, verbose_name='Discount percent')
    vip_discount_percent = models.SmallIntegerField(default=0, verbose_name='Vip discount percent')
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


class HouseOwner(Base):
    def __str__(self):
        return f"{self.user}"

    user = models.ForeignKey(User, on_delete=PROTECT, related_name='house_owner_user')
    account_number = models.CharField(max_length=255)
    account_name = models.CharField(max_length=255)
    account_card = models.CharField(max_length=255)
    account_shaba = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'house_owner'
        ordering = ['-id']


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

    person_price = models.IntegerField(default=0)
    weekend = models.IntegerField(default=0)
    weekday = models.IntegerField(default=0)
    weekly_discount_percent = models.IntegerField(default=0)
    monthly_discount_percent = models.IntegerField(default=0)

    class Meta:
        db_table = 'house_price'
        ordering = ['-id']


class House(Base):
    def __str__(self):
        return self.product.name['fa']

    cancel_rules = JSONField(default=multilanguage, blank=True)
    rules = JSONField(default=multilanguage, blank=True)
    owner = models.ForeignKey(HouseOwner, on_delete=CASCADE)
    state = models.ForeignKey(State, on_delete=PROTECT)
    city = models.ForeignKey(City, on_delete=PROTECT)
    price = models.OneToOneField(HousePrice, on_delete=PROTECT, null=True)
    product = models.OneToOneField(Product, on_delete=PROTECT)
    house_feature = JSONField(blank=True)
    capacity = JSONField()
    residence_type = models.ManyToManyField(ResidenceType)
    rent_type = JSONField(default=multilanguage, blank=True)
    residence_area = JSONField(default=multilanguage, blank=True)
    bedroom = JSONField(blank=True)  # rooms, shared space, rakhte khab, description, ...
    safety = JSONField(blank=True)
    calender = JSONField(blank=True)
    notify_before_arrival = models.IntegerField(default=0)  # days number
    future_booking_time = models.IntegerField(default=7)  # future days with reserve availability

    class Meta:
        db_table = 'house'
        ordering = ['-id']


class CostumeHousePrice(Base):
    house = models.ForeignKey(House, on_delete=PROTECT)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    price = models.IntegerField(default=0)

    class Meta:
        db_table = 'costume_house_price'
        ordering = ['-id']


class Book(Base):
    def __str__(self):
        return f"{self.house}"

    user = models.ForeignKey(User, on_delete=PROTECT, related_name='booking_user')
    house = models.ForeignKey(House, on_delete=PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=PROTECT, null=True, blank=True)
    confirmation_date = models.DateTimeField(null=True, blank=True)
    confirmation_by = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True,
                                        related_name='booking_confirmation')
    confirm = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    cancel_at = models.DateTimeField(null=True, blank=True)
    cancel_by = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True, related_name='booking_cancel_by')
    reject_at = models.DateTimeField(null=True, blank=True)
    reject_by = models.ForeignKey(User, on_delete=PROTECT, null=True, blank=True, related_name='booking_reject_by')

    class Meta:
        db_table = 'book'
        ordering = ['-id']


@receiver(post_softdelete, sender=Media)
def submission_delete(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(False)
