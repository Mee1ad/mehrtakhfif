from django.urls import path
from server.views.auth import *
from django.views.decorators.cache import cache_page
from server.views.client.home import *

app_name = 'server'

urlpatterns = [
    path('test', Test.as_view(), name='test'),
    path('error', Error.as_view(), name='error'),

    path('signup', Signup.as_view(), name='signup'),
    path('login', Login.as_view(), name='login'),
    path('activate', Activate.as_view(), name='activate'),
    path('resend_code', ResendCode.as_view(), name='resend_code'),
    path('reset_password_request', ResetPasswordRequest.as_view(), name='reset_password_request'),
    path('reset_password', ResetPassword.as_view(), name='reset_password'),

    path('home', Home.as_view(), name='home'),
    path('box/<int:pk>', BoxView.as_view(), name='box'),
    path('category/<int:pk>', CategoryView.as_view(), name='category'),
    path('tag/<int:pk>', TagView.as_view(), name='tag'),
    path('single/<int:pk>', Single.as_view(), name='single'),
    path('profile', Profile.as_view(), name='profile'),
    path('comment', CommentView.as_view(), name='comment'),
    path('wishlist', WishlistView.as_view(), name='wishlist'),
    path('buy', Buy.as_view(), name='buy'),
]
