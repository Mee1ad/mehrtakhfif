from django.urls import path
from server import tests
from server.views import auth, payment
from server.views.client import box
from server.views.client import home
from server.views.client import shopping
from server.views.client import product
from server.views.client import user

app_name = 'server'

home = [
    path('test', home.Test.as_view(), name='test'),
    path('slider', home.GetSlider.as_view(), name='slider'),
    path('special_offer', home.GetSpecialOffer.as_view(), name='special_offer'),
    path('special_product', home.GetSpecialProduct.as_view(), name='all_special_product'),
    path('best_seller', home.BestSeller.as_view(), name='best_seller'),
    path('category', home.AllCategory.as_view(), name='category'),
    path('box', home.AllBoxWithCategories.as_view(), name='box'),
    path('menu', home.GetMenu.as_view(), name='menu'),
    path('search', home.ElasticSearch.as_view(), name='search'),
    path('search2', home.Search.as_view(), name='search2'),
    path('ads', home.GetAds.as_view(), name='ads'),
    path('get_products', home.GetProducts.as_view(), name='get_products'),
]

box = [
    path('box/<str:permalink>', box.BoxView.as_view(), name='box'),
    path('special_offer/<str:name>', box.GetSpecialOffer.as_view(), name='special_offer'),
    path('special_product/<str:permalink>', box.GetSpecialProduct.as_view(), name='special_product'),
    path('best_seller/<str:permalink>', box.BestSeller.as_view(), name='best_seller'),
    path('box_detail/<str:permalink>', box.BoxDetail.as_view(), name='box_detail'),
    path('features', box.GetFeature.as_view(), name='features'),
    path('filter', box.Filter.as_view(), name='filter'),
    # path('tag/<int:pk>', box.TagView.as_view(), name='tag'),
    path('box/<str:box>/category/<str:category>', box.BoxCategory.as_view(), name='category'),
    # path('box/<str:name>', box.Filter.as_view(), name='box')
]

single = [
    path('product/<str:permalink>', product.Single.as_view(), name='single'),
    path('comment', product.CommentView.as_view(), name='comment'),
    path('related-products/<str:permalink>', product.RelatedProduct.as_view(), name='related_products'),
]

shopping = [
    path('basket', shopping.BasketView.as_view(), name='basket'),
    # path('show_codes', shopping.ShowCodes.as_view(), name='show_codes'),
]

pay = [
    path('psp', payment.IPG.as_view(), name='psp'),
    path('payment', payment.PaymentRequest.as_view(), name='payment'),
    path('callback', payment.CallBack.as_view(), name='callback'),
]

user = [
    path('profile', user.Profile.as_view(), name='profile'),
    path('get_states', user.GetState.as_view(), name='get_states'),
    path('get_cities/<int:state_id>', user.GetCity.as_view(), name='get_cities'),
    path('shopping_list', user.ShoppingList.as_view(), name='shopping_list'),
    path('wishlist', user.WishlistView.as_view(), name='wishlist'),
    path('user_comments', user.UserComment.as_view(), name='user_comments'),
    path('address', user.AddressView.as_view(), name='address')]

auth = [
    path('login', auth.Login.as_view(), name='login'),
    path('logout', auth.LogoutView.as_view(), name='logout'),
    path('activate', auth.Activate.as_view(), name='activate'),
    path('resend_code', auth.ResendCode.as_view(), name='resend_code'),
    path('reset_password', auth.SetPassword.as_view(), name='reset_password'),
    path('privacy_policy', auth.PrivacyPolicy.as_view(), name='privacy_policy'),
]

test = [
    path('add', tests.Add.as_view(), name='add'),
    path('get', tests.Get.as_view(), name='get'),
    path('delete/<str:job>', tests.Delete.as_view(), name='delete'),
]

urlpatterns = [*home, *box, *user, *shopping, *single, *auth, *pay, *test]
