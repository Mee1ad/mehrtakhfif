from django.urls import path, include
from admin.views import create as c
from admin.views import read as r
from admin.views import update as u
from admin.views import delete as d
from admin.views import upload
from django.views.decorators.cache import cache_page

app_name = 'admin_panel'

delete = [
    path('category/<int:pk>', d.DeleteCategory.as_view(), name='delete_category'),
    path('delete_address/<int:pk>', d.DeleteAddress.as_view(), name='delete_address'),
    path('delete_blog/<int:pk>', d.DeleteBlog.as_view(), name='delete_blog'),
    path('delete_blog_post/<int:pk>', d.DeleteBlogPost.as_view(), name='delete_blog_post'),
    path('delete_feature/<int:pk>', d.DeleteFeature.as_view(), name='delete_feature'),
    path('delete_feature_data/<int:pk>', d.DeleteFeatureData.as_view(), name='delete_feature_data'),
    path('delete_menu/<int:pk>', d.DeleteMenu.as_view(), name='delete_menu'),
    path('delete_product/<int:pk>', d.DeleteProduct.as_view(), name='delete_product'),
    path('delete_special_offer/<int:pk>', d.DeleteSpecialOffer.as_view(), name='delete_special_offer'),
    path('delete_special_product/<int:pk>', d.DeleteSpecialProducts.as_view(), name='delete_special_product'),
    path('delete_storage/<int:pk>', d.DeleteStorage.as_view(), name='delete_storage'),
    path('delete_tag/<int:pk>', d.DeleteTag.as_view(), name='delete_tag'),
]

urlpatterns = [
    path('delete/', include(delete)),

    path('upload', upload.BoxMedia.as_view(), name='upload'),

    path('create_category', c.NewCategory.as_view(), name='create_user'),
    path('create_address', c.NewAddress.as_view(), name='create_user'),
    path('create_user', c.NewBlog.as_view(), name='create_user'),
    path('create_user', c.NewBlogPost.as_view(), name='create_user'),
    path('create_user', c.NewFeature.as_view(), name='create_user'),
    path('create_user', c.NewMenu.as_view(), name='create_user'),
    path('create_user', c.NewProduct.as_view(), name='create_user'),
    path('create_user', c.NewSpecialOffer.as_view(), name='create_user'),
    path('create_user', c.NewSpecialProducts.as_view(), name='create_user'),
    path('create_user', c.NewStorage.as_view(), name='create_user'),
    path('create_user', c.NewTag.as_view(), name='create_user'),

    path('get_category', r.GetCategory.as_view(), name='get_category'),
    path('get_category', r.GetAddress.as_view(), name='get_category'),
    path('get_category', r.GetBlog.as_view(), name='get_category'),
    path('get_category', r.GetBlogPost.as_view(), name='get_category'),
    path('get_category', r.GetFeature.as_view(), name='get_category'),
    path('get_category', r.GetMenu.as_view(), name='get_category'),
    path('get_category', r.GetProduct.as_view(), name='get_category'),
    path('get_category', r.GetSpecialOffer.as_view(), name='get_category'),
    # path('get_category', r.BoxesGetSpecialProducts.as_view(), name='get_category'),
    path('get_category', r.GetStorage.as_view(), name='get_category'),
    path('get_category', r.GetTag.as_view(), name='get_category'),
    path('get_category', r.GetTourism.as_view(), name='get_category'),

    path('update_address/<int:pk>', u.UpdateAddress.as_view(), name='delete_category'),
    path('update_blog/<int:pk>', u.UpdateBlog.as_view(), name='delete_category'),
    path('update_blog_post/<int:pk>', u.UpdateBlogPost.as_view(), name='delete_category'),
    path('update_category/<int:pk>', u.UpdateCategory.as_view(), name='delete_category'),
    path('update_feature/<int:pk>', u.UpdateFeature.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateMenu.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateProduct.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateSpecialOffer.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateSpecialProducts.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateStorage.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateTag.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateTourism.as_view(), name='delete_category'),
]
