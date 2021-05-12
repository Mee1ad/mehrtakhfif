import json
import random

from django.contrib.postgres.fields import JSONField
from django.db.models import *
from django_seed import Seed
from django_seed.guessers import FieldTypeGuesser, _timezone_format, NameGuesser
from django_seed.seeder import Seeder, ModelSeeder
from rest_framework.test import APITestCase, APIClient, APIRequestFactory

from server.models import *


class CustomFieldTypeGuesser(FieldTypeGuesser):

    def guess_format(self, field):
        """
        Returns the correct faker function based on the field type
        :param field:
        """
        faker = self.faker
        provider = self.provider
        if isinstance(field, DurationField): return lambda x: provider.duration()
        if isinstance(field, UUIDField): return lambda x: provider.uuid()

        if isinstance(field, BooleanField): return lambda x: faker.boolean()
        if isinstance(field, NullBooleanField): return lambda x: faker.null_boolean()
        if isinstance(field, PositiveSmallIntegerField): return lambda x: provider.rand_small_int(pos=True)
        if isinstance(field, SmallIntegerField): return lambda x: provider.rand_small_int()
        if isinstance(field, BigIntegerField): return lambda x: provider.rand_big_int()
        if isinstance(field, PositiveIntegerField): return lambda x: provider.rand_small_int(pos=True)
        if isinstance(field, IntegerField): return lambda x: provider.rand_small_int()
        if isinstance(field, FloatField): return lambda x: provider.rand_float()
        if isinstance(field, DecimalField): return lambda x: random.random()

        if isinstance(field, URLField): return lambda x: faker.uri()
        if isinstance(field, SlugField): return lambda x: faker.uri_page()
        if isinstance(field, IPAddressField) or isinstance(field, GenericIPAddressField):
            protocol = random.choice(['ipv4', 'ipv6'])
            return lambda x: getattr(faker, protocol)()
        if isinstance(field, EmailField): return lambda x: faker.email()
        if isinstance(field, CommaSeparatedIntegerField):
            return lambda x: provider.comma_sep_ints()

        if isinstance(field, BinaryField): return lambda x: provider.binary()
        if isinstance(field, ImageField): return lambda x: provider.file_name()
        if isinstance(field, FilePathField): return lambda x: provider.file_name()
        if isinstance(field, FileField): return lambda x: provider.file_name()

        if isinstance(field, CharField):
            if field.choices:
                return lambda x: random.choice(field.choices)[0]
            return lambda x: faker.text(field.max_length) if field.max_length >= 5 else faker.word()
        if isinstance(field, TextField): return lambda x: faker.text()

        if isinstance(field, DateTimeField):
            # format with timezone if it is active
            return lambda x: _timezone_format(faker.date_time())
        if isinstance(field, DateField): return lambda x: faker.date()
        if isinstance(field, TimeField): return lambda x: faker.time()
        if isinstance(field, JSONField): return lambda x: {'fa': faker.text(), 'ar': faker.text(), 'en': faker.text()}
        raise AttributeError(field)


class CustomSeeder(Seeder):
    def add_entity(self, model, number, customFieldFormatters=None):
        """
        Add an order for the generation of $number records for $entity.

        :param model: mixed A Django Model classname,
        or a faker.orm.django.EntitySeeder instance
        :type model: Model
        :param number: int The number of entities to seed
        :type number: integer
        :param customFieldFormatters: optional dict with field as key and
        callable as value
        :type customFieldFormatters: dict or None
        """
        if not isinstance(model, ModelSeeder):
            model = CustomModelSeeder(model)

        model.field_formatters = model.guess_field_formatters(self.faker)
        if customFieldFormatters:
            model.field_formatters.update(customFieldFormatters)

        klass = model.model
        self.entities[klass] = model
        self.quantities[klass] = number
        self.orders.append(klass)


class CustomSeed(Seed):

    @classmethod
    def seeder(cls, locale=None):
        code = cls.codename(locale)
        if code not in cls.seeders:
            faker = cls.fakers.get(code, None) or cls.faker(codename=code)
            cls.seeders[code] = CustomSeeder(faker)

        return cls.seeders[code]


class CustomModelSeeder(ModelSeeder):

    def guess_field_formatters(self, faker):
        """
        Gets the formatter methods for each field using the guessers
        or related object fields
        :param faker: Faker factory object
        """
        formatters = {}
        name_guesser = NameGuesser(faker)
        field_type_guesser = CustomFieldTypeGuesser(faker)

        for field in self.model._meta.fields:

            field_name = field.name

            if field.primary_key:
                continue

            if field.get_default():
                formatters[field_name] = field.get_default()
                continue

            if isinstance(field, (ForeignKey, ManyToManyField, OneToOneField)):
                formatters[field_name] = self.build_relation(field, field.related_model)
                continue

            if not field.choices:
                formatter = name_guesser.guess_format(field_name)
                if formatter:
                    formatters[field_name] = formatter
                    continue

            formatter = field_type_guesser.guess_format(field)
            if formatter:
                formatters[field_name] = formatter
                continue

        return formatters


class FakeTest(APITestCase):

    def test_fake(self):
        seeder = CustomSeed.seeder()
        seeder.add_entity(State, 2)
        seeder.add_entity(City, 3)
        seeder.add_entity(Address, 1)
        seeder.add_entity(User, 1)
        seeder.add_entity(Brand, 1)
        seeder.execute()
        inserted_pks = seeder.execute()
        print(inserted_pks)
        print('thats work')


# todo show disable items to admins

class AdminBaseTest(APITestCase):
    # fixtures = ["user.yaml", "group.yaml", "content_type.yaml", "permission.yaml", "box.yaml", "media.yaml"]
    fixtures = ["db.yaml"]
    client = APIClient()
    factory = APIRequestFactory()
    box = 3
    product = 1
    invoice = 107
    brand = 6
    feature = 16

    def base_get(self, url):
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def get_permalink(self):
        return self.fake.name().replace(' ', '-')

    def get_name(self):
        return {'fa': self.fake.name(), 'en': '', 'ar': ''}

    def base_create(self, data, url):
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, 201)
        try:
            return json.loads(res.content)['data']['id']
        except KeyError:
            return json.loads(res.content)['id']

    def base_read(self, url, get_query):
        res = self.client.get(url + get_query)
        self.assertEqual(res.status_code, 200)

    def base_update(self, url, data):
        res = self.client.put(url, data, format='json')
        self.assertEqual(res.status_code, 202)

    def base_delete(self, url, pk):
        res = self.client.delete(f'{url}?id={pk}')
        self.assertEqual(res.status_code, 200)

    def base_crud(self, data, url, get_query=f'?b={box}'):
        pk = self.base_create(data, url)
        data['id'] = pk
        self.base_read(url, get_query)
        self.base_update(url, data)
        self.base_delete(url, pk)


class UserGetData(AdminBaseTest):
    box_permalink = 'ghaza_noshidani_old'
    tag_permalink = 'cafe'
    category_permalink = 'غذا-خشک-گربه'
    product_permalink = 'p-23'
    basket_id = 31
    invoice_key = "5ZaBzK"
    invoice_id = 100

    def test_slider(self):
        print(Slider.objects.values_list('id', flat=True))
        # self.base_get('/slider/home')

    def test_special_offer(self):
        self.base_get('/special_offer')

    def test_box_special_product(self):
        self.base_get('/box_special_product')

    def test_special_product(self):
        self.base_get('/special_product')

    def test_best_seller(self):
        self.base_get('/best_seller')

    def test_box_with_category(self):
        self.base_get('/box_with_category')

    def test_menu(self):
        self.base_get('/menu')

    def test_suggest(self):
        self.base_get('/suggest?id=test')

    def test_ads(self):
        self.base_get('/ads')

    def test_filter(self):
        self.base_get('/filter')

    def test_filter_detail(self):
        self.base_get('/filter_detail')

    def test_features(self):
        self.base_get(f'/features?box={self.box_permalink}')

    def test_tag(self):
        self.base_get(f'/tag/{self.tag_permalink}')

    def test_category(self):
        self.base_get(f'/category/{self.category_permalink}')

    def test_product(self):
        self.base_get(f'/product/{self.product_permalink}')

    def test_comment(self):
        self.base_get(f'/comment?prp=p-23&type=1')
        self.base_get(f'/comment?prp=p-23&type=2')

    def test_relatd_products(self):
        self.base_get(f'/relatd_products/{self.product_permalink}')

    def test_basket(self):
        self.base_get('/basket')

    def test_ipg(self):
        self.base_get('/ipg')

    def test_payment(self):
        self.base_get(f'/payment/{self.basket_id}')

    def test_invoice(self):
        self.base_get(f'/invoice/{self.invoice_key}')

    def test_profile(self):
        self.base_get('/profile')

    def test_states(self):
        self.base_get('/states')

    def test_cities(self):
        self.base_get('/cities/1')

    def test_orders(self):
        self.base_get('/orders')
        self.base_get(f'/orders?id={self.invoice_id}')

    def test_trips(self):
        self.base_get('/trips')

    def test_wishlist(self):
        self.base_get('/wishlist')

        # advance filter testing
        # post product for unauthorized users
        #


# todo show disable items to admins


class AdminCrud(AdminBaseTest):

    def test_category_crud(self):
        url = '/admin/category'
        data = {'parent': None, 'box_id': self.box, 'name': self.get_name(), 'permalink': self.get_permalink(),
                'media': None}
        self.base_crud(data, url)

    def test_brand_crud(self):
        url = '/admin/brand'
        data = {'name': self.get_name(), 'permalink': self.get_permalink()}
        self.base_crud(data, url, '')

    def test_tag_crud(self):
        url = '/admin/tag'
        data = {'name': self.get_name(), 'permalink': self.get_permalink()}
        self.base_crud(data, url, '')

    def test_feature_crud(self):
        url = '/admin/feature'
        data = {'name': self.get_name(), 'type': randint(1, 3), 'value': self.get_name(), 'box_id': self.box}
        self.base_crud(data, url)

    def test_product_crud(self):
        url = '/admin/product'
        data = {'name': self.get_name(), 'type': randint(1, 5), 'brand_id': self.brand, 'thumbnail_id': 1, 'city_id': 1,
                'tags': [1], 'permalink': self.get_permalink(), 'short_description': self.get_name(), 'media': [],
                'description': self.get_name(), 'invoice_description': self.get_name(), 'location': self.get_name(),
                'categories': [1], 'box_id': self.box, 'address': self.get_name(),
                'short_address': self.get_name(), 'properties': self.get_name(), 'details': self.get_name(),
                'settings': self.get_name()}
        self.base_crud(data, url)

    def test_storage_crud(self):
        url = '/admin/storage'
        data = {'product_id': 1, 'features': [{'feature_id': self.feature, 'value': {"fvid": 1, "price": 0}},
                                              {'feature_id': self.feature, 'value': {"fvid": 2, "price": 5000}}],
                'items': [],
                'available_count': 10, 'start_price': 5,
                'final_price': 10, 'discount_price': 7, 'vip_discount_price': 6, 'available_count_for_sale': 10,
                'max_count_for_sale': 10, 'vip_max_count_for_sale': 10, 'min_count_alert': 10, 'tax_type': 'has_not',
                'start_time': 1588155505, 'title': self.get_name(), 'supplier_id': 1,
                'invoice_description': self.get_name(), 'invoice_title': self.get_name()}
        self.base_crud(data, url, get_query='?product_id=1')

    def test_supplier_cru(self):
        url = '/admin/supplier'
        data = {'first_name': self.fake.first_name(), 'last_name': self.fake.last_name(), 'username': '09015618439',
                'phone': '01333003033', 'shaba': 'IR123456789', 'meli_code': '2580859722'}
        pk = self.base_create(data, url)
        data['id'] = pk
        self.base_read(url, f'?id={pk}')
        self.base_update(url, data)

    def test_invoice_r(self):
        url = '/admin/supplier'
        self.base_read(url, '')

    def test_media_crud(self):
        res = self.client.get(f'/admin/media?b={self.box}')
        self.assertEqual(res.status_code, 200)

    #
    def test_menu_crud(self):
        url = '/admin/menu'
        self.base_crud(data, url)

    def invoice_product(self):
        # todo
        res = self.client.get(f'/invoice_product?id={self.invoice}')
        self.assertEqual(res.status_code, 200)

    def test_special_offer(self):
        res = self.client.get(f'/admin/special_offer?b={self.box}')
        self.assertEqual(res.status_code, 200)

    def test_special_product(self):
        res = self.client.get(f'/admin/special_product?b={self.box}')
        self.assertEqual(res.status_code, 200)

    def test_table_filter(self):
        res = self.client.get('/admin/table_filter/product?b=3')
        self.assertEqual(res.status_code, 200)

    def test_roll(self):
        res = self.client.get('/admin/roll')
        self.assertEqual(res.status_code, 200)

    def test_tax(self):
        res = self.client.get('/admin/tax?b=3')
        self.assertEqual(res.status_code, 200)

    def test_search(self):
        res = self.client.get('/admin/search?type=supplier&q=')
        self.assertEqual(res.status_code, 200)

    def test_settings(self):
        res = self.client.get(f'/admin/settings/box?id={self.box}')
        self.assertEqual(res.status_code, 200)
        res = self.client.get(f'/admin/settings/product?id={self.product}')
        self.assertEqual(res.status_code, 200

    def test_icon(self):
        res = self.client.get('/admin/icon/feature')
        self.assertEqual(res.status_code, 200)


class AdminCreate(BaseTests):
    def menu(self):
        res = self.client.get('admin/category', {'title': 'new idea'}, format='json')
        self.assertEqual(res.status_code, 200)
