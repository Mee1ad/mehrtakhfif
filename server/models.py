from django.db import models
from django.contrib.postgres.fields import JSONField, DateRangeField, DateTimeRangeField
from django.db.models import CASCADE, PROTECT
from django.contrib.auth.models import AbstractUser
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from django.utils.translation import gettext_lazy as _
from django.core.validators import *
from django.utils import timezone
import pysnooper
from django.db.models.signals import post_delete
from django.dispatch import receiver
import magic
import re
import os


def multilanguage():
    return {"persian": "",
            "english": "",
            "arabic": ""}


def menu_value():
    return {"url": "",
            "image": ""}


def feature_value():
    return [{"persian": "",
             "english": "",
             "arabic": "",
             "price": 0}, ]


def upload_to(instance, filename):
    date = timezone.now().strftime("%Y-%m-%d")
    time = timezone.now().strftime("%H-%M-%S-%f")[:-4]
    # file_type = re.search('\\w+', instance.type)[0]
    file_format = os.path.splitext(instance.file.name)[-1]
    return f'boxes/{instance.box_id}/{date}/{instance.type}/{time}{file_format}'


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
    username = models.CharField(max_length=150, unique=True, error_messages={
            'unique': _("A user with that username already exists."),
        },)
    language = models.CharField(max_length=7, default='fa')
    email = models.TextField(max_length=255, blank=True, null=True, validators=[validate_email])
    password = models.CharField(max_length=255, blank=True, null=True)
    gender = models.BooleanField(blank=True, null=True)
    phone = models.CharField(max_length=15, unique=True, validators=[RegexValidator()])
    updated_at = models.DateTimeField(blank=True, auto_now=True, verbose_name='Updated at')
    is_ban = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False, verbose_name='Phone verified')
    email_verified = models.BooleanField(default=False, verbose_name='Email verified')
    is_superuser = models.BooleanField(default=False, verbose_name='Superuser')
    is_staff = models.BooleanField(default=False, verbose_name='Staff')
    avatar_id = models.BigIntegerField(blank=True, null=True)
    meli_code = models.CharField(max_length=15, blank=True, null=True, verbose_name='National code', unique=True)
    wallet_money = models.IntegerField(blank=True, null=True, verbose_name='Wallet money')
    suspend_expire_date = models.DateTimeField(blank=True, null=True, verbose_name='Suspend expire date')
    vip = models.BooleanField(default=False)
    activation_code = models.CharField(max_length=127, null=True, blank=True)
    activation_expire = models.DateTimeField(null=True, blank=True)
    access_token = models.TextField(max_length=255, null=True, blank=True)
    access_token_expire = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user'


class Address(models.Model):
    def __str__(self):
        return self.city
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    province = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    postal_code = models.CharField(max_length=15, blank=True, null=True, verbose_name='Postal code')
    address = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=65, blank=True, null=True)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        db_table = 'address'


class Box(SafeDeleteModel):
    def __str__(self):
        try:
            return self.name['persian']
        except Exception:
            return self.name

    _safedelete_policy = SOFT_DELETE_CASCADE
    objects = MyManager()
    id = models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    name = JSONField(default=multilanguage)
    admin = models.OneToOneField(User, on_delete=PROTECT)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='box_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='box_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Deleted by',
                                   related_name='box_deleted_by', null=True, blank=True)

    class Meta:
        db_table = 'box'


class Media(SafeDeleteModel):
    # def __str__(self):
    #     return self.title

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    file = models.FileField(upload_to=upload_to)
    title = JSONField(default=multilanguage)
    type = models.CharField(max_length=255, blank=True, null=True)
    box = models.ForeignKey(Box, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='media_created_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='media_deleted_by')

    class Meta:
        db_table = 'media'


class Category(SafeDeleteModel):
    def __str__(self):
        return f"{self.name['persian']}"

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
    box = models.ForeignKey(Box, on_delete=CASCADE)
    name = JSONField(default=multilanguage)
    priority = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='category_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='category_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='category_deleted_by')
    deactive = models.BooleanField(default=False)
    media = models.ForeignKey(Media, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'category'


class Feature(models.Model):
    def __str__(self):
        return f"{self.name['persian']}"

    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='feature_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='feature_updated_by')
    name = JSONField(default=multilanguage)
    value = JSONField(default=feature_value)
    category = models.ManyToManyField(Category)

    class Meta:
        db_table = 'feature'


class Tag(SafeDeleteModel):
    def __str__(self):
        return f"{self.name['persian']}"

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    name = JSONField(default=multilanguage)
    box = models.ForeignKey(Box, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='tag_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='tag_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='tag_deleted_by')

    class Meta:
        db_table = 'tag'


class Product(SafeDeleteModel):
    def __str__(self):
        return f"{self.name['persian']}"

    @property
    def test(self):
        return self.name['persian']

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=CASCADE, verbose_name='Created by',
                                   related_name='product_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=CASCADE, verbose_name='Updated by',
                                   related_name='product_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='product_deleted_by')
    category = models.ForeignKey(Category, on_delete=CASCADE)
    box = models.ForeignKey(Box, on_delete=PROTECT)
    name = JSONField(default=multilanguage)
    tag = models.ManyToManyField(Tag)
    permalink = models.URLField(blank=True, null=True)
    gender = models.BooleanField(blank=True, null=True)
    short_description = JSONField(default=multilanguage)
    description = JSONField(default=multilanguage)
    location = models.CharField(max_length=65, null=True, blank=True)
    usage_condition = JSONField(default=multilanguage)
    media = models.ManyToManyField(Media)
    thumbnail = models.ForeignKey(Media, on_delete=PROTECT, related_name='product_thumbnail')
    sold_count = models.BigIntegerField(default=0, verbose_name='Sold count')
    income = models.BigIntegerField(default=0)
    profit = models.BigIntegerField(default=0)
    deactive = models.BooleanField(default=True)
    verify = models.BooleanField(default=False)
    type = models.CharField(max_length=255)
    feature = models.ManyToManyField(Feature)

    class Meta:
        db_table = 'product'

from django_serializable_model import SerializableModel
class Storage(SafeDeleteModel, SerializableModel):
    def __str__(self):
        return f"{self.product}"

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    product = models.ForeignKey(Product, on_delete=CASCADE)
    box = models.ForeignKey(Box, on_delete=PROTECT)
    category = models.ForeignKey(Category, on_delete=CASCADE)
    available_count = models.BigIntegerField(blank=True, null=True, verbose_name='Available count')
    available_count_for_sale = models.BigIntegerField(blank=True, null=True, verbose_name='Available count for sale')
    count = models.BigIntegerField(blank=True, null=True)
    final_price = models.BigIntegerField(blank=True, null=True, verbose_name='Final price')
    start_price = models.BigIntegerField(blank=True, null=True, verbose_name='Start price')
    transportation_price = models.IntegerField(default=0)
    discount_price = models.BigIntegerField(blank=True, null=True, verbose_name='Discount price')
    discount_vip_price = models.BigIntegerField(blank=True, null=True, verbose_name='Discount vip price')
    discount_price_percent = models.PositiveSmallIntegerField(
        blank=True, null=True, verbose_name='Discount price percent')
    discount_vip_price_percent = models.PositiveSmallIntegerField(
        blank=True, null=True, verbose_name='Discount vip price percent')
    default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=CASCADE, verbose_name='Created by',
                                   related_name='storage_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=CASCADE, verbose_name='Updated by',
                                   related_name='storage_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='storage_deleted_by')

    class Meta:
        db_table = 'storage'


class Basket(SafeDeleteModel):
    def __str__(self):
        return f"{self.user}"

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    count = models.IntegerField(default=0)
    products = models.ManyToManyField(Storage, through='BasketProduct')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='basket_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='basket_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='basket_deleted_by')
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'basket'


class BasketProduct(models.Model):
    def __str__(self):
        return f"{self.id}"

    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    product = models.ForeignKey(Storage, on_delete=models.CASCADE)
    basket = models.ForeignKey(Basket, on_delete=PROTECT)
    count = models.IntegerField(default=1)

    class Meta:
        db_table = 'basket_product'


class Blog(SafeDeleteModel):
    def __str__(self):
        return self.title

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='blog_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='blog_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='blog_deleted_by')
    box = models.ForeignKey(Box, on_delete=models.CASCADE)
    title = JSONField(default=multilanguage)
    description = JSONField(null=True, blank=True)
    media = models.ForeignKey(Media, on_delete=CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'blog'


class BlogPost(SafeDeleteModel):
    def __str__(self):
        return self.permalink

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='blog_post_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='blog_post_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='blog_post_deleted_by')
    blog = models.ForeignKey(Blog, on_delete=CASCADE, blank=True, null=True)
    body = JSONField(blank=True, null=True)
    permalink = models.URLField(blank=True, null=True)
    media = models.ForeignKey(Media, on_delete=CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'blog_post'


class Comment(SafeDeleteModel):
    def __str__(self):
        return f"{self.user}"

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='comment_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='comment_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='comment_deleted_by')
    text = models.TextField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reply = models.ForeignKey('self', on_delete=CASCADE, blank=True, null=True)
    suspend = models.BooleanField(default=False)
    type = models.CharField(max_length=255, )
    product = models.ForeignKey(Product, on_delete=CASCADE, null=True, blank=True)
    blog_post = models.ForeignKey(BlogPost, on_delete=CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'comments'


class Factor(models.Model):
    def __str__(self):
        return f"{self.user}"

    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(to=User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='factor_created_by')
    suspended_at = models.DateTimeField(blank=True, null=True, verbose_name='Suspended at')
    suspended_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='Suspended by',
                                     related_name='factor_suspended_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='factor_product_updated_by')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    price = models.BigIntegerField()
    products = models.ManyToManyField(Product, through='FactorProduct')
    payed_at = models.DateTimeField(blank=True, null=True, verbose_name='Payed at')
    successful = models.BooleanField(default=False)
    type = models.CharField(max_length=255, blank=True, null=True)
    special_offer_id = models.BigIntegerField(blank=True, null=True, verbose_name='Special offer id')
    address = models.TextField(blank=True, null=True)
    description = models.TextField(max_length=255, blank=True, null=True)
    final_price = models.BigIntegerField(verbose_name='Final price')
    discount_price = models.BigIntegerField(verbose_name='Discount price', default=0)
    count = models.SmallIntegerField()
    tax = models.IntegerField()
    start_price = models.BigIntegerField(verbose_name='Start price')

    class Meta:
        db_table = 'factor'


class FactorProduct(models.Model):
    def __str__(self):
        return f"{self.product}"

    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    product = models.ForeignKey(Product, on_delete=PROTECT)
    factor = models.ForeignKey(Factor, on_delete=PROTECT)
    count = models.SmallIntegerField(default=1)
    tax = models.IntegerField(default=0)
    price = models.BigIntegerField()
    final_price = models.BigIntegerField(verbose_name='Final price')
    discount_price = models.BigIntegerField(verbose_name='Discount price', default=0)

    class Meta:
        db_table = 'factor_product'


class Menu(SafeDeleteModel):
    def __str__(self):
        return f"{self.name['persian']}"

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='menu_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='menu_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='menu_deleted_by')
    type = models.CharField(max_length=255, blank=True, null=True)
    name = JSONField(default=multilanguage)
    media = models.ForeignKey(Media, on_delete=PROTECT, blank=True, null=True)
    url = models.CharField(max_length=25, null=True, blank=True)
    parent = models.ForeignKey("self", on_delete=CASCADE, null=True, blank=True)
    priority = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'menu'


class Rate(models.Model):
    def __str__(self):
        return f"{self.rate}"

    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rate = models.FloatField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        db_table = 'rate'


class Slider(SafeDeleteModel):
    def __str__(self):
        return f"{self.title['persian']}"

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    title = JSONField(default=multilanguage)
    product = models.ForeignKey(Product, on_delete=CASCADE, blank=True, null=True)
    media = models.ForeignKey(Media, on_delete=CASCADE)
    type = models.CharField(max_length=255)
    link = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='slider_created_by')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='slider_updated_by')
    deleted_at = models.DateTimeField(blank=True, null=True, verbose_name='Deleted at')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='slider_deleted_by')

    class Meta:
        db_table = 'slider'


class SpecialOffer(SafeDeleteModel):
    def __str__(self):
        return f"{self.name['persian']}"

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    name = JSONField(default=multilanguage)
    code = models.CharField(max_length=65)
    user = models.ManyToManyField(User, blank=True)
    product = models.ManyToManyField(Storage, related_name="special_offer_products", blank=True)
    not_accepted_products = models.ManyToManyField(Storage, related_name="special_offer_not_accepted_products",
                                                   blank=True)
    box = models.ForeignKey(Box, on_delete=CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=CASCADE, null=True, blank=True)
    discount_price = models.IntegerField(default=0, verbose_name='Discount price')
    discount_percent = models.SmallIntegerField(default=0, verbose_name='Discount percent')
    vip_discount_price = models.IntegerField(default=0, verbose_name='Vip discount price')
    vip_discount_percent = models.SmallIntegerField(default=0, verbose_name='Vip discount percent')
    start_date = models.DateTimeField(verbose_name='Start date')
    end_date = models.DateTimeField(verbose_name='End date')
    media = models.ForeignKey(Media, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='special_offer_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='special_offer_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='special_offer_deleted_by')
    least_count = models.IntegerField(default=1)

    peak_price = models.BigIntegerField(verbose_name='Peak price')

    class Meta:
        db_table = 'special_offer'


class SpecialProduct(SafeDeleteModel):
    def __str__(self):
        return f"{self.storage}"

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    title = JSONField(default=multilanguage, null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    storage = models.ForeignKey(Storage, on_delete=CASCADE)
    box = models.ForeignKey(Box, on_delete=PROTECT)
    category = models.ForeignKey(Category, on_delete=CASCADE)
    media = models.ForeignKey(Media, on_delete=CASCADE, null=True, blank=True)
    type = models.CharField(max_length=255, )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='special_product_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='special_product_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='special_product_deleted_by')
    description = JSONField(default=multilanguage)

    class Meta:
        db_table = 'special_products'


class WalletDetail(models.Model):
    def __str__(self):
        return f"{self.user}"

    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    credit = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='wallet_detail_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='wallet_detail_updated_by')
    user = models.ForeignKey(User, on_delete=CASCADE)

    class Meta:
        db_table = 'wallet_detail'


class WishList(SafeDeleteModel):
    def __str__(self):
        return f"{self.user}"

    _safedelete_policy = SOFT_DELETE_CASCADE
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created by',
                                   related_name='wish_list_created_by')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Updated by',
                                   related_name='wish_list_updated_by')
    deleted_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Deleted by',
                                   related_name='wish_list_deleted_by')
    user = models.ForeignKey(User, on_delete=CASCADE)
    type = models.CharField(max_length=255, )
    notify = models.BooleanField(default=False)
    product = models.ForeignKey(Product, on_delete=CASCADE)

    class Meta:
        db_table = 'wishList'


class NotifyUser(models.Model):
    def __str__(self):
        return f"{self.user}"

    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    user = models.ForeignKey(User, on_delete=CASCADE)
    type = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=CASCADE)
    box = models.ForeignKey(Box, on_delete=CASCADE)

    class Meta:
        db_table = 'notify_user'


class Tourism(models.Model):
    def __str__(self):
        return f'{self.date}'

    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    # start_date = models.DateTimeField(default=timezone.now)
    # end_date = models.DateTimeField(default=timezone.now)
    date = DateRangeField(null=True, blank=True)
    date2 = DateTimeRangeField(null=True, blank=True)
    price = models.IntegerField(default=0)

    class Meta:
        db_table = 'tourism'


class Ad(models.Model):
    def __str__(self):
        return self.title['persian']

    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    title = JSONField(default=multilanguage)
    url = models.CharField(max_length=255, null=True, blank=True)
    media = models.ForeignKey(Media, on_delete=PROTECT)
    storage = models.ForeignKey(Storage, on_delete=PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'ad'


@receiver(post_delete, sender=Media)
def submission_delete(sender, instance, **kwargs):
    instance.file.delete(False)
