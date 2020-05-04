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

    def get_name(self):
        return {'fa': self.fake.name(), 'en': '', 'ar': ''}

    def base_create(self, data, url):
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, 201)
        try:
            return json.loads(res.content)['data']['id']
        except KeyError:
            return json.loads(res.content)['id']

    def base_get(self, urls, get_query):
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200)


class UserGetData(AdminBaseTest):

    def test_get_data(self):
        pass
        # res = self.client.get('/slider/home')
        # self.assertEqual(res.status_code, 200)
        # res = self.client.get('special_offer')
        # self.assertEqual(res.status_code, 200)
        # res = self.client.get('/box_special_product')
        # self.assertEqual(res.status_code, 200)
        # res = self.client.get('/special_product')
        # self.assertEqual(res.status_code, 200)
        # res = self.client.get('/best_seller')
        # self.assertEqual(res.status_code, 200)
        # res = self.client.get('/box_with_category')
        # self.assertEqual(res.status_code, 200)
        # res = self.client.get('/menu')
        # self.assertEqual(res.status_code, 200)
        # res = self.client.get('/suggest?id="test"')
        # self.assertEqual(res.status_code, 200)
        # res = self.client.get('/ads')
        # self.assertEqual(res.status_code, 200)
        # res = self.client.get('/slider/home')
        # self.assertEqual(res.status_code, 200)
