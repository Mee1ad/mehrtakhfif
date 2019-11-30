from django.urls import path
from server.views import auth, payment
from django.views.decorators.cache import cache_page
from server.views.client import home
from server.views.client import box
from server.views.client import single
from server.views.client import user
from server.views.client import shopping
from server.views.client import blog

app_name = 'server'

home = [path('test', home.Test.as_view(), name='test'),
        path('slider', home.GetSlider.as_view(), name='slider'),
        path('special_offer', home.GetSpecialOffer.as_view(), name='special_offer'),
        path('special_product', home.GetSpecialProduct.as_view(), name='special_product'),
        path('all_special_product', home.AllSpecialProduct.as_view(), name='all_special_product'),
        path('category', home.AllCategory.as_view(), name='category'),
        path('menu', home.GetMenu.as_view(), name='menu'),
        path('search', home.Search.as_view(), name='search'),
        path('ads', home.GetAds.as_view(), name='ads'),
        path('get_products', home.GetProducts.as_view(), name='get_products'),
        ]

box = [
        path('box/<str:name>', box.BoxView.as_view(), name='box'),
        path('special_offer/<str:name>', box.GetSpecialOffer.as_view(), name='special_offer'),
        path('box_detail/<str:key>', box.BoxDetail.as_view(), name='box_detail'),
        path('filter', box.Filter.as_view(), name='filter'),
        # path('tag/<int:pk>', box.TagView.as_view(), name='tag'),
        path('box/<str:box>/category/<str:category>', box.BoxCategory.as_view(), name='category'),
        # path('box/<str:name>', box.Filter.as_view(), name='box')
]

single = [path('single/<int:pk>', single.Single.as_view(), name='single'),
          path('comment', single.CommentView.as_view(), name='comment')]

shopping = [
        path('basket', shopping.BasketView.as_view(), name='basket'),
        # path('show_codes', shopping.ShowCodes.as_view(), name='show_codes'),
]

pay = [
        path('psp', payment.PSP.as_view(), name='psp'),
        path('payment', payment.PaymentRequest.as_view(), name='payment'),
        path('callback', payment.CallBack.as_view(), name='callback'),
]

user = [path('profile', user.Profile.as_view(), name='profile'),
        path('get_states', user.GetState.as_view(), name='get_states'),
        path('get_cities/<int:state_id>', user.GetCity.as_view(), name='get_cities'),
        path('wishlist', user.WishlistView.as_view(), name='wishlist'),
        path('address', user.AddressView.as_view(), name='address')]

auth = [path('login', auth.Login.as_view(), name='login'),
        path('logout', auth.LogoutView.as_view(), name='logout'),
        path('activate', auth.Activate.as_view(), name='activate'),
        path('resend_code', auth.ResendCode.as_view(), name='resend_code'),
        path('reset_password', auth.SetPassword.as_view(), name='reset_password'),
        path('privacy_policy', auth.PrivacyPolicy.as_view(), name='privacy_policy'),
        ]

urlpatterns = [*home, *box, *user, *shopping, *single, *auth, *pay]
