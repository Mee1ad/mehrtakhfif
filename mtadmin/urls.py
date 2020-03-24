from django.urls import path
from mtadmin.views.tables import *
from mtadmin.views.auth import *
from mtadmin.views.views import *
from mtadmin.decorator import error_handler

app_name = 'mtadmin'

urlpatterns = [
    # path('test', Test.as_view(), name='test'),
    path('admin/category', error_handler(CategoryView.as_view()), name='category'),
    path('admin/feature', error_handler(FeatureView.as_view()), name='feature'),
    path('admin/menu', error_handler(MenuView.as_view()), name='menu'),
    path('admin/brand', error_handler(BrandView.as_view()), name='brand'),
    path('admin/product', error_handler(ProductView.as_view()), name='product'),
    path('admin/invoice', error_handler(InvoiceView.as_view()), name='invoice'),
    path('admin/invoice_product', error_handler(InvoiceStorageView.as_view()), name='invoice_product'),
    path('admin/special_offer', error_handler(SpecialOfferView.as_view()), name='special_offer'),
    path('admin/special_product', error_handler(SpecialProductView.as_view()), name='special_product'),
    path('admin/storage', error_handler(StorageView.as_view()), name='storage'),
    path('admin/tag', error_handler(TagView.as_view()), name='tag'),
    path('admin/token', error_handler(Token.as_view()), name='token'),
    path('admin/media', error_handler(MediaView.as_view()), name='media'),
    path('admin/comment', error_handler(CommentView.as_view()), name='comment'),
    path('admin/mail', error_handler(MailView.as_view()), name='mail'),
    path('admin/check_prices', error_handler(CheckPrices.as_view()), name='check_prices'),
    path('admin/generate_code', error_handler(GenerateCode.as_view()), name='generate_code'),
    path('admin/table_filter/<str:table>', error_handler(TableFilter.as_view()), name='table_filter'),
    path('admin/get_roll', error_handler(CheckLoginToken.as_view()), name='get_roll'),
]
