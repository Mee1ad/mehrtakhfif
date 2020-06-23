from rest_framework.test import APITestCase, APIClient, APIRequestFactory
from server.models import *
from faker import Faker
from time import sleep
import json
import pysnooper
from random import randint


# todo show disable items to admins

class AdminBaseTest(APITestCase):
    fixtures = ["db.yaml"]
    # fixtures = ["user.yaml", "group.yaml", "content_type.yaml", "permission.yaml", "box.yaml", "media.yaml"]
    # fixtures = ["db.yaml", "product.yaml", "storage.yaml", "invoice.yaml", "invoice_storage.yaml",
    #             "basket.yaml"]
    client = APIClient()
    factory = APIRequestFactory()
    fake = Faker()

    def base_get(self, url):
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)


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
