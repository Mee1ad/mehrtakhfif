from django.urls import path, include
from mtadmin.views.tables import *
from mtadmin.views.views import *
from mtadmin.views.dashboard import *
from mtadmin.decorator import error_handler

app_name = 'mtadmin'

urlpatterns = [
    # path('test2', error_handler(Test2.as_view()), name='test2'),
    # path('test3', error_handler(Test3.as_view()), name='test3'),
    path('box', error_handler(BoxView.as_view()), name='box'),
    path('category', error_handler(CategoryView.as_view()), name='category'),
    path('feature', error_handler(FeatureView.as_view()), name='feature'),
    path('feature_value', error_handler(FeatureValueView.as_view()), name='feature_value'),
    path('feature_group', error_handler(FeatureGroupView.as_view()), name='feature_group'),
    path('menu', error_handler(MenuView.as_view()), name='menu'),
    path('brand', error_handler(BrandView.as_view()), name='brand'),
    path('product', error_handler(ProductView.as_view()), name='product'),
    path('product_feature', error_handler(ProductFeatureView.as_view()), name='product_feature'),
    path('house', error_handler(HouseView.as_view()), name='house'),
    path('invoice', error_handler(InvoiceView.as_view()), name='invoice'),
    path('invoice_product', error_handler(InvoiceProductView.as_view()), name='invoice_product'),
    path('special_offer', error_handler(SpecialOfferView.as_view()), name='special_offer'),
    path('special_product', error_handler(SpecialProductView.as_view()), name='special_product'),
    path('storage', error_handler(StorageView.as_view()), name='storage'),
    path('package', error_handler(PackageView.as_view()), name='package'),
    path('tag', error_handler(TagView.as_view()), name='tag'),
    path('tag_group', error_handler(TagGroupView.as_view()), name='tag_group'),
    path('token', error_handler(Token.as_view()), name='token'),
    path('media', error_handler(MediaView.as_view()), name='media'),
    path('comment', error_handler(CommentView.as_view()), name='comment'),
    path('mail', error_handler(MailView.as_view()), name='mail'),
    path('check_prices', error_handler(CheckPrices.as_view()), name='check_prices'),
    path('discount_code', error_handler(DiscountCodeView.as_view()), name='discount_code'),
    path('table_filter/<str:table>', error_handler(TableFilter.as_view()), name='table_filter'),
    path('roll', error_handler(CheckLoginToken.as_view()), name='get_roll'),
    path('tax', error_handler(Tax.as_view()), name='tax'),
    path('search', error_handler(Search.as_view()), name='search'),
    path('settings/<str:model>', error_handler(BoxSettings.as_view()), name='settings'),
    path('supplier', error_handler(SupplierView.as_view()), name='supplier'),
    path('snapshot', error_handler(Snapshot.as_view()), name='snapshot'),
    path('icon/<str:key>', error_handler(Icon.as_view()), name='icon'),
    path('vip_price', error_handler(VipPriceView.as_view()), name='vip_Price'),
    path('vip_type', error_handler(VipTypeView.as_view()), name='vip_type'),
    path('ads', error_handler(AdsView.as_view()), name='ads'),
    path('slider', error_handler(SliderView.as_view()), name='slider'),
    path('recipient_info', error_handler(RecipientInfo.as_view()), name='recipient_info'),

    path('tg_login', error_handler(TelegramLogin.as_view()), name='tg_login'),
    path('tg_register', error_handler(TelegramRegister.as_view()), name='tg_register'),

]
