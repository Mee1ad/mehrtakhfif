import pprint
from datetime import date

from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.admin.exceptions import DisallowedModelAdminToField
from django.contrib.admin.options import (
    IS_POPUP_VAR, TO_FIELD_VAR, )
from django.contrib.admin.utils import (
    model_ngettext, )
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Permission
from django.core.exceptions import (
    PermissionDenied, )
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.template.response import SimpleTemplateResponse, TemplateResponse
from django.utils.html import escape
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from guardian.admin import GuardedModelAdmin
from prettyjson import PrettyJSONWidget
from safedelete.admin import SafeDeleteAdmin

from .models import *

# Changelist settings
ALL_VAR = 'all'
ORDER_VAR = 'o'
ORDER_TYPE_VAR = 'ot'
PAGE_VAR = 'p'
SEARCH_VAR = 'q'
ERROR_FLAG = 'e'

IGNORED_PARAMS = (
    ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR, TO_FIELD_VAR)


class NoCountPaginator(Paginator):
    @property
    def count(self):
        return 100  # Some arbitrarily large number,
        # so we can still get our page tab.


class MyChangeList(ChangeList):
    def __init__(self, request, model, list_display, list_display_links,
                 list_filter, date_hierarchy, search_fields, list_select_related,
                 list_per_page, list_max_show_all, list_editable, model_admin, sortable_by):
        self.model = model
        self.opts = model._meta
        self.lookup_opts = self.opts
        if re.search(r"/\w+/\w+/\w+/\d+", request.path):
            self.root_queryset = model_admin.model.objects.none()
        else:
            self.root_queryset = model_admin.get_queryset(request)
        self.list_display = list_display
        self.list_display_links = list_display_links
        self.list_filter = list_filter
        self.has_filters = None
        self.date_hierarchy = date_hierarchy
        self.search_fields = search_fields
        self.list_select_related = list_select_related
        self.list_per_page = list_per_page
        self.list_max_show_all = list_max_show_all
        self.model_admin = model_admin
        self.preserved_filters = model_admin.get_preserved_filters(request)
        self.sortable_by = sortable_by

        # Get search parameters from the query string.
        try:
            self.page_num = int(request.GET.get(PAGE_VAR, 0))
        except ValueError:
            self.page_num = 0
        self.show_all = ALL_VAR in request.GET
        self.is_popup = IS_POPUP_VAR in request.GET
        to_field = request.GET.get(TO_FIELD_VAR)
        if to_field and not model_admin.to_field_allowed(request, to_field):
            raise DisallowedModelAdminToField("The field %s cannot be referenced." % to_field)
        self.to_field = to_field
        self.params = dict(request.GET.items())
        if PAGE_VAR in self.params:
            del self.params[PAGE_VAR]
        if ERROR_FLAG in self.params:
            del self.params[ERROR_FLAG]

        if self.is_popup:
            self.list_editable = ()
        else:
            self.list_editable = list_editable
        self.query = request.GET.get(SEARCH_VAR, '')
        self.queryset = self.get_queryset(request)
        self.get_results(request)
        if self.is_popup:
            title = gettext('Select %s')
        elif self.model_admin.has_change_permission(request):
            title = gettext('Select %s to change')
        else:
            title = gettext('Select %s to view')
        self.title = title % self.opts.verbose_name
        self.pk_attname = self.lookup_opts.pk.attname


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


class UserAdmin(BaseUserAdmin):
    BaseUserAdmin.list_display = ('id', *BaseUserAdmin.list_display, 'updated_at',)
    list_filter = ('groups', 'is_staff')
    ordering = ('-id',)
    list_per_page = 10
    BaseUserAdmin.fieldsets[2][1]['fields'] = ('is_supplier',) + BaseUserAdmin.fieldsets[2][1]['fields'] + (
        'vip_types', 'category_permissions')

    # UserAdmin.filter_horizontal += ('box_permission',)


from django.core.exceptions import (
    FieldError, )
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.contrib.admin.options import csrf_protect_m, IncorrectLookupParameters


class Base(SafeDeleteAdmin):
    paginator = NoCountPaginator

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        """
        The 'change list' admin view for this model.
        """
        from django.contrib.admin.views.main import ERROR_FLAG
        opts = self.model._meta
        app_label = opts.app_label
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        try:
            cl = self.get_changelist_instance(request)
        except IncorrectLookupParameters:
            # Wacky lookup parameters were given, so redirect to the main
            # changelist page, without parameters, and pass an 'invalid=1'
            # parameter via the query string. If wacky parameters were given
            # and the 'invalid=1' parameter was already in the query string,
            # something is screwed up with the database, so display an error
            # page.
            if ERROR_FLAG in request.GET:
                return SimpleTemplateResponse('admin/invalid_setup.html', {
                    'title': _('Database error'),
                })
            return HttpResponseRedirect(request.path + '?' + ERROR_FLAG + '=1')

        # If the request was POSTed, this might be a bulk action or a bulk
        # edit. Try to look up an action or confirmation first, but if this
        # isn't an action the POST will fall through to the bulk edit check,
        # below.
        action_failed = False
        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)

        actions = self.get_actions(request)
        # Actions with no confirmation
        if (actions and request.method == 'POST' and
                'index' in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, queryset=cl.get_queryset(request))
                if response:
                    return response
                else:
                    action_failed = True
            else:
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                self.message_user(request, msg, messages.WARNING)
                action_failed = True

        # Actions with confirmation
        if (actions and request.method == 'POST' and
                helpers.ACTION_CHECKBOX_NAME in request.POST and
                'index' not in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, queryset=cl.get_queryset(request))
                if response:
                    return response
                else:
                    action_failed = True

        if action_failed:
            # Redirect back to the changelist page to avoid resubmitting the
            # form if the user refreshes the browser or uses the "No, take
            # me back" button on the action confirmation page.
            return HttpResponseRedirect(request.get_full_path())

        # If we're allowing changelist editing, we need to construct a formset
        # for the changelist given all the fields to be edited. Then we'll
        # use the formset to validate/process POSTed data.
        formset = cl.formset = None

        # Handle POSTed bulk-edit data.
        if request.method == 'POST' and cl.list_editable and '_save' in request.POST:
            if not self.has_change_permission(request):
                raise PermissionDenied
            FormSet = self.get_changelist_formset(request)
            modified_objects = self._get_list_editable_queryset(request, FormSet.get_default_prefix())
            formset = cl.formset = FormSet(request.POST, request.FILES, queryset=modified_objects)
            if formset.is_valid():
                changecount = 0
                for form in formset.forms:
                    if form.has_changed():
                        obj = self.save_form(request, form, change=True)
                        self.save_model(request, obj, form, change=True)
                        self.save_related(request, form, formsets=[], change=True)
                        change_msg = self.construct_change_message(request, form, None)
                        self.log_change(request, obj, change_msg)
                        changecount += 1

                if changecount:
                    msg = ngettext(
                        "%(count)s %(name)s was changed successfully.",
                        "%(count)s %(name)s were changed successfully.",
                        changecount
                    ) % {
                              'count': changecount,
                              'name': model_ngettext(opts, changecount),
                          }
                    self.message_user(request, msg, messages.SUCCESS)

                return HttpResponseRedirect(request.get_full_path())

        # Handle GET -- construct a formset for display.
        elif cl.list_editable and self.has_change_permission(request):
            FormSet = self.get_changelist_formset(request)
            formset = cl.formset = FormSet(queryset=cl.result_list)

        # Build the list of media to be used by the formset.
        if formset:
            media = self.media + formset.media
        else:
            media = self.media

        # Build the action form and populate it with available actions.
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields['action'].choices = self.get_action_choices(request)
            media += action_form.media
        else:
            action_form = None

        selection_note_all = ngettext(
            '%(total_count)s selected',
            'All %(total_count)s selected',
            # cl.result_count
            cl.result_count
        )

        context = {
            **self.admin_site.each_context(request),
            'module_name': str(opts.verbose_name_plural),
            'selection_note': _('0 of %(cnt)s selected') % {'cnt': len(cl.result_list)},
            'selection_note_all': selection_note_all % {'total_count': cl.result_count},
            'title': cl.title,
            'is_popup': cl.is_popup,
            'to_field': cl.to_field,
            'cl': cl,
            'media': media,
            'has_add_permission': self.has_add_permission(request),
            'opts': cl.opts,
            'action_form': action_form,
            'actions_on_top': self.actions_on_top,
            'actions_on_bottom': self.actions_on_bottom,
            'actions_selection_counter': self.actions_selection_counter,
            'preserved_filters': self.get_preserved_filters(request),
            **(extra_context or {}),
        }

        request.current_app = self.admin_site.name

        return TemplateResponse(request, self.change_list_template or [
            'admin/%s/%s/change_list.html' % (app_label, opts.model_name),
            'admin/%s/change_list.html' % app_label,
            'admin/change_list.html'
        ], context)

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
        if db_field.name in ["created_by", "updated_by", "deleted_by", "suspended_by", "owner"]:
            kwargs["queryset"] = User.objects.filter(is_staff=True).order_by('id')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget(attrs={'initial': 'parsed'})}
    }


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


class BasketAdmin(Base):
    list_display = ('id', 'get_user', 'count', 'sync') + SafeDeleteAdmin.list_display
    list_filter = ('sync',) + SafeDeleteAdmin.list_filter
    # list_display_links = ('product_name',)
    search_fields = ['user']
    list_per_page = 10
    ordering = ('-updated_at',)

    # get_user.short_description = 'user'


class BrandAdmin(Base):
    list_display = ('id', 'name_fa', 'permalink') + SafeDeleteAdmin.list_display
    list_per_page = 10
    search_fields = ['name']


class CategoryAdmin(Base, GuardedModelAdmin):
    list_display = ('id', 'parent_id', 'name_fa') + SafeDeleteAdmin.list_display
    list_filter = SafeDeleteAdmin.list_filter
    list_display_links = ('name_fa',)
    search_fields = ['name', 'id']
    list_per_page = 10
    # ordering = ('-created_at',)


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


class DateRangeAdmin(Base):
    list_display = ('title', 'start_date', 'end_date') + SafeDeleteAdmin.list_display
    search_fields = ['title']
    list_filter = ()
    list_per_page = 10
    ordering = ('-created_at',)


class FeatureAdmin(Base):
    list_display = ('id', 'name_fa', 'type', 'layout_type', 'values') + SafeDeleteAdmin.list_display
    list_filter = ('type', 'layout_type') + SafeDeleteAdmin.list_filter
    search_fields = ['name__fa']
    list_per_page = 10
    ordering = ('-created_at',)

    def values(self, obj):
        link = f'{HOST}/superuser/server/featurevalue/?feature_id={obj.id}'
        return mark_safe(f'<a href="{link}">Show</a>')


class FeatureValueAdmin(Base):
    list_display = ('id', 'feature', 'value_fa', 'priority') + SafeDeleteAdmin.list_display
    search_fields = ['value__fa']
    list_per_page = 10
    ordering = ('-created_at',)

    def value_fa(self, obj):
        return obj.value['fa']


class FeatureGroupAdmin(Base):
    list_display = ('name_fa', 'category', 'get_features') + SafeDeleteAdmin.list_display
    list_filter = ('category',) + SafeDeleteAdmin.list_filter
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def get_features(self, obj):
        link = f'{HOST}/superuser/server/feature/?feature_id={obj.id}'
        return mark_safe(f'<a href="{link}">Show</a>')


class MenuAdmin(Base):
    list_display = ('menu_name', 'media', 'url', 'type', 'parent', 'priority') + SafeDeleteAdmin.list_display
    list_filter = ('name', 'type', 'parent') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['name']
    list_per_page = 10
    ordering = ('-created_at',)

    def menu_name(self, obj):
        return obj.name['fa']

    menu_name.short_description = 'name'


class CommentAdmin(Base):
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


class SliderAdmin(Base):
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


class SpecialOfferAdmin(Base):
    list_display = ('menu_name', 'code', 'category', 'start_date', 'end_date') + SafeDeleteAdmin.list_display
    list_filter = ('name', 'code', 'category', 'product', 'category') + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    search_fields = ['name', 'code']
    list_per_page = 10
    ordering = ('-created_at',)

    def menu_name(self, obj):
        return obj.name['fa']

    menu_name.short_description = 'name'


class SpecialProductAdmin(Base):
    list_display = ('url', 'storage', 'category') + SafeDeleteAdmin.list_display
    list_filter = ('name', 'storage', 'category') + SafeDeleteAdmin.list_filter
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


class ProductAdmin(Base):
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
        return obj.name.get("fa", "")

    product_name.short_description = 'name'


class HouseAdmin(Base):
    list_display = ('id', 'owner', 'state', 'city', 'price') + SafeDeleteAdmin.list_display
    # list_display_links = ('name',)
    search_fields = ['city']
    list_per_page = 10
    ordering = ('-created_at',)


class HouseOwnerAdmin(Base):
    list_display = ('id', 'user', 'bank_name') + SafeDeleteAdmin.list_display
    list_filter = ('bank_name',) + SafeDeleteAdmin.list_filter
    # list_display_links = ('name',)
    list_per_page = 10
    ordering = ('-created_at',)


class HousePriceAdmin(Base):
    list_display = ('id',) + SafeDeleteAdmin.list_display
    # list_display_links = ('name',)
    list_per_page = 10
    ordering = ('-created_at',)


class BookAdmin(Base):
    list_display = ('id', 'start_date', 'end_date') + SafeDeleteAdmin.list_display
    # list_display_links = ('name',)
    list_per_page = 10
    ordering = ('-created_at',)


class ResidenceTypeAdmin(Base):
    list_display = ('id', 'name') + SafeDeleteAdmin.list_display
    list_display_links = ('name',)
    list_per_page = 10
    ordering = ('-created_at',)


class StorageAdmin(Base):
    list_display = ('id', 'storage_name', 'sold_count', 'available_count_for_sale', 'max_count_for_sale',
                    'discount_price', 'disable', 'tax_type', 'get_supplier',
                    'min_count_for_sale') + SafeDeleteAdmin.list_display
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


class InvoiceAdmin(Base):
    list_display = ('id', 'amount', 'invoice_discount', 'status', 'get_storages', 'get_suppliers',
                    'get_invoice') + SafeDeleteAdmin.list_display
    list_filter = ('status',) + SafeDeleteAdmin.list_filter
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


class PaymentHistoryAdmin(Base):
    list_display = ('id', 'get_invoice', 'reference_id', 'status', 'amount',
                    'description') + SafeDeleteAdmin.list_display
    list_filter = ('status',) + SafeDeleteAdmin.list_filter
    list_per_page = 10

    def get_invoice(self, obj):
        link = f'{HOST}/superuser/server/invoice/?id={obj.invoice_id}'
        return mark_safe(f'<a href="{link}">Show</a>')

    get_invoice.short_description = 'invoice'


class TagAdmin(Base):
    list_display = ('id', 'name_fa') + SafeDeleteAdmin.list_display
    list_per_page = 10
    search_fields = ['name']

    def get_queryset(self, request):
        import inspect
        print(inspect.stack()[1])

        try:
            queryset = self.model.all_objects.all()
        except:
            queryset = self.model._default_manager.all()

        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    def get_object(self, request, object_id, from_field=None):
        print(request.path)
        """
        Return an instance matching the field and value provided, the primary
        key is used if no field is provided. Return ``None`` if no match is
        found or the object_id fails validation.
        """
        queryset = self.get_queryset(request)
        print('1')
        model = queryset.model
        field = model._meta.pk if from_field is None else model._meta.get_field(from_field)
        try:
            object_id = field.to_python(object_id)
            return queryset.get(**{field.name: object_id})
        except (model.DoesNotExist, ValidationError, ValueError):
            return None

    def get_changelist_instance(self, request):
        """
        Return a `ChangeList` instance based on `request`. May raise
        `IncorrectLookupParameters`.
        """
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        # Add the action checkboxes if any actions are available.
        if self.get_actions(request):
            list_display = ['action_checkbox', *list_display]
        sortable_by = self.get_sortable_by(request)
        return MyChangeList(
            request,
            self.model,
            list_display,
            list_display_links,
            self.get_list_filter(request),
            self.date_hierarchy,
            self.get_search_fields(request),
            self.get_list_select_related(request),
            self.list_per_page,
            self.list_max_show_all,
            self.list_editable,
            self,
            sortable_by,
        )


class InvoiceStorageAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'storage_name', 'discount_price', 'tax', 'charity', 'start_price', 'dev', 'admin', 'mt_profit',
        'count', 'invoice_id')

    # list_filter = ['status', 'supplier']
    # # list_display_links = ('',)
    search_fields = ['invoice__id', 'storage__title__fa']

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
    list_display = ('type', 'category', 'url')
    search_fields = ['name', 'category', 'type']
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


class HolidayAdmin(Base):
    list_display = ('occasion', 'day_off')
    list_filter = ('day_off',)
    search_fields = ['occasion', ]
    list_per_page = 10

    # ordering = ('-created_at',)

    def name_fa(self, obj):
        return obj.name['fa']


class VipTypeAdmin(Base):
    list_display = ('name_fa', 'media')
    # list_filter = ('day_off',)
    search_fields = ['name', ]
    list_per_page = 10

    ordering = ('-created_at',)

    def name_fa(self, obj):
        return obj.name['fa']

    def url(self, obj):
        return mark_safe(f'<a href="{HOST}{obj.media.url}">{obj.media.name}</a>')


class SupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'deposit_id', 'first_name', 'last_name', 'shaba', 'is_verify', 'created_by')
    list_filter = ('is_verify',)
    search_fields = ['deposit_id', 'first_name', 'last_name', 'phone']
    list_per_page = 10
    ordering = ('-deposit_id',)
    fieldsets = (
        ('Payment info',
         {'fields': ('deposit_id', 'first_name', 'last_name', 'shaba', 'is_verify', 'created_by')}),)

    list_editable = ('deposit_id', 'is_verify')

    def get_paginator(self, request, queryset, per_page, orphans=0, allow_empty_first_page=True):
        queryset = queryset.filter(is_supplier=True)
        return self.paginator(queryset, per_page, orphans, allow_empty_first_page)


register_list = [(Session, SessionAdmin), (User, UserAdmin), (Category, CategoryAdmin),
                 (Feature, FeatureAdmin), (FeatureValue, FeatureValueAdmin), (Address,), (Media, MediaAdmin),
                 (Product, ProductAdmin), (House, HouseAdmin), (FeatureGroup, FeatureGroupAdmin),
                 (HousePrice, HousePriceAdmin), (ResidenceType, ResidenceTypeAdmin),
                 (Storage, StorageAdmin), (Basket, BasketAdmin), (Comment, CommentAdmin), (Invoice, InvoiceAdmin),
                 (InvoiceStorage, InvoiceStorageAdmin), (InvoiceSuppliers, InvoiceSupplierAdmin), (Menu, MenuAdmin),
                 (Tag, TagAdmin), (TagGroup,), (Rate,), (Slider, SliderAdmin), (SpecialOffer, SpecialOfferAdmin),
                 (Holiday, HolidayAdmin), (Charity, CharityAdmin), (DiscountCode, DiscountCodeAdmin),
                 (SpecialProduct, SpecialProductAdmin), (Blog,), (BlogPost,), (WishList,), (NotifyUser,), (Ad, AdAdmin),
                 (State, StateAdmin), (City, CityAdmin), (Permission,), (VipType, VipTypeAdmin),
                 (Supplier, SupplierAdmin), (PaymentHistory, PaymentHistoryAdmin), (DateRange, DateRangeAdmin)]
for item in register_list:
    admin.site.register(*item)
admin.site.site_header = "Mehr Takhfif"
admin.site.site_title = "Mehr Takhfif"

from jet.templatetags.jet_tags import assignment_tag


@assignment_tag(takes_context=True)
def jet_previous_object(context):
    # return jet_sibling_object(context, False)
    return "prev_obj"


@assignment_tag(takes_context=True)
def jet_next_object(context):
    # return jet_sibling_object(context, True)
    return "next_obj"
