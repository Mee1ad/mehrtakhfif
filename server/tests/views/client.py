from server.views.auth import *
from server.views.client.box import *
from server.views.client.home import *
from server.views.client.product import *
from server.views.client.shopping import *
from server.views.client.user import *
from server.views.payment import *
from server.tests.models import *
from ..utils import *
from rest_framework.test import RequestsClient, APIClient

# Get an instance of a logger


#  RequestFactory does not support middleware. Session and authentication attributes must be supplied by the test
#  itself if required for the view to function properly.

class HomeTestCase(TestCase):

    def setUp(self):
        pass

    def test_test(self):
        get('test', Test)

    def test_init(self):
        get('init', Init)

    def test_menu(self):
        fake_menu(5)
        get('menu', GetMenu)

    def test_slider(self):
        fake_slider(5)
        get('slider', GetSlider, slider_type='home')

    def test_box_special_product(self):
        fake_special_product(5)
        get('box_special_product', BoxesGetSpecialProduct)

    def test_box_with_category(self):
        fake_category(5)
        get('box_with_category', BoxWithCategory)

    def test_suggest(self):
        get('suggest?q=تست', Suggest)

    def test_search(self):
        get('suggest?q=تست', ElasticSearch)

    def test_ads(self):
        fake_ad(5, null=False)
        get('ads', GetAds, ads_type='home')

    # def test_favicon(self):
    #     get('favicon', get_favicon)

    def test_permalink_id(self):
        product = fake_product()
        get('permalink_id', PermalinkToId, permalink=product.permalink)


class UserTestCase(TestCase):

    def setUp(self):
        self.user = mixer.blend(User)

    def test_profile(self):
        get('profile', Profile)

    def test_states(self):
        get('states', GetState, user=self.user)

    def test_city(self):
        state = fake_state()
        fake_city(5, state=state)
        get(f'cities/{state.id}', GetCity, user=self.user, state_id=state.id)

    def test_orders(self):
        invoice = fake_invoice(user=self.user)
        get(f'orders?id={invoice.id}', Orders, self.user)

    def test_orders_product(self):
        invoice = fake_invoice(user=self.user)
        invoice_storages_id = list(invoice.invoice_storages.all().values_list('id', flat=True))
        for pk in invoice_storages_id:
            get(f'order/product?id={pk}', OrderProduct, self.user)

    def test_wishlist(self):
        fake_wishlist(5, user=self.user)
        get(f'wishlist', WishlistView, self.user)

    def test_address(self):
        fake_address(3, user=self.user)
        get(f'address', AddressView, self.user)

    def test_user_comments(self):
        fake_comment(5, user=self.user)
        get(f'user_comments', UserCommentView, self.user)

    def test_invoice_details(self):
        invoice = fake_invoice(user=self.user, status=2)
        get(f'invoice_detail/{invoice.id}', InvoiceView, self.user, html=True, invoice_id=invoice.id)


class BoxTestCase(TestCase):

    def setUp(self):
        self.user = mixer.blend(User)

    def test_filter(self):
        fake_product(10, null=False)
        get('filter', Filter)
        get('filter?q=رز', Filter)

    def test_filter_detail(self):
        fake_product(10, null=False)
        get('filter_detail', FilterDetail)
        get('filter_detail?q=رز', FilterDetail)

    def test_category(self):
        categories = fake_category(5, null=False)
        products = fake_product(10, null=False)
        for product in products:
            product.categories.add(categories[0])
        get(f'category', CategoryView, permalink=categories[0].permalink)


class ProductTestCase(TestCase):

    def setUp(self):
        self.user = mixer.blend(User)

    def test_filter(self):
        product = fake_product(null=False)
        get('product', ProductView, permalink=product.permalink)
        get('product', ProductView, permalink=product.id)

    def test_comment(self):
        product = fake_product(null=False)
        fake_comment(10, product=product)
        permalink = product.permalink
        get(f'comment?prp={permalink}', ProductView)

    def test_features(self):
        product = fake_product(null=False)
        get(f'features', FeatureView, permalink=product.permalink)

    def test_product_userdata(self):
        product = fake_product(null=False)
        get(f'product_userdata', ProductUserData, permalink=product.permalink)

    def test_related_products(self):
        product = fake_product(null=False)
        get('related_products', RelatedProduct, permalink=product.permalink)


class BookingTestCase(TestCase):

    def setUp(self):
        self.user = mixer.blend(User)

    def test_booking(self):
        invoice = fake_invoice()
        get('booking', BookingView, invoice_id=invoice.id)


class ShoppingTestCase(TestCase):

    def setUp(self):
        self.user = mixer.blend(User)

    def test_basket(self):
        fake_basket(user=self.user)
        get('basket', BasketView)

    def test_edit_invoice(self):
        invoice = fake_invoice(user=self.user)
        get('edit_invoice', EditInvoice, invoice_id=invoice.id)

    def test_product(self):
        storages = fake_storage(5)
        basket = [{"id": storage.id, "count": fake.random_int(1, 5)} for storage in storages]
        post('product', {"basket": basket}, GetProducts)

    def test_discount_code(self):
        discount_code = fake_discount_code()
        post('product', {"code": discount_code.code}, DiscountCodeView)


class AuthTestCase(TestCase):

    def setUp(self):
        pass

    def login(self):
        factory = RequestFactory()
        request = factory.post(f'/login', {"username": "09015518484"}, HTTP_USER_AGENT='Mozilla/5.0')
        res = Login.as_view()(request)
        print(res.status_code)
        print(res.headers)
        # post('login', {"username": "09015518484"}, Login, headers={"content_type": "test"})
        # post('login', {'username': '', 'password': '', 'code': ''}, Login, content_type='test')

    def add_device(self):
        token = fake.uuid4()
        device_id = fake.uuid4()
        post('add_device', {'token': token, 'device_id': device_id}, AddDevice)
        post('add_device', {'token': token, 'device_id': device_id}, AddDevice)  # test duplicate device_id

    def logout(self):
        fake_basket(user=self.user)
        get('basket', BasketView)

    def set_password(self):
        fake_basket(user=self.user)
        get('basket', BasketView)

