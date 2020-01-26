from django.urls import path
from admin.view import *
from admin.decorator import error_handler

app_name = 'admin_panel'

urlpatterns = [
    # path('test', Test.as_view(), name='test'),

    path('blog', error_handler(BlogView.as_view()), name='blog'),
    path('blog_post', error_handler(BlogPostView.as_view()), name='blog_post'),
    path('category', error_handler(CategoryView.as_view()), name='category'),
    path('feature', error_handler(FeatureView.as_view()), name='feature'),
    path('menu', error_handler(MenuView.as_view()), name='menu'),
    path('product', error_handler(ProductView.as_view()), name='product'),
    path('special_offer', error_handler(SpecialOfferView.as_view()), name='special_offer'),
    path('special_product', error_handler(SpecialProductsView.as_view()), name='special_product'),
    path('storage', error_handler(StorageView.as_view()), name='storage'),
    path('tag', error_handler(TagView.as_view()), name='tag'),
    path('token', error_handler(Token.as_view()), name='token'),
    path('media', error_handler(MediaView.as_view()), name='media'),
]

# todo make reference for response codes
