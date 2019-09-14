from django.urls import path
from server.views.auth import *
from django.views.decorators.cache import cache_page
from server.views.client.home import *
from server.views.client.box import *
from server.views.client.single import *
from server.views.client.user import *
from server.views.client.shopping import *
from server.views.client.blog import *

app_name = 'server'

home = [path('test', Test.as_view(), name='test'),
        path('error', Error.as_view(), name='error'),
        path('slider', GetSlider.as_view(), name='slider'),
        path('special_offer', GetSpecialOffer.as_view(), name='special_offer'),
        path('special_product', GetSpecialProduct.as_view(), name='special_product'),
        path('all_special_product', AllSpecialProduct.as_view(), name='all_special_product'),
        path('menu', GetMenu.as_view(), name='menu'),
        path('search', Search.as_view(), name='search')]
box = [path('box/<int:pk>', BoxView.as_view(), name='box'),
       path('box_detail/<int:pk>', BoxDetail.as_view(), name='box_detail'),
       path('category/<int:pk>', CategoryView.as_view(), name='category'),
       path('tag/<int:pk>', TagView.as_view(), name='tag')]
single = [path('single/<int:pk>', Single.as_view(), name='single')]
shopping = [path('buy', Buy.as_view(), name='buy')]
user = []
blog = []
auth = [path('signup', Signup.as_view(), name='signup'),
        path('login', Login.as_view(), name='login'),
        path('activate', Activate.as_view(), name='activate'),
        path('resend_code', ResendCode.as_view(), name='resend_code'),
        path('reset_password_request', ResetPasswordRequest.as_view(), name='reset_password_request'),
        path('reset_password', ResetPassword.as_view(), name='reset_password')]

urlpatterns = [path('home/', home)]
