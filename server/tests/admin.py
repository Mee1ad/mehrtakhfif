from rest_framework.test import APITestCase, APIClient, APIRequestFactory
from server.models import *
from faker import Faker
from time import sleep
import json
import pysnooper
from random import randint


# todo show disable items to admins

class AdminBaseTest(APITestCase):
    # fixtures = ["user.yaml", "group.yaml", "content_type.yaml", "permission.yaml", "box.yaml", "media.yaml"]
    fixtures = ["db.yaml", "product.yaml"]
    client = APIClient()
    factory = APIRequestFactory()
    fake = Faker()
    box = 3
    product = 1
    invoice = 107
    brand = 6
    feature = 16

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

    @pysnooper.snoop()
    def base_crud(self, data, url, get_query=f'?b={box}'):
        pk = self.base_create(data, url)
        data['id'] = pk
        self.base_read(url, get_query)
        self.base_update(url, data)
        self.base_delete(url, pk)


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
    # def test_menu_crud(self):
    #     url = '/admin/menu'
    #     self.base_crud(data, url)
    #
    # def invoice_product(self):
    #     # todo
    #     res = self.client.get(f'/invoice_product?id={self.invoice}')
    #     self.assertEqual(res.status_code, 200)
    #
    # def test_special_offer(self):
    #     res = self.client.get(f'/admin/special_offer?b={self.box}')
    #     self.assertEqual(res.status_code, 200)
    #
    # def test_special_product(self):
    #     res = self.client.get(f'/admin/special_product?b={self.box}')
    #     self.assertEqual(res.status_code, 200)
    # def test_table_filter(self):
    #     res = self.client.get('/admin/table_filter/product?b=3')
    #     self.assertEqual(res.status_code, 200)
    #
    # def test_roll(self):
    #     res = self.client.get('/admin/roll')
    #     self.assertEqual(res.status_code, 200)
    #
    # def test_tax(self):
    #     res = self.client.get('/admin/tax?b=3')
    #     self.assertEqual(res.status_code, 200)
    #
    # def test_search(self):
    #     res = self.client.get('/admin/search?type=supplier&q=')
    #     self.assertEqual(res.status_code, 200)
    #
    # def test_settings(self):
    #     res = self.client.get(f'/admin/settings/box?id={self.box}')
    #     self.assertEqual(res.status_code, 200)
    #     res = self.client.get(f'/admin/settings/product?id={self.product}')
    #     self.assertEqual(res.status_code, 200
    # def test_icon(self):
    #     res = self.client.get('/admin/icon/feature')
    #     self.assertEqual(res.status_code, 200)

# class AdminCreate(BaseTests):
#     def menu(self):
#         res = self.client.get('admin/category', {'title': 'new idea'}, format='json')
#         self.assertEqual(res.status_code, 200)
