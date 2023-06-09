from django.urls import path
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from server.decorators import try_except
from server.views.auth import *
from server.views.client.category import *
from server.views.client.home import *
from server.views.client.product import *
from server.views.client.shopping import *
from server.views.client.user import *
from server.views.payment import *

try:
    from .urls_test import urls
except ModuleNotFoundError:
    urls = []

app_name = 'server'


def get_favicon(request):
    return HttpResponseRedirect('https://mehrtakhfif.com/drawable/icons/mt/favicon.ico')


def cache_proxy(func, key, minutes=5, cached=True):
    name = re.match(r'(?P<route>\w+/?\w+)/?(?P<var><.*)?', key).group('route')
    # if DEBUG or not cached:
    return path(key, (try_except(func)), name=name)
    # return path(key, cache_page(60 * minutes, key_prefix=name)(try_except((vary_on_headers())(func))), name=name)


#  10: day, 20: month
lvl = {0: 1, 1: 5, 2: 10, 3: 15, 4: 30, 5: 60, 6: 120, 7: 180, 8: 360, 9: 720, 10: 1440, 20: 2592000}

home = [
    cache_proxy(PingView.as_view(), 'ping', lvl[9]),
    # path('n/<int:pk>', try_except(NotifTest.as_view()), name='n'),
    path('init', try_except(Init.as_view()), name='init'),  # no cache
    cache_proxy(ClientSlider.as_view(), 'slider', lvl[6], False),
    cache_proxy(ClientSpecialOffer.as_view(), 'special_offer', lvl[6]),
    cache_proxy(ClientSpecialProduct.as_view(), 'special_product', lvl[6]),
    cache_proxy(LimitedSpecialProduct.as_view(), 'limited_special_product', lvl[4]),
    path('categories', try_except(Categories.as_view()), name='categories'),  # not for admin
    path('promoted_categories', try_except(PromotedCategories.as_view()), name='promoted_categories'),  # not for admin
    # path('menu', cache_page(60 * 5)(try_except(ClientMenu.as_view())), name='menu'),
    cache_proxy(ClientMenu.as_view(), 'menu', lvl[9]),
    cache_proxy(ElasticSearch.as_view(), 'search', lvl[9]),
    cache_proxy(ClientAds.as_view(), 'ads', lvl[9], False),
    cache_proxy(get_favicon, 'favicon', lvl[10]),
    cache_proxy(PermalinkToId.as_view(), 'permalink_id/<str:permalink>', lvl[10]),
]

category = [
    cache_proxy(Filter.as_view(), 'filter', lvl[5]),
    # path('special_offer/<str:name>', ClientSpecialOffer.as_view(), name='special_offer'),
    # path('special_product/<str:permalink>', GetSpecialProduct.as_view(), name='special_product'),
    cache_proxy(FilterDetail.as_view(), 'filter_detail', lvl[5]),
    # path('features', try_except(GetFeature.as_view()), name='features'),
]

product = [
    cache_proxy(ProductView.as_view(), 'product/<str:permalink>', lvl[10]),
    cache_proxy(CommentView.as_view(), 'comment', lvl[1]),
    path('product_wishlist/<int:product_id>', try_except(ProductWishlist.as_view()), name='product_wishlist'),
    path('features/<str:permalink>', try_except(FeatureView.as_view()), name='features'),  # no cache
    cache_proxy(RelatedProduct.as_view(), 'related_products/<str:permalink>', lvl[7]),
]

tourism = [
    path('booking', try_except(BookingView.as_view()), name='booking'),
    path('booking/<int:invoice_id>', try_except(BookingView.as_view()), name='booking')  # no cache
]

shopping = [
    path('basket', try_except(BasketView.as_view()), name='basket'),  # no cache
    path('edit_invoice/<str:invoice_id>', try_except(EditInvoice.as_view()), name='edit_invoice'),
    # path('show_codes', ShowCodes.as_view(), name='show_codes'),
    path('discount_code', try_except(DiscountCodeView.as_view()), name='discount_code')
]

pay = [
    cache_proxy(IPG.as_view(), 'ipg', lvl[20]),
    path('payment/<int:basket_id>', try_except(PaymentRequest.as_view()), name='payment'),
    path('repay/<int:invoice_id>', try_except(RePayInvoice.as_view()), name='repay'),
    path('payment/callback', try_except(CallBack.as_view()), name='callback'),
    path('invoice/<str:key>', try_except(ShortLinkView.as_view()), name='invoice'),
]

user = [
    path('profile', try_except(Profile.as_view()), name='profile'),
    cache_proxy(GetState.as_view(), 'states', lvl[20]),
    cache_proxy(GetCity.as_view(), 'cities/<int:state_id>', lvl[20]),
    path('orders', try_except(Orders.as_view()), name='orders'),
    cache_proxy(OrderProduct.as_view(), 'order/product', lvl[10]),  # vary by user
    path('wishlist', try_except(WishlistView.as_view()), name='wishlist'),
    # path('avatar', try_except(Avatar.as_view()), name='avatar'),
    path('address', try_except(AddressView.as_view()), name='address'),
    path('user_comments', try_except(UserCommentView.as_view()), name='user_comments'),
    path('user_products', try_except(UserProductsView.as_view()), name='user_products'),
    cache_proxy(InvoiceView.as_view(), 'invoice_detail/<int:invoice_id>', lvl[10])  # vary by user
]

auth = [
    path('login', try_except(Login.as_view()), name='login'),
    path('add_device', try_except(AddDevice.as_view()), name='add_device'),
    path('logout', try_except(LogoutView.as_view()), name='logout'),
    path('send_code', try_except(SendCode.as_view()), name='send_code'),
    path('set_password', try_except(SetPassword.as_view()), name='set_password'),
]
urlpatterns = [*home, *category, *user, *shopping, *product, *tourism, *auth, *pay, *urls]
