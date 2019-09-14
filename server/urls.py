from django.urls import path
from server.views.auth import *
from django.views.decorators.cache import cache_page
from server.views.client import home
from server.views.client import box
from server.views.client import single
from server.views.client import user
from server.views.client import shopping
from server.views.client import blog

app_name = 'server'

home = [path('test', Test.as_view(), name='test'),
        path('error', Error.as_view(), name='error'),
        path('slider', home.GetSlider.as_view(), name='slider'),
        path('special_offer', home.GetSpecialOffer.as_view(), name='special_offer'),
        path('special_product', home.GetSpecialProduct.as_view(), name='special_product'),
        path('all_special_product', home.AllSpecialProduct.as_view(), name='all_special_product'),
        path('menu', home.GetMenu.as_view(), name='menu'),
        path('search', home.Search.as_view(), name='search')]
box = [path('box/<int:pk>', box.BoxView.as_view(), name='box'),
       path('box_detail/<int:pk>', box.BoxDetail.as_view(), name='box_detail'),
       path('category/<int:pk>', box.CategoryView.as_view(), name='category'),
       path('tag/<int:pk>', box.TagView.as_view(), name='tag')]
single = [path('single/<int:pk>', single.Single.as_view(), name='single')]
shopping = [path('buy', shopping.Buy.as_view(), name='buy')]
user = []
blog = []
auth = [path('signup', Signup.as_view(), name='signup'),
        path('login', Login.as_view(), name='login'),
        path('activate', Activate.as_view(), name='activate'),
        path('resend_code', ResendCode.as_view(), name='resend_code'),
        path('reset_password_request', ResetPasswordRequest.as_view(), name='reset_password_request'),
        path('reset_password', ResetPassword.as_view(), name='reset_password')]

urlpatterns = [*home]
