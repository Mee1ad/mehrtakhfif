from django.urls import path

from server.decorators import try_except
from server.views.auth import *
from server.views.client.box import *
from server.views.client.home import *
from server.views.client.product import *
from server.views.client.shopping import *
from server.views.client.tourism import *
from server.views.client.user import *
from server.views.payment import *

app_name = 'server'

home = [
    path('slider/<str:slider_type>', try_except(GetSlider.as_view()), name='slider'),
    path('special_offer', try_except(GetSpecialOffer.as_view()), name='special_offer'),
    path('box_special_product', try_except(BoxesGetSpecialProduct.as_view()), name='box_special_product'),
    path('special_product', try_except(GetSpecialProduct.as_view()), name='special_product'),
    path('best_seller', try_except(BestSeller.as_view()), name='best_seller'),
    path('box_with_category', try_except(BoxWithCategory.as_view()), name='box_with_category'),
    path('menu', try_except(GetMenu.as_view()), name='menu'),
    path('search', try_except(ElasticSearch.as_view()), name='search'),
    path('search2', Search.as_view(), name='search2'),
    path('ads', try_except(GetAds.as_view()), name='ads'),
]

box = [
    path('q', try_except(BoxView.as_view()), name='box'),
    # path('special_offer/<str:name>', GetSpecialOffer.as_view(), name='special_offer'),
    # path('special_product/<str:permalink>', GetSpecialProduct.as_view(), name='special_product'),
    path('best_seller/<str:permalink>', try_except(BestSeller.as_view()), name='best_seller'),
    path('box_detail', try_except(BoxDetail.as_view()), name='box_detail'),
    path('features', try_except(GetFeature.as_view()), name='features'),
    path('tag/<str:permalink>', try_except(TagView.as_view()), name='tag'),
    path('category/<str:permalink>', try_except(CategoryView.as_view()), name='category'),
]

product = [
    path('product/<str:permalink>', try_except(ProductView.as_view()), name='single'),
    path('comment', try_except(CommentView.as_view()), name='comment'),
    path('related_products/<str:permalink>', try_except(RelatedProduct.as_view()), name='related_products'),
]

tourism = [
    path('booking', try_except(BookingView.as_view()), name='booking')
]


shopping = [
    path('basket', try_except(BasketView.as_view()), name='basket'),
    path('get_products', try_except(GetProducts.as_view()), name='get_products'),
    # path('show_codes', ShowCodes.as_view(), name='show_codes'),
]

pay = [
    path('ipg', try_except(IPG.as_view()), name='ipg'),
    path('payment/<int:basket_id>', try_except(PaymentRequest.as_view()), name='payment'),
    path('payment/callback', try_except(CallBack.as_view()), name='callback'),
    path('invoice/<str:key>', try_except(ShortLinkView.as_view()), name='invoice'),
]

user = [
    path('profile', try_except(Profile.as_view()), name='profile'),
    path('states', try_except(GetState.as_view()), name='get_states'),
    path('cities/<int:state_id>', try_except(GetCity.as_view()), name='get_cities'),
    path('orders', try_except(Orders.as_view()), name='orders'),
    path('orders/product', try_except(OrderProduct.as_view()), name='order/product'),
    path('trips', try_except(Trips.as_view()), name='trips'),
    path('wishlist', try_except(WishlistView.as_view()), name='wishlist'),
    path('avatar', try_except(Avatar.as_view()), name='avatar'),
    path('address', try_except(AddressView.as_view()), name='address'),
    path('user_comments', try_except(CommentView.as_view()), name='user_comments')
]

auth = [
    path('login', try_except(Login.as_view()), name='login'),
    path('logout', try_except(LogoutView.as_view()), name='logout'),
    path('activate', try_except(Activate.as_view()), name='activate'),
    path('resend_code', try_except(ResendCode.as_view()), name='resend_code'),
    path('reset_password', try_except(SetPassword.as_view()), name='reset_password'),
    path('privacy_policy', try_except(PrivacyPolicy.as_view()), name='privacy_policy'),
]

urlpatterns = [*home, *box, *user, *shopping, *product, *tourism, *auth, *pay]
