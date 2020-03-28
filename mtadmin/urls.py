from django.urls import path
from mtadmin.views.tables import *
from mtadmin.views.auth import *
from mtadmin.views.views import *
from mtadmin.decorator import error_handler

app_name = 'mtadmin'

urlpatterns = [
    path('test', error_handler(Test.as_view()), name='test'),
    path('category', error_handler(CategoryView.as_view()), name='category'),
    path('feature', error_handler(FeatureView.as_view()), name='feature'),
    path('menu', error_handler(MenuView.as_view()), name='menu'),
    path('brand', error_handler(BrandView.as_view()), name='brand'),
    path('product', error_handler(ProductView.as_view()), name='product'),
    path('storage/<int:pk>', error_handler(ProductStorage.as_view()), name='storage'),
    path('invoice', error_handler(InvoiceView.as_view()), name='invoice'),
    path('invoice_product', error_handler(InvoiceStorageView.as_view()), name='invoice_product'),
    path('special_offer', error_handler(SpecialOfferView.as_view()), name='special_offer'),
    path('special_product', error_handler(SpecialProductView.as_view()), name='special_product'),
    path('storage', error_handler(StorageView.as_view()), name='storage'),
    path('tag', error_handler(TagView.as_view()), name='tag'),
    path('token', error_handler(Token.as_view()), name='token'),
    path('media', error_handler(MediaView.as_view()), name='media'),
    path('comment', error_handler(CommentView.as_view()), name='comment'),
    path('mail', error_handler(MailView.as_view()), name='mail'),
    path('check_prices', error_handler(CheckPrices.as_view()), name='check_prices'),
    path('generate_code', error_handler(GenerateCode.as_view()), name='generate_code'),
    path('table_filter/<str:table>', error_handler(TableFilter.as_view()), name='table_filter'),
    path('roll', error_handler(CheckLoginToken.as_view()), name='get_roll'),
]
