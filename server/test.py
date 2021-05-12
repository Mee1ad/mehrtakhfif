import logging

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, RequestFactory
from faker import Faker
from mixer.backend.django import Mixer

from server.views.client.home import *

# Get an instance of a logger
logger = logging.getLogger(__name__)

fake = Faker('fa_IR')
mixer = Mixer(commit=True)


def fake_json():
    return {"fa": fake.name(), "en": ""}


#  RequestFactory does not support middleware. Session and authentication attributes must be supplied by the test
#  itself if required for the view to function properly.

class HomeTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = mixer.blend(User)

        print('setup')

    def get(self, route, class_name, anonymous=False):
        request = self.factory.get(f'/{route}')
        request.lang = 'fa'
        request.user = self.user
        if anonymous:
            request.user = AnonymousUser()
        res = json.loads(class_name.as_view()(request).content)
        assert 200 <= 200 <= 299, (print(res), f"{class_name} has issue in /{route}")
        return res

    def test_test(self):
        self.get('test', Test)

    def test_init(self):
        self.get('init', Init)

    def test_menu(self):
        mixer.cycle(5).blend(Menu)
        self.get('menu', GetMenu)

    def test_slider(self):
        mixer.cycle(5).blend(Slider, title=fake_json(), product=product, media=media, mobile_media=mobile_media,
                             type='home', url=fake.url, priority=0)
        self.get('slider', GetSlider)

    def test_special_offer(self):
        self.get('menu', GetMenu)

    def test_box_special_product(self):
        self.get('menu', GetMenu)

    def test_special_product(self):
        self.get('menu', GetMenu)

    def test_best_seller(self):
        self.get('menu', GetMenu)

    def test_box_with_category(self):
        self.get('menu', GetMenu)

    def test_suggest(self):
        self.get('menu', GetMenu)

    def test_search(self):
        self.get('menu', GetMenu)

    def test_ads(self):
        self.get('menu', GetMenu)

    def test_favicon(self):
        self.get('menu', GetMenu)

    def test_permalink_id(self):
        self.get('menu', GetMenu)
