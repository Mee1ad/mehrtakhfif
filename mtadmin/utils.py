from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from server.utils import get_pagination, get_token_from_cookie, set_token, check_access_token
from django.core.exceptions import ValidationError, FieldError, PermissionDenied, FieldDoesNotExist
from django.contrib.admin.utils import NestedObjects
from django.db.models import F
from server.models import *
from mtadmin.serializer import tables
from operator import attrgetter
import json
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views import View
import pysnooper
from server.utils import res_code

rolls = ['superuser', 'backup', 'admin', 'accountants']


class TableView(LoginRequiredMixin, PermissionRequiredMixin, View):
    pass


class AdminView(LoginRequiredMixin, View):
    pass


def serialized_objects(request, model, serializer=None, single_serializer=None, box_key='box_id', error_null_box=True,
                       params=None):
    pk = request.GET.get('id', None)
    box_check = get_box_permission(request.user, box_key) if error_null_box and box_key else {}
    if pk:
        try:
            obj = model.objects.get(pk=pk, **box_check)
            return {"data": single_serializer().dump(obj)}
        except model.DoesNotExist:
            raise PermissionDenied
    if not params:
        params = get_params(request, box_key)
    try:
        if error_null_box and not params['filter'].get(box_key):
            raise PermissionDenied
        query = model.objects.filter(**params['filter']).order_by(*params['order'])
        if params.get('aggregate', None):
            # todo tax
            pass
        return get_pagination(request, query, serializer, show_all=request.all)
    except (FieldError, ValueError):
        raise FieldError


def get_params(request, box_key=None, date_key='created_at'):
    remove_param = ['s', 'p', 'delay', 'error', 'all']
    filterby = {}
    orderby = []
    try:
        params = request.GET
        new_params = dict(params)
        [new_params.pop(key, None) for key in remove_param]
        keys = new_params.keys()
    except AttributeError:
        return {'filter': filterby, 'order': orderby}
    for key in keys:
        value = params.getlist(key)
        if key == 'sd':
            filterby[f'{date_key}__gte'] = value[0]
        if key == 'ed':
            filterby[f'{date_key}__lte'] = value[0]
        if key == 'b':
            if int(value[0]) in request.user.box_permission.all().values_list('id', flat=True):
                filterby[f'{box_key}'] = value[0]
                continue
            raise PermissionDenied
        if key == 'o':
            orderby += value
            continue
        if re.search('\[\]', key):
            filterby[key.replace('[]', '__in')] = value
            continue
        filterby[key] = value[0]

    return {'filter': filterby, 'order': orderby}


def get_data(request, require_box=True):
    # token = get_token_from_cookie(request)
    # assert check_access_token(token, request.user)
    data = json.loads(request.body)
    remove = ['created_at', 'created_by', 'updated_at', 'updated_by', 'deleted_by', 'income', 'profit',
              'rate', 'default_storage', 'sold_count', 'is_superuser', 'is_staff', 'deposit_id',
              'box_permission', 'wallet_credit', 'suspend_expire_date', 'activation_expire'] + ['feature', ]
    [data.pop(k, None) for k in remove]
    boxes = request.user.box_permission.all()
    if require_box and data.get('box_id') not in boxes.values_list('id', flat=True):
        raise PermissionDenied
    if request.method == "POST":
        data.pop('id', None)
    return data


def get_roll(user):
    try:
        if user.is_superuser:
            return 'superuser'
        return user.groups.first().name
    except AttributeError:
        raise PermissionDenied


def assign_default_value(product_id):
    storages = Storage.objects.filter(product_id=product_id)
    Product.objects.filter(pk=product_id).update(default_storage=min(storages, key=attrgetter('discount_price')))


def create_object(request, model, box_key='box', return_item=False, serializer=None, error_null_box=True, data=None):
    if not request.user.has_perm(f'server.add_{model.__name__.lower()}'):
        raise PermissionDenied
    data = data or get_data(request, require_box=error_null_box)
    user = request.user
    boxes = user.box_permission.all()
    if box_key == 'product__box':
        if not Product.objects.filter(pk=data['product_id'], box__in=boxes).exists():
            raise PermissionDenied
    rm = ['tags', 'media', 'features', 'categories', 'items']
    m2m = {}
    for item in rm:
        try:
            m2m[item] = data[item]
            data.pop(item)
        except KeyError:
            continue
    obj = model.objects.create(**data, created_by=user, updated_by=user)
    if model == Product:
        if not m2m['categories']:
            raise ValidationError('لطفا دسته بندی را انتخاب کنید')
        product = obj
        tags = Tag.objects.filter(pk__in=m2m['tags'])
        categories = Category.objects.filter(pk__in=m2m['categories'])
        p_medias = [ProductMedia(product=product, media_id=pk, priority=m2m['media'].index(pk)) for pk in m2m['media']]
        ProductMedia.objects.bulk_create(p_medias)
        product.tags.add(*tags)
        product.category.add(*categories)
        if not product.thumbnail_id or not product.media.all() or not product.category.all():
            product.disable = True
            product.save()
    # todo submit feature to invoice products
    # todo handle manytomany items <<items>>
    if model == Category:
        pass
    if model == Storage:
        if 'features' in m2m:
            feature_storages = [FeatureStorage(feature_id=item['feature_id'], storage_id=obj.pk,
                                               value=item['value']) for item in m2m['features']]
            FeatureStorage.objects.bulk_create(feature_storages)
        obj.priority = Product.objects.filter(pk=obj.product_id).count() - 1
        obj.save(validation=False)
        if obj.product.manage:
            obj.product.assign_default_value()

    if return_item:
        request.GET._mutable = True
        request.GET['id'] = obj.pk
        items = serialized_objects(request, model, single_serializer=serializer, box_key=box_key,
                                   error_null_box=error_null_box)
        return JsonResponse(items, status=201)
    return JsonResponse({'id': obj.pk}, status=201)


@pysnooper.snoop()
def update_object(request, model, box_key='box', return_item=False, serializer=None, data=None, require_box=True):
    if not request.user.has_perm(f'server.change_{model.__name__.lower()}'):
        raise PermissionDenied
    # data = get_data(request)
    data = data or json.loads(request.body)
    pk = data['id']
    box_check = get_box_permission(request.user, box_key) if require_box else {}
    items = model.objects.filter(pk=pk, **box_check)
    try:
        items.update(**data, validation=True)
    except FieldDoesNotExist:
        print(data)
        items.update(**data)
    if return_item:
        request.GET._mutable = True
        request.GET['id'] = items.first().pk
        items = serialized_objects(request, model, single_serializer=serializer, error_null_box=require_box)
        return JsonResponse({"data": items}, status=res_code['updated'])
    return JsonResponse({}, status=res_code['updated'])


# bug remove mt_profit from res

def delete_base(request, model, require_box=False):
    pk = int(request.GET.get('id', None))
    if request.token:
        if delete_object(request, model, pk):
            return JsonResponse({})
        return JsonResponse({}, status=400)
    return prepare_for_delete(model, pk, request.user, require_box=require_box)


def get_box_permission(user, box_key='box', box_id=None):
    boxes_id = user.box_permission.all().values_list('id', flat=True)
    if boxes_id:
        if box_id:
            if int(box_id) not in boxes_id:
                raise PermissionDenied
            return {f'{box_key}': box_id}
        return {f'{box_key}__in': boxes_id}
    raise PermissionDenied


def check_user_permission(user, permission):
    if not user.has_perm(f'server.{permission}'):
        raise PermissionDenied


def prepare_for_delete(model, pk, user, box_key='box', require_box=True):
    if not user.has_perm(f'server.delete_{model.__name__.lower()}'):
        raise PermissionDenied
    box_check = get_box_permission(user, box_key)
    try:
        item = model.objects.get(pk=pk, **box_check)
    except FieldError:
        item = model.objects.get(pk=pk)
    collector = NestedObjects(using='default')
    collector.collect([item])
    data = collector.nested()
    related_objects = []
    deleted_item = None
    for item in data:
        if type(item) == list:
            for nested_item in item:
                if type(nested_item) == list:
                    continue
                related_objects.append({'model': f'{nested_item.__class__.__name__}', 'id': nested_item.pk,
                                        'name': f'{nested_item}'})
        else:
            deleted_item = f'{item}'
    if len(related_objects) > 0:
        res = JsonResponse({'deleted_item': deleted_item, 'related_objects': related_objects})
    else:
        res = JsonResponse({'deleted_item': deleted_item})
        res = set_token(user, res)
    return res


def safe_delete(model, pk, user_id):
    model.objects.get(pk=pk).safe_delete(user_id)


def delete_object(request, model, pk):
    token = get_token_from_cookie(request)
    user = request.user
    if check_access_token(token, user, model, pk):
        safe_delete(Category, pk, user.id)
        return True
    return False


def get_model_filter(model, box):
    filter_list = model.objects.filter(**box).extra(select={'name': "name->>'fa'"}).values('id', 'name')
    return {'name': model.__name__.lower(), 'filters': list(filter_list)}


def get_table_filter(table, box):
    schema = tables.get(table, None)
    list_filter = schema.list_filter
    filters = [get_model_filter(model, box) for model in list_filter]
    return filters
