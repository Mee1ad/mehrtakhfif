from django.test import TestCase

from server.views.auth import *
from server.views.client.category import *
from server.views.client.home import *
from server.views.client.product import *
from server.views.client.shopping import *
from server.views.client.user import *
from server.tests.utils import *


# Get an instance of a logger


#  RequestFactory does not support middleware. Session and authentication attributes must be supplied by the test
#  itself if required for the view to function properly.

class HomeTestCase(TestCase):

    def setUp(self):
        self.user = fake_user(is_superuser=False, is_active=False)
        self.factory = RequestFactory()

    def test_test(self):
        request = self.factory.get(f'/ping')
        request = attach_request_default_attr(request, self.user)
        res = Test.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_init(self):
        request = self.factory.get(f'/init')
        request = attach_request_default_attr(request, self.user)
        res = Init.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_menu(self):
        fake_menu(), fake_menu(), fake_menu(), fake_menu()
        request = self.factory.get(f'/menu')
        request = attach_request_default_attr(request, self.user)
        res = ClientMenu.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_slider(self):
        fake_slider(), fake_slider(), fake_slider()
        request = self.factory.get(f'/slider')
        request = attach_request_default_attr(request, self.user)
        res = ClientSlider.as_view()(request, slider_type='home')
        assert 200 <= res.status_code <= 299

    def test_category_special_product(self):
        fake_special_product(), fake_special_product(), fake_special_product()
        request = self.factory.get(f'/category_special_product')
        request = attach_request_default_attr(request, self.user)
        res = ClientSpecialProduct.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_categories(self):
        fake_category(), fake_category(), fake_category(), fake_category()
        request = self.factory.get(f'/categories')
        request = attach_request_default_attr(request, self.user)
        res = Categories.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_promoted_categories(self):
        fake_category(promote=True), fake_category(promote=True), fake_category(), fake_category()
        request = self.factory.get(f'/promoted_categories')
        request = attach_request_default_attr(request, self.user)
        res = PromotedCategories.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_search(self):
        request = self.factory.get(f'/search?q=تست')
        request = attach_request_default_attr(request, self.user)
        res = ElasticSearch.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_ads(self):
        fake_ad(), fake_ad(), fake_ad(), fake_ad()
        request = self.factory.get(f'/ads')
        request = attach_request_default_attr(request, self.user)
        res = ClientAds.as_view()(request, ads_type='home')
        assert 200 <= res.status_code <= 299

    # def test_favicon(self):
    #     get('favicon', get_favicon)

    def test_permalink_id(self):
        product = fake_product()
        request = self.factory.get(f'/permalink_id')
        request = attach_request_default_attr(request, self.user)
        res = PermalinkToId.as_view()(request, permalink=product.permalink)
        assert 200 <= res.status_code <= 299


class UserTestCase(TestCase):

    def setUp(self):
        self.user = fake_user(is_superuser=False, is_active=False)
        self.factory = RequestFactory()

    def test_profile(self):
        request = self.factory.get(f'/profile')
        request = attach_request_default_attr(request, self.user)
        res = Profile.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_states(self):
        request = self.factory.get(f'/states')
        request = attach_request_default_attr(request, self.user)
        res = GetState.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_city(self):
        state = fake_state()
        fake_city(state=state)
        request = self.factory.get(f'/cities')
        request = attach_request_default_attr(request, self.user)
        res = GetCity.as_view()(request, state_id=state.id)
        assert 200 <= res.status_code <= 299

    def test_orders(self):
        invoice = fake_invoice(user=self.user)
        request = self.factory.get(f'orders?id={invoice.id}')
        request = attach_request_default_attr(request, self.user)
        res = Orders.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_orders_product(self):
        invoice = fake_invoice(user=self.user)
        invoice_storages_id = list(invoice.invoice_storages.all().values_list('id', flat=True))
        for pk in invoice_storages_id:
            request = self.factory.get(f'order/product?id={pk}')
            request = attach_request_default_attr(request, self.user)
            res = OrderProduct.as_view()(request)
            assert 200 <= res.status_code <= 299

    def test_wishlist(self):
        fake_wishlist(user=self.user)
        request = self.factory.get(f'/wishlist')
        request = attach_request_default_attr(request, self.user)
        res = WishlistView.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_address(self):
        fake_address(user=self.user)
        request = self.factory.get(f'address')
        request = attach_request_default_attr(request, self.user)
        res = AddressView.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_user_comments(self):
        fake_comment(user=self.user), fake_comment(user=self.user), fake_comment(user=self.user)
        request = self.factory.get(f'/user_comments')
        request = attach_request_default_attr(request, self.user)
        res = UserCommentView.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_invoice_details(self):
        invoice = fake_invoice(user=self.user, status=2)
        request = self.factory.get(f'/invoice_detail')
        request = attach_request_default_attr(request, self.user)
        res = InvoiceView.as_view()(request, invoice_id=invoice.id)
        assert 200 <= res.status_code <= 299


class BoxTestCase(TestCase):

    def setUp(self):
        self.user = fake_user(is_superuser=False, is_active=False)
        self.factory = RequestFactory()
        self.category = fake_category()
        self.product1 = fake_product(category=self.category)
        self.product2 = fake_product(category=self.category)
        self.product1.categories.add(self.category)
        self.product2.categories.add(self.category)

    def test_filter(self):
        request = get(f'/filter?q={self.product1.name["fa"]}')
        res = Filter.as_view()(request)
        res_data = json.loads(res.content)
        assert len(res_data['data']) > 0

    def test_filter_detail(self):
        request = get(f'/filter_detail?q={self.product1.name["fa"]}')
        res = FilterDetail.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_special_offer(self):
        request = get(f'/special_offer')
        res = ClientSpecialOffer.as_view()(request)
        assert 200 <= res.status_code <= 299

class ProductTestCase(TestCase):

    def setUp(self):
        self.user = fake_user(is_superuser=False, is_active=False)

    def test_product(self):
        category = fake_category()
        product = fake_product(category=category)
        product.categories.add(category)
        request = get(f'/product/')
        res = ProductView.as_view()(request, permalink=product.permalink)
        res_data = json.loads(res.content)
        assert 200 <= res.status_code <= 299, res_data
        request = get(f'/product/')
        res = ProductView.as_view()(request, permalink=product.id)
        assert 200 <= res.status_code <= 299

    def test_comment(self):
        product = fake_product(null=False)
        fake_comment(), fake_comment(), fake_comment(), fake_comment()
        permalink = product.permalink
        request = get(f'/comment?prp={permalink}&type=1')
        res = CommentView.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_features(self):
        product = fake_product(null=False)
        request = get(f'/features')
        res = FeatureView.as_view()(request, permalink=product.permalink)
        assert 200 <= res.status_code <= 299

    def test_product_userdata(self):
        product = fake_product(null=False)
        wishlist = fake_wishlist(product_id=product.id, user_id=self.user.id)
        request = get(f'/product_wishlist', self.user)
        res = ProductWishlist.as_view()(request, product_id=product.id)
        assert 200 <= res.status_code <= 299

    def test_related_products(self):
        product = fake_product(null=False)
        request = get(f'/related_products')
        res = RelatedProduct.as_view()(request, permalink=product.permalink)
        assert 200 <= res.status_code <= 299


class BookingTestCase(TestCase):

    def setUp(self):
        self.user = fake_user(is_superuser=False, is_active=False)

    def test_booking(self):
        invoice = fake_invoice()
        request = get(f'/booking')
        res = BookingView.as_view()(request, invoice_id=invoice.id)
        assert res.status_code == 302, res.status_code


class ShoppingTestCase(TestCase):

    def setUp(self):
        self.user = fake_user(is_superuser=False, is_active=False)

    def test_basket(self):
        fake_basket(user=self.user)
        request = get(f'/basket')
        res = BasketView.as_view()(request)
        assert 200 <= res.status_code <= 299

    def test_edit_invoice(self):
        pass

    def test_discount_code(self):
        discount_code = fake_discount_code()
        request = post(f'/discount_code', {"code": discount_code.code})
        res = DiscountCodeView.as_view()(request)
        res_data = json.loads(res.content)
        assert 200 <= res.status_code <= 299, res_data


class AuthTestCase(TestCase):

    def setUp(self):
        pass

    def test_login(self):
        request = post(f'/login', {"username": fake_phone_number()})
        res = Login.as_view()(request)
        res_data = json.loads(res.content)
        assert 200 <= res.status_code <= 299, res_data
        # post('login', {'username': '', 'password': '', 'code': ''}, Login, content_type='test')

    def test_add_device(self):
        token = fake.uuid4()
        device_id = fake.uuid4()
        request = post(f'/add_device', {'token': token, 'device_id': device_id})
        res = AddDevice.as_view()(request)
        res_data = json.loads(res.content)
        assert 200 <= res.status_code <= 299, res_data
        # test duplicate device_id

    def test_logout(self):
        request = post(f'/logout')
        res = LogoutView.as_view()(request)
        assert res.status_code == 403, res.status_code

    def test_set_password(self):
        pass


class PaymentTestCase(TestCase):

    def setUp(self):
        self.user = mixer.blend(User)
