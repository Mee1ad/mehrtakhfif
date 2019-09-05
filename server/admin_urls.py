from django.urls import path
from server.views.admin_panel import create as c
from server.views.admin_panel import read as r
from server.views.admin_panel import update as u
from server.views.admin_panel import delete as d
from server.views.admin_panel import upload
from django.views.decorators.cache import cache_page

app_name = 'admin_panel'

urlpatterns = [
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
    path('create_user', c.NewTourism.as_view(), name='create_user'),

    path('get_category', r.GetCategory.as_view(), name='get_category'),
    path('get_category', r.GetAddress.as_view(), name='get_category'),
    path('get_category', r.GetBlog.as_view(), name='get_category'),
    path('get_category', r.GetBlogPost.as_view(), name='get_category'),
    path('get_category', r.GetFeature.as_view(), name='get_category'),
    path('get_category', r.GetMenu.as_view(), name='get_category'),
    path('get_category', r.GetProduct.as_view(), name='get_category'),
    path('get_category', r.GetSpecialOffer.as_view(), name='get_category'),
    path('get_category', r.GetSpecialProducts.as_view(), name='get_category'),
    path('get_category', r.GetStorage.as_view(), name='get_category'),
    path('get_category', r.GetTag.as_view(), name='get_category'),
    path('get_category', r.GetTourism.as_view(), name='get_category'),

    path('delete_category/<int:pk>', u.UpdateAddress.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateBlog.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateBlogPost.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateCategory.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateFeature.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateMenu.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateProduct.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateSpecialOffer.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateSpecialProducts.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateStorage.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateTag.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', u.UpdateTourism.as_view(), name='delete_category'),

    path('delete_category/<int:pk>', d.DeleteCategory.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteAddress.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteBlog.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteBlogPost.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteFeature.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteFeatureData.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteMenu.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteProduct.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteSpecialOffer.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteSpecialProducts.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteStorage.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteTag.as_view(), name='delete_category'),
    path('delete_category/<int:pk>', d.DeleteTourism.as_view(), name='delete_category'),
]
