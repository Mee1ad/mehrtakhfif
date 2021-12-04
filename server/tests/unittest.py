import datetime

from django.test import TestCase
from server.utils import *
from base64 import b64decode
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import StringIO
from django.http import QueryDict
from server.tests.models import *
import jdatetime


# models test
class UtilsTest(TestCase):

    def test_add_minutes(self):
        ten_min_later = add_minutes(10)
        self.assertIsInstance(ten_min_later, datetime.datetime)

    def test_to_jalali(self):
        dt = timezone.now()
        dt = to_jalali(dt)
        self.assertIsInstance(dt, jdatetime.datetime)

    def test_add_days(self):
        tomorrow = add_days(1)
        self.assertIsInstance(tomorrow, datetime.datetime)

    def test_get_mimetype(self):
        print('test_get_mimetype', "404")

    def test_upload(self):
        print('test_upload', "404")

    def test_get_request_params(self):
        ordinary_dict = {'type': 'product', 'q': '', 'category_id': '385'}
        query_dict = QueryDict('', mutable=True)
        query_dict.update(ordinary_dict)
        params = get_request_params(query_dict)
        self.assertEqual(params, ordinary_dict)

    def test_load_location(self):
        location = [0, 1]
        location = load_location(location)
        self.assertIsInstance(location, dict)

    def test_safe_get(self):
        obj1 = type('Test', (), {'attr3': 'hi'})()
        obj2 = type('Test', (), {'attr2': obj1})()
        obj3 = type('Test', (), {'attr1': obj2})()
        attr3 = safe_get(obj3, 'attr1', 'attr2', 'attr3')
        attr4 = safe_get(obj3, 'attr1', 'attr2', 'attr3', 'attr4')
        self.assertEqual(attr3, 'hi')
        self.assertEqual(attr4, None)

    def test_get_share_of_storage(self):
        invoice = fake_invoice()
        invoice_storage = fake_invoice_storage(invoice=invoice)[0]
        share = get_share(invoice_storage)
        self.assertIsInstance(share['mt_profit'], int)

    def test_get_share_of_invoice(self):
        invoice = fake_invoice()
        fake_invoice_storage(invoice=invoice)
        share = get_share(invoice=invoice)
        self.assertIsInstance(share['mt_profit'], int)

    def test_obj_to_json(self):
        category = fake_category()
        category_json = obj_to_json(category)
        self.assertIsInstance(category_json, dict)

    def test_move_file(self):
        print('test_move_file', "404")

    def test_dict_to_obj(self):
        data = {'one': 1, 'two': 2, 'three': 3}
        data_obj = dict_to_obj(data)
        self.assertEqual(data_obj.one, 1)

    def test_create_qr(self):
        qr = create_qr("test_string", "file_name")
        self.assertIsInstance(qr, str)

    def test_send_sms(self):
        # todo uncomment
        sms = None
        # sms = send_sms("09015518439", "verify", "123456")
        self.assertEqual(sms, None)

    def test_send_pm(self):
        pm = send_pm("312145983", "test")
        self.assertEqual(pm.status_code, 200)

    def test_send_email(self):
        email = send_email("test_subject", "soheilravasani@gmail.com", message="test_message")
        self.assertEqual(email, True)

    def test_get_discount_price(self):
        storage = fake_storage()
        discount_price = get_discount_price(storage)
        self.assertEqual(discount_price, storage.discount_price)

    def test_get_discount_percent(self):
        storage = fake_storage()
        discount_percent = get_discount_percent(storage)
        self.assertEqual(discount_percent, storage.discount_percent)

    def test_get_vip_discount_price(self):
        storage = fake_storage()
        vip_prices = [fake_vip_price(), fake_vip_price(), fake_vip_price()]
        storage.vip_prices.set(vip_prices)
        discount_price = get_discount_price(storage)
        min_price = min([storage.discount_price, vip_prices[0].discount_price, vip_prices[1].discount_price,
                         vip_prices[2].discount_price])
        self.assertEqual(discount_price, min_price)

    def test_get_vip_discount_percent(self):
        storage = fake_storage()
        vip_prices = [fake_vip_price(), fake_vip_price(), fake_vip_price()]
        storage.vip_prices.set(vip_prices)
        discount_percent = get_discount_percent(storage)
        min_price = min([storage.discount_percent, vip_prices[0].discount_percent, vip_prices[1].discount_percent,
                         vip_prices[2].discount_percent])
        self.assertEqual(discount_percent, min_price)

    def test_remove_null_from_dict(self):
        dic = {'one': 1, 'two': 2, 'tree': 3}
        print('test_remove_null_from_dict', "404")

    def test_get_preview_permission(self):
        print('test_get_preview_permission', "404")

    def test_add_to_basket(self):
        # todo accessory test
        user = fake_user()
        basket = fake_basket(user=user)
        storage = fake_storage()
        count = fake.random_int(1, 5)
        products = [{'storage_id': storage.id, 'count': count}]
        basket_count = add_to_basket(basket, products)
        self.assertEqual(basket_count, count)

    def test_make_short_link(self):
        short_link = make_short_link('test.com')
        self.assertRegex(short_link, r'https:\/\/mhrt.ir\/.*')
