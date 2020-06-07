from django.urls import path, include
from mtadmin.views.dashboard import *
from mtadmin.decorator import error_handler

urlpatterns = [
    path('date_product_count', error_handler(DateProductCount.as_view()), name='created_product_count'),
    path('product_count', error_handler(ProductCount.as_view()), name='product_count'),
]
