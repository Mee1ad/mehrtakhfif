from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re


def validate_vip_price(value):
    keys = {'weight': 'وزن', 'height': 'ارتفاع', 'width': 'عرض', 'length': 'طول'}
    for key in keys:
        if key not in value:
            raise ValidationError(_(f'لطفا {key} محصول را وارد نمایید'))


def validate_product_type(value):
    pass


def validate_permalink(value):
    pattern = '^[A-Za-z0-9\u0591-\u07FF\uFB1D-\uFDFD\uFE70-\uFEFC][A-Za-z0-9-\u0591-\u07FF\uFB1D-\uFDFD\uFE70-\uFEFC]*$'
    if value and not re.match(pattern, value):
        raise ValidationError(_("پیوند یکتا نامعتبر است"))


def product_validation(self, **kwargs):
    product = self.first()
    kwargs = self.activation_validation(product, kwargs)
    if kwargs.get('disable') is False:
        pass
    if product.disable is False and (kwargs.get('thumbnail', '') is None or kwargs.get('media') is []
                                     or kwargs.get('tag') is [] or kwargs.get('category') is []):
        raise ValidationError(_('محصول فعال است. برای اعمال تغییرات ابتدا محصول را غیرفعال نمایید'))

    if kwargs.get('storages_id', None):
        [Storage.objects.filter(pk=pk).update(priority=kwargs['storages_id'].index(pk), is_manage=True)
         for pk in kwargs.get('storages_id', [])]
        kwargs.pop('storages_id')
        return kwargs

    default_storage_id = kwargs.get('default_storage_id')
    pk = kwargs.get('id')
    if default_storage_id:
        new_default_storage = Storage.objects.filter(pk=default_storage_id)
        Storage.objects.filter(product_id=pk, priority__lt=new_default_storage.first().priority) \
            .order_by('priority').update(priority=F('priority') + 1)
        new_default_storage.update(priority=0)
    if kwargs.get('tags', None) is not None and kwargs.get('categories') is not None \
            and kwargs.get('media') is not None:
        tags = Tag.objects.filter(pk__in=kwargs.get('tags', []))
        if not tags:
            raise ValidationError(_('لطفا حداقل 3 تگ را انتخاب کنید'))
        categories = Category.objects.filter(pk__in=kwargs.get('categories', []))
        if not categories:
            raise ValidationError(_('لطفا دسته بندی را انتخاب کنید'))
        product.tags.clear()
        product.tags.add(*tags)
        product.categories.clear()
        product.categories.add(*categories)
        product.media.clear()
        p_medias = [ProductMedia(product=product, media_id=pk, priority=kwargs['media'].index(pk)) for pk in
                    kwargs.get('media', [])]
        ProductMedia.objects.bulk_create(p_medias)
    if kwargs.get('manage', None):
        item = self.first()
        item.assign_default_value()
    return kwargs


def validate_meli_code(value):
    print('this is validations')
    return value + '555'
