from django.contrib import admin
from reversion.admin import VersionAdmin
from django.contrib.auth.admin import UserAdmin
from .models import *
from safedelete.admin import SafeDeleteAdmin, highlight_deleted
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from mehr_takhfif import settings
import os
from mehr_takhfif.settings import HOST

UserAdmin.list_display += ('phone', 'updated_at')
UserAdmin.list_filter = ('username',)
UserAdmin.ordering = ('-id',)
UserAdmin.list_per_page = 10


class Base:

    @staticmethod
    def persian(obj, table='language'):
        link = reverse(f"admin:server_{table}_change", args=[obj.name.id])
        return mark_safe(f'<a href="{link}">{escape(obj.name)}</a>')


class BoxAdmin(SafeDeleteAdmin):
    list_display = ('persian', 'created_by', 'updated_at', 'deleted_by') + SafeDeleteAdmin.list_display
    list_filter = ('name',) + SafeDeleteAdmin.list_filter
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def persian(self, obj):
        return obj.name['persian']


class CategoryAdmin(SafeDeleteAdmin):
    list_display = ('parent', 'box', 'persian', 'deleted_by') + SafeDeleteAdmin.list_display
    list_filter = ('name',) + SafeDeleteAdmin.list_filter
    list_display_links = ('box',)
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def persian(self, obj):
        return obj.name['persian']


class MenuAdmin(SafeDeleteAdmin):
    list_display = ('menu_name', 'media', 'url', 'type', 'parent', 'priority') + SafeDeleteAdmin.list_display
    list_filter = ('name', 'type', 'parent') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def menu_name(self, obj):
        return obj.name['persian']
    menu_name.short_description = 'name'


class SliderAdmin(SafeDeleteAdmin):
    list_display = ('slider_title', 'type', 'url', 'product') + SafeDeleteAdmin.list_display
    list_filter = ('title', 'type') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['title']
    list_per_page = 10
    ordering = ('-created_at',)

    def slider_title(self, obj):
        return obj.title['persian']
    slider_title.short_description = 'name'

    def url(self, obj):
        return mark_safe(f'<a href="{HOST + obj.media.file.url}">{escape(obj.media.title)}</a>')
    url.short_description = 'url'


class SpecialOfferAdmin(SafeDeleteAdmin):
    list_display = ('menu_name', 'code', 'category', 'start_date', 'end_date') + SafeDeleteAdmin.list_display
    list_filter = ('name', 'code', 'box', 'product', 'category') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['name', 'code']
    list_per_page = 10
    ordering = ('-created_at',)

    def menu_name(self, obj):
        return obj.name['persian']
    menu_name.short_description = 'name'


class SpecialProductAdmin(SafeDeleteAdmin):
    list_display = ('title_persian', 'url', 'storage', 'box', 'category', 'media', 'type') + SafeDeleteAdmin.list_display
    list_filter = ('title', 'storage', 'box', 'category') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['title']
    list_per_page = 10
    ordering = ('-created_at',)

    def title_persian(self, obj):
        return obj.storage
    title_persian.short_description = 'name'


class ProductAdmin(SafeDeleteAdmin):
    list_display = ('product_name', 'category', 'gender', 'verify', 'type', 'permalink') + SafeDeleteAdmin.list_display
    list_filter = ('name', 'type', 'category') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def product_name(self, obj):
        return obj.name['persian']
    product_name.short_description = 'name'


class StorageAdmin(SafeDeleteAdmin):
    list_display = ('product_name', 'category', 'gender', 'verify', 'type', 'permalink') + SafeDeleteAdmin.list_display
    list_filter = ('name', 'type', 'category') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def product_name(self, obj):
        return obj.name['persian']
    product_name.short_description = 'name'


class TourismAdmin(admin.ModelAdmin):
    list_display = ('date', 'price')
    # search_fields = ['name']
    list_per_page = 10
    ordering = ('-id',)


class MediaAdmin(admin.ModelAdmin):
    list_display = ('type', 'box', 'url')
    search_fields = ['name', 'box', 'type']
    list_per_page = 10
    ordering = ('-id',)
    # fields = ('name', 'type',)

    def url(self, obj):
        # move file

        return mark_safe(f'<a href="http://localhost{obj.file.url}">{obj.file.name}</a>')


admin.site.register(User, UserAdmin)
admin.site.register(Box, BoxAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Feature)
admin.site.register(Address)
admin.site.register(Media, MediaAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Storage)
admin.site.register(Basket)
admin.site.register(Comment)
admin.site.register(Factor)
admin.site.register(Menu, MenuAdmin)
admin.site.register(Tag)
admin.site.register(Rate)
admin.site.register(Slider, SliderAdmin)
admin.site.register(SpecialOffer, SpecialOfferAdmin)
admin.site.register(SpecialProduct, SpecialProductAdmin)
admin.site.register(WalletDetail)
admin.site.register(Blog)
admin.site.register(BlogPost)
admin.site.register(WishList)
admin.site.register(NotifyUser)
admin.site.register(Tourism, TourismAdmin)
admin.site.register(Ad)

admin.site.register(Permission)
admin.site.site_header = "Mehr Takhfif"
admin.site.site_title = "Mehr Takhfif"
