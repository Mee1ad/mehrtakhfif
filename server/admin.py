import pprint
from datetime import date

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.core.exceptions import FieldError
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from prettyjson import PrettyJSONWidget
from safedelete.admin import SafeDeleteAdmin
from django.utils.http import urlencode

from .models import *


class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return pprint.pformat(obj.get_decoded()).replace('\n', '<br>\n')

    _session_data.allow_tags = True
    list_display = ['session_key', '_session_data', 'expire_date']
    readonly_fields = ['_session_data']
    exclude = ['session_data']
    date_hierarchy = 'expire_date'
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget(attrs={'initial': 'parsed'})},
    }


UserAdmin.list_display += ('updated_at',)
UserAdmin.list_filter = ('groups', 'box_permission', 'is_staff')
UserAdmin.ordering = ('-id',)
UserAdmin.list_per_page = 10
UserAdmin.fieldsets[2][1]['fields'] = ('is_supplier',) + UserAdmin.fieldsets[2][1]['fields'] + ('box_permission',
                                                                                                'vip_types')
UserAdmin.filter_horizontal += ('box_permission',)


class Base(SafeDeleteAdmin):

    @staticmethod
    def link_name_fa(obj, table='language'):
        link = reverse(f"admin:server_{table}_change", args=[obj.name.id])
        return mark_safe(f'<a href="{link}">{escape(obj.name)}</a>')

    @staticmethod
    def name_fa(obj):
        return obj.name['fa']

    @staticmethod
    def get_user(obj):
        link = reverse(f"admin:server_user_change", args=[obj.user_id])
        return mark_safe(f'<a href="{link}">{escape(obj)}</a>')

    @staticmethod
    def get_product(obj):
        link = reverse(f"admin:server_product_change", args=[obj.product_id])
        return mark_safe(f'<a href="{link}">{escape(obj.product.name["fa"])}</a>')

    @staticmethod
    def get_post(obj):
        # link = reverse(f"admin:server_blog_post_change", args=[obj.blog_post_id])
        # return mark_safe(f'<a href="{link}">{escape(obj)}</a>')
        return None

    def lookup_allowed(self, key, value):
        # if key in ('related__pk', 'related__custom_field'):
        return True

        # return super(StorageAdmin, self).lookup_allowed(key, value)

    def view_students_link(self, obj):
        count = obj.person_set.count()
        url = (
                reverse("admin:core_person_changelist")
                + "?"
                + urlencode({"courses__id": f"{obj.id}"})
        )
        return mark_safe(f'<a href="{url}">{count} Students</a>')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ["created_by", "updated_by", "deleted_by", "suspended_by"]:
            kwargs["queryset"] = User.objects.filter(is_staff=True).order_by('id')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class BoxAdmin(SafeDeleteAdmin):
    list_display = ('name_fa', 'permalink', 'owner') + SafeDeleteAdmin.list_display
    # list_filter = ('name',) + SafeDeleteAdmin.list_filter
    search_fields = ['name']
    autocomplete_fields = ['owner']
    list_per_page = 10
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget(attrs={'initial': 'parsed'})}
    }

    # ordering = ('-created_at',)

    def name_fa(self, obj):
        return obj.name['fa']


class AdAdmin(admin.ModelAdmin):
    list_display = ('id', 'title_fa', 'url', 'storage', 'get_media', 'get_mobile_media')
    # list_filter = ('name',) + SafeDeleteAdmin.list_filter
    # search_fields = ['name']
    # autocomplete_fields = ['owner']
    list_per_page = 10

    # ordering = ('-created_at',)

    def title_fa(self, obj):
        return obj.title['fa']

    def get_media(self, obj):
        link = obj.media.image.url
        return mark_safe(f'<a href="{link}">{obj.media}</a>')

    def get_mobile_media(self, obj):
        try:
            link = obj.mobile_media.image.url
            return mark_safe(f'<a href="{link}">{obj.mobile_media}</a>')
        except AttributeError:
            return None

    get_media.short_description = 'media'
    get_mobile_media.short_description = 'mobile media'


class AddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'state', 'city', 'name', 'phone', 'address', 'user')
    list_filter = ('city', 'state') + SafeDeleteAdmin.list_filter
    search_fields = ['name', 'address', 'phone', 'user']
    autocomplete_fields = ['user']
    list_per_page = 10

    # ordering = ('-created_at',)

    def title_fa(self, obj):
        return obj.title['fa']

    def get_media(self, obj):
        link = obj.media.image.url
        return mark_safe(f'<a href="{link}">{obj.media}</a>')

    def get_mobile_media(self, obj):
        try:
            link = obj.mobile_media.image.url
            return mark_safe(f'<a href="{link}">{obj.mobile_media}</a>')
        except AttributeError:
            return None

    get_media.short_description = 'media'
    get_mobile_media.short_description = 'mobile media'


class CategoryAdmin(SafeDeleteAdmin):
    list_display = ('parent', 'box', 'name_fa', 'deleted_by') + SafeDeleteAdmin.list_display
    list_filter = ('name',) + SafeDeleteAdmin.list_filter
    list_display_links = ('box',)
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def name_fa(self, obj):
        return obj.name['fa']


class CharityAdmin(Base):
    list_display = ('name_fa', 'deposit_id') + SafeDeleteAdmin.list_display
    search_fields = ['name', 'deposit_id']
    list_per_page = 10
    ordering = ('-created_at',)


class DiscountCodeAdmin(Base):
    list_display = ('code', 'type', 'invoice_storage_id', 'basket_id') + SafeDeleteAdmin.list_display
    search_fields = ['code', 'invoice']
    list_filter = ('type',)
    list_per_page = 10
    ordering = ('-created_at',)


class FeatureAdmin(Base):
    list_display = ('name_fa', 'type', 'layout_type', 'values') + SafeDeleteAdmin.list_display
    list_filter = ('type', 'layout_type') + SafeDeleteAdmin.list_filter
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def values(self, obj):
        link = f'{HOST}/superuser/server/featurevalue/?feature_id={obj.id}'
        return mark_safe(f'<a href="{link}">Show</a>')


class FeatureValueAdmin(Base):
    list_display = ('id', 'feature', 'value_fa', 'priority') + SafeDeleteAdmin.list_display
    search_fields = ['feature', 'value_fa']
    list_per_page = 10
    ordering = ('-created_at',)

    def value_fa(self, obj):
        return obj.value['fa']


class FeatureGroupAdmin(Base):
    list_display = ('name_fa', 'box', 'get_features') + SafeDeleteAdmin.list_display
    list_filter = ('box',) + SafeDeleteAdmin.list_filter
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def get_features(self, obj):
        link = f'{HOST}/superuser/server/feature/?feature_id={obj.id}'
        return mark_safe(f'<a href="{link}">Show</a>')


class MenuAdmin(SafeDeleteAdmin):
    list_display = ('menu_name', 'media', 'url', 'type', 'parent', 'priority') + SafeDeleteAdmin.list_display
    list_filter = ('name', 'type', 'parent') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def menu_name(self, obj):
        return obj.name['fa']

    menu_name.short_description = 'name'


class CommentAdmin(SafeDeleteAdmin):
    list_display = ('get_user', 'get_product', 'get_post', 'approved') + SafeDeleteAdmin.list_display
    list_filter = ('user', 'product', 'blog_post', 'approved') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['user', 'product']
    list_per_page = 10
    ordering = ('-created_at',)

    def get_user(self, obj):
        return Base.get_user(obj)

    def get_product(self, obj):
        return Base.get_product(obj)

    def get_post(self, obj):
        return Base.get_post(obj)

    get_user.short_description = 'user'


class SliderAdmin(SafeDeleteAdmin):
    list_display = ('slider_title', 'type', 'url', 'product') + SafeDeleteAdmin.list_display
    list_filter = ('title', 'type') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['title']
    list_per_page = 10
    ordering = ('-created_at',)

    def slider_title(self, obj):
        return obj.title['fa']

    slider_title.short_description = 'name'

    def url(self, obj):
        return mark_safe(f'<a href="{HOST + obj.media.image.url}">{escape(obj.media.title["fa"])}</a>')

    url.short_description = 'url'


class SpecialOfferAdmin(SafeDeleteAdmin):
    list_display = ('menu_name', 'code', 'category', 'start_date', 'end_date') + SafeDeleteAdmin.list_display
    list_filter = ('name', 'code', 'box', 'product', 'category') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['name', 'code']
    list_per_page = 10
    ordering = ('-created_at',)

    def menu_name(self, obj):
        return obj.name['fa']

    menu_name.short_description = 'name'


class SpecialProductAdmin(SafeDeleteAdmin):
    list_display = ('url', 'storage', 'box') + SafeDeleteAdmin.list_display
    list_filter = ('name', 'storage', 'box') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)


class DecadeBornListFilter(admin.SimpleListFilter):
    title = _('by date')
    parameter_name = 'date'

    def lookups(self, request, model_admin):
        return (
            ('80s', _('in the eighties')),
            ('90s', _('in the nineties')),
        )

    def queryset(self, request, queryset):
        if self.value() == '80s':
            return queryset.filter(birthday__gte=date(1980, 1, 1),
                                   birthday__lte=date(1989, 12, 31))
        if self.value() == '90s':
            return queryset.filter(birthday__gte=date(1990, 1, 1),
                                   birthday__lte=date(1999, 12, 31))


class ProductAdmin(SafeDeleteAdmin):
    list_display = ('product_name', 'disable', 'type', 'permalink') + SafeDeleteAdmin.list_display
    # list_filter = ('type', 'DecadeBornListFilter') + SafeDeleteAdmin.list_filter
    list_display_links = ('product_name',)
    search_fields = ['product_name']
    list_per_page = 10
    ordering = ('-created_at',)

    def lookup_allowed(self, key, value):
        # if key in ('related__pk', 'related__custom_field'):
        return True

        # return super(StorageAdmin, self).lookup_allowed(key, value)

    def get_search_results(self, request, queryset, search_term):
        try:
            queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        except FieldError:
            queryset, use_distinct = Product.objects.annotate(q=KeyTextTransform('fa', 'name')).filter(
                q__contains=search_term), False
        return queryset, use_distinct

    def product_name(self, obj):
        return obj.name['fa']

    product_name.short_description = 'name'


class HouseAdmin(SafeDeleteAdmin):
    list_display = ('id', 'owner', 'state', 'city', 'price') + SafeDeleteAdmin.list_display
    # list_display_links = ('name',)
    search_fields = ['city']
    list_per_page = 10
    ordering = ('-created_at',)


class HouseOwnerAdmin(SafeDeleteAdmin):
    list_display = ('id', 'user', 'bank_name') + SafeDeleteAdmin.list_display
    list_filter = ('bank_name',) + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    list_per_page = 10
    ordering = ('-created_at',)


class HousePriceAdmin(SafeDeleteAdmin):
    list_display = ('id',) + SafeDeleteAdmin.list_display
    # list_display_links = ('name',)
    list_per_page = 10
    ordering = ('-created_at',)


class BookAdmin(SafeDeleteAdmin):
    list_display = ('id', 'start_date', 'end_date') + SafeDeleteAdmin.list_display
    # list_display_links = ('name',)
    list_per_page = 10
    ordering = ('-created_at',)


class ResidenceTypeAdmin(SafeDeleteAdmin):
    list_display = ('id', 'name') + SafeDeleteAdmin.list_display
    list_display_links = ('name',)
    list_per_page = 10
    ordering = ('-created_at',)


class StorageAdmin(Base):
    list_display = ('id', 'storage_name', 'sold_count', 'available_count_for_sale', 'max_count_for_sale',
                    'discount_price', 'disable', 'tax_type', 'get_supplier') + SafeDeleteAdmin.list_display
    list_filter = () + SafeDeleteAdmin.list_filter
    list_display_links = ('storage_name',)
    search_fields = ['storage_name']
    list_per_page = 10
    ordering = ('-created_at',)

    def get_search_results(self, request, queryset, search_term):
        try:
            queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        except FieldError:
            queryset, use_distinct = Storage.objects.annotate(q=KeyTextTransform('fa', 'title')).filter(
                q__contains=search_term), False
        return queryset, use_distinct

    def storage_name(self, obj):
        return obj.title['fa']

    def get_supplier(self, obj):
        try:
            link = reverse("admin:server_user_change", args=[obj.supplier.id])
            return mark_safe(f'<a href="{link}">{escape(obj.supplier)}</a>')
        except AttributeError:
            return None

    def lookup_allowed(self, key, value):
        # if key in ('related__pk', 'related__custom_field'):
        return True

        # return super(StorageAdmin, self).lookup_allowed(key, value)

    storage_name.short_description = 'title'
    get_supplier.short_description = 'supplier'


class InvoiceAdmin(SafeDeleteAdmin):
    list_display = ('id', 'amount', 'invoice_discount', 'status', 'get_storages', 'get_suppliers',
                    'get_invoice') + SafeDeleteAdmin.list_display
    list_filter = ('status', ) + SafeDeleteAdmin.list_filter
    # list_display_links = ('',)
    # search_fields = ['']
    list_per_page = 10
    ordering = ('-created_at',)

    def get_storages(self, obj):
        link = f'{HOST}/superuser/server/invoicestorage/?q={obj.id}'
        return mark_safe(f'<a href="{link}">Show</a>')

    def get_suppliers(self, obj):
        link = f'{HOST}/superuser/server/invoicesuppliers/?q={obj.id}'
        return mark_safe(f'<a href="{link}">Show</a>')

    def get_invoice(self, obj):
        link = f'{HOST}/invoice_detail/{obj.id}'
        return mark_safe(f'<a href="{link}">Show</a>')

    get_storages.short_description = 'storages'
    get_suppliers.short_description = 'suppliers'
    get_invoice.short_description = 'invoice'


class InvoiceStorageAdmin(admin.ModelAdmin):
    list_display = ('id', 'storage_name', 'discount_price', 'tax', 'charity', 'start_price', 'dev', 'admin', 'mt_profit',
                    'count', 'invoice_id')

    # list_filter = ['status', 'supplier']
    # # list_display_links = ('',)
    search_fields = ['invoice__id']

    # list_per_page = 10
    # ordering = ('-created_at',)

    def storage_name(self, obj):
        link = reverse("admin:server_storage_change", args=[obj.storage_id])
        return mark_safe(f'<a href="{link}">{escape(obj.storage.__str__())}</a>')

    storage_name.short_description = 'storage'


class InvoiceSupplierAdmin(admin.ModelAdmin):
    pass
    list_display = ('id', 'invoice', 'supplier', 'amount')

    # list_filter =
    list_display_links = ('id',)
    search_fields = ['invoice__id']

    # list_per_page = 10
    # ordering = ('-created_at',)


class MediaAdmin(admin.ModelAdmin):
    list_display = ('type', 'box', 'url')
    search_fields = ['name', 'box', 'type']
    list_per_page = 10
    ordering = ('-id',)

    # fields = ('name', 'type',)

    def url(self, obj):
        # move file

        return mark_safe(f'<a href="{HOST}{obj.image.url}">{obj.image.name}</a>')


class StateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    search_fields = ['name', ]
    list_per_page = 10
    ordering = ('-id',)


class CityAdmin(admin.ModelAdmin):
    list_display = ('get_state', 'name')
    search_fields = ['state', 'name']
    list_filter = ('state',)
    list_per_page = 10
    ordering = ('-id',)

    def get_state(self, obj):
        link = reverse("admin:server_state_change", args=[obj.state_id])
        return mark_safe(f'<a href="{link}">{escape(obj.state.__str__())}</a>')


class HolidayAdmin(SafeDeleteAdmin):
    list_display = ('occasion', 'day_off')
    list_filter = ('day_off',)
    search_fields = ['occasion', ]
    list_per_page = 10

    # ordering = ('-created_at',)

    def name_fa(self, obj):
        return obj.name['fa']


class VipTypeAdmin(SafeDeleteAdmin):
    list_display = ('name_fa', 'media')
    # list_filter = ('day_off',)
    search_fields = ['name', ]
    list_per_page = 10

    ordering = ('-created_at',)

    def name_fa(self, obj):
        return obj.name['fa']

    def url(self, obj):
        return mark_safe(f'<a href="{HOST}{obj.media.url}">{obj.media.name}</a>')


register_list = [(Session, SessionAdmin), (User, UserAdmin), (Box, BoxAdmin), (Category, CategoryAdmin),
                 (Feature, FeatureAdmin), (FeatureValue, FeatureValueAdmin), (Address,), (Media, MediaAdmin),
                 (Product, ProductAdmin), (House, HouseAdmin), (FeatureGroup, FeatureGroupAdmin),
                 (HousePrice, HousePriceAdmin), (ResidenceType, ResidenceTypeAdmin), (Booking, BookAdmin),
                 (Storage, StorageAdmin), (Basket,), (Comment, CommentAdmin), (Invoice, InvoiceAdmin),
                 (InvoiceStorage, InvoiceStorageAdmin), (InvoiceSuppliers, InvoiceSupplierAdmin), (Menu, MenuAdmin),
                 (Tag,), (TagGroup,), (Rate,), (Slider, SliderAdmin), (SpecialOffer, SpecialOfferAdmin),
                 (Holiday, HolidayAdmin), (Charity, CharityAdmin), (DiscountCode, DiscountCodeAdmin),
                 (SpecialProduct, SpecialProductAdmin), (Blog,), (BlogPost,), (WishList,), (NotifyUser,), (Ad, AdAdmin),
                 (State, StateAdmin), (City, CityAdmin), (Permission,), (VipType, VipTypeAdmin)]
for item in register_list:
    admin.site.register(*item)
admin.site.site_header = "Mehr Takhfif"
admin.site.site_title = "Mehr Takhfif"
