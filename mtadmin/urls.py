from django.urls import path
from mtadmin.views.tables import *
from mtadmin.views.auth import *
from mtadmin.views.views import *
from mtadmin.decorator import error_handler

app_name = 'mtadmin'

urlpatterns = [
    # path('test2', error_handler(Test2.as_view()), name='test2'),
    # path('test3', error_handler(Test3.as_view()), name='test3'),
    path('category', error_handler(CategoryView.as_view()), name='category'),
    path('feature', error_handler(FeatureView.as_view()), name='feature'),
    path('menu', error_handler(MenuView.as_view()), name='menu'),
    path('brand', error_handler(BrandView.as_view()), name='brand'),
    path('product', error_handler(ProductView.as_view()), name='product'),
    path('house', error_handler(HouseView.as_view()), name='house'),
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
    path('tax', error_handler(Tax.as_view()), name='tax'),
    path('search', error_handler(Search.as_view()), name='search'),
    path('settings', error_handler(BoxSettings.as_view()), name='settings'),
    path('supplier', error_handler(Supplier.as_view()), name='supplier'),
]
