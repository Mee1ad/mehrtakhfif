from django.urls import path
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from server.decorators import try_except
from server.views.auth import *
from server.views.client.box import *
from server.views.client.home import *
from server.views.client.product import *
from server.views.client.shopping import *
from server.views.client.user import *
from server.views.payment import *
from django.contrib.sitemaps.views import sitemap
from .sitemap import *
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
    cache_proxy(Test.as_view(), 'ping', lvl[9]),
    # path('n/<int:pk>', try_except(NotifTest.as_view()), name='n'),
    path('init', try_except(Init.as_view()), name='init'),  # no cache
    cache_proxy(GetSlider.as_view(), 'slider/<str:slider_type>', lvl[6], False),
    cache_proxy(GetSpecialOffer.as_view(), 'special_offer', lvl[6]),
    cache_proxy(BoxesGetSpecialProduct.as_view(), 'box_special_product', lvl[6]),
    cache_proxy(GetSpecialProduct.as_view(), 'special_product', lvl[6]),
    cache_proxy(BestSeller.as_view(), 'best_seller', lvl[6]),
    path('box_with_category', try_except(BoxWithCategory.as_view()), name='box_with_category'),  # not for admin
    path('categories', try_except(Categories.as_view()), name='categories'),  # not for admin
    # path('menu', cache_page(60 * 5)(try_except(GetMenu.as_view())), name='menu'),
    cache_proxy(GetMenu.as_view(), 'menu', lvl[9]),
    cache_proxy(Suggest.as_view(), 'suggest', lvl[9]),
    cache_proxy(ElasticSearch.as_view(), 'search', lvl[9]),
    cache_proxy(GetAds.as_view(), 'ads/<str:ads_type>', lvl[9], False),
    cache_proxy(get_favicon, 'favicon', lvl[10]),
    cache_proxy(PermalinkToId.as_view(), 'permalink_id/<str:permalink>', lvl[10]),
]

box = [
    cache_proxy(Filter.as_view(), 'filter', lvl[5]),
    # path('special_offer/<str:name>', GetSpecialOffer.as_view(), name='special_offer'),
    # path('special_product/<str:permalink>', GetSpecialProduct.as_view(), name='special_product'),
    cache_proxy(FilterDetail.as_view(), 'filter_detail', lvl[5]),
    # path('features', try_except(GetFeature.as_view()), name='features'),
    cache_proxy(CategoryView.as_view(), 'category/<str:permalink>', lvl[5]),
]

product = [
    cache_proxy(ProductView.as_view(), 'product/<str:permalink>', lvl[10]),
    cache_proxy(CommentView.as_view(), 'comment', lvl[1]),
    path('product_wishlist/<int:product_id>', try_except(ProductWishlist.as_view()), name='product_wishlist'),
    path('features/<str:permalink>', try_except(FeatureView.as_view()), name='features'),  # no cache
    path('product_userdata/<str:permalink>', try_except(ProductUserData.as_view()), name='features'),  # no cache
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
    cache_proxy(InvoiceView.as_view(), 'invoice_detail/<int:invoice_id>', lvl[10])  # vary by user
]

auth = [
    path('login', try_except(Login.as_view()), name='login'),
    path('add_device', try_except(AddDevice.as_view()), name='add_device'),
    path('logout', try_except(LogoutView.as_view()), name='logout'),
    path('send_code', try_except(SendCode.as_view()), name='send_code'),
    path('set_password', try_except(SetPassword.as_view()), name='set_password'),
]

sitemap = [path('sitemap.xml', sitemap, {'sitemaps': {'sitemaps': BaseSitemap}},
                name='django.contrib.sitemaps.views.sitemap'),
           path('product-sitemap.xml', sitemap, {'sitemaps': {'product': ProductSitemap}},
                name='django.contrib.sitemaps.views.sitemap'),
           path('category-sitemap.xml', sitemap, {'sitemaps': {'category': CategorySitemap}},
                name='django.contrib.sitemaps.views.sitemap'),
           path('tag-sitemap.xml', sitemap, {'sitemaps': {'tag': TagSitemap}},
                name='django.contrib.sitemaps.views.sitemap')]
urlpatterns = [*home, *box, *user, *shopping, *product, *tourism, *auth, *pay, *urls, *sitemap]
