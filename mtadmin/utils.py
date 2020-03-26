from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from server.utils import get_pagination, get_token_from_cookie, set_token, check_access_token
from django.core.exceptions import ValidationError, FieldError, PermissionDenied
from django.contrib.admin.utils import NestedObjects
from server.models import *
from mtadmin.serializer import tables
from operator import attrgetter
import json
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views import View
import pysnooper

rolls = ['superuser', 'backup', 'admin', 'accountants']


class TableView(LoginRequiredMixin, PermissionRequiredMixin, View):
    pass


class AdminView(LoginRequiredMixin, View):
    pass


@pysnooper.snoop()
def serialized_objects(request, model, serializer, single_serializer=None, box_key='box_id', error_null_box=True):
    pk = request.GET.get('id', None)
    params = get_params(request, box_key)
    if pk:
        try:
            box_check = get_box_permission(request.user, box_key) if error_null_box else {}
            obj = model.objects.get(pk=pk, **params['filter'], **box_check)
            return {"data": single_serializer().dump(obj)}
        except model.DoesNotExist:
            raise PermissionDenied
    try:
        if error_null_box and not params['filter'].get(box_key):
            raise PermissionDenied
        query = model.objects.filter(**params['filter']).order_by(*params['order'])
        return get_pagination(query, request.step, request.page, serializer)
    except (FieldError, ValueError):
        raise FieldError


def get_params(request, box_key=None):
    remove_param = ['s', 'p', 'delay', 'error']
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
        if key == 'b':
            if int(value[0]) in request.user.box_permission.all().values_list('id', flat=True):
                filterby[f'{box_key}'] = value[0]
                continue
            raise PermissionDenied
        if key == 'o':
            orderby += value
            continue
        if len(value) == 1:
            filterby[key] = value[0]
            continue
        filterby[key.replace('[]', '__in')] = value
    return {'filter': filterby, 'order': orderby}


def get_data(request):
    # token = get_token_from_cookie(request)
    # assert check_access_token(token, request.user)
    data = json.loads(request.body)
    remove = ['created_at', 'created_by', 'updated_at', 'updated_by', 'deleted_by', 'income', 'profit',
              'rate', 'default_storage', 'sold_count', 'feature']
    [data.pop(k, None) for k in remove]
    boxes = request.user.box_permission.all()
    if data.get('box_id') not in boxes.values_list('id', flat=True):
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


def create_object(request, model, serializer, box_key='box'):
    if not request.user.has_perm(f'server.add_{model.__name__.lower()}'):
        raise PermissionDenied
    # data = get_data(request)
    data = json.loads(request)
    user = request.user
    boxes = user.box_permission.all()
    if box_key == 'product__box':
        if not Product.objects.filter(pk=data['product_id'], box__in=boxes).exists():
            raise PermissionDenied
    rm = ['tags', 'media', 'features']
    m2m = {}
    for item in rm:
        try:
            m2m[item] = data[item]
            data.pop(item)
        except KeyError:
            continue
    obj = model.objects.create(**data, created_by=user, updated_by=user)
    if model == Product:
        product = obj
        tags = Tag.objects.filter(pk__in=m2m['tags'])
        media = Media.objects.filter(pk__in=m2m['media'])
        product.tag.add(*tags)
        product.media.add(*media)
    if model == Category or model == Storage:
        item = obj
        features = Feature.objects.filter(pk__in=m2m['features'])
        item.feature_set.add(*features)
        if model == Storage:
            assign_default_value(obj.product_id)
    return serialized_objects(request, model, serializer)


def update_object(request, model, box_key='box'):
    if not request.user.has_perm(f'server.change_{model.__name__.lower()}'):
        raise PermissionDenied
    # data = get_data(request)
    data = json.loads(request.body)
    box_check = get_box_permission(request.user, box_key)
    items = model.objects.filter(pk=data['id'], **box_check)
    if model == Product:
        tags = Tag.objects.filter(pk__in=data['tags'])
        media = Media.objects.filter(pk__in=data['media'])
        product = items.first()
        product.tag.clear()
        product.tag.add(*tags)
        product.media.clear()
        product.media.add(*media)
        data.pop('tags')
        data.pop('media')
    if model == Category or model == Storage:
        item = items.first()
        features = Feature.objects.filter(pk__in=data['features'])
        data.pop('features')
        item.feature_set.clear()
        item.feature_set.add(*features)
        if model == Storage:
            assign_default_value(item.product_id)
    items.update(**data)


def delete_base(request, model):
    pk = int(request.GET.get('id', None))
    if request.token:
        if delete_object(request, model, pk):
            return JsonResponse({})
        return JsonResponse({}, status=400)
    return prepare_for_delete(model, pk, request.user)


def get_box_permission(user, box_key='box'):
    boxes_id = user.box_permission.all().values_list('id', flat=True)
    return {f'{box_key}__in': boxes_id}


def check_box_permission(user, box_id):
    try:
        box_id = int(box_id)
    except Exception:
        pass
    if box_id not in user.box_permission.all().values_list('id', flat=True):
        raise PermissionDenied


def check_user_permission(user, permission):
    if not user.has_perm(f'server.{permission}'):
        raise PermissionDenied


def prepare_for_delete(model, pk, user, box_key='box'):
    if not user.has_perm(f'server.delete_{model.__name__.lower()}'):
        raise PermissionDenied
    box_check = get_box_permission(user, box_key)
    item = model.objects.get(pk=pk, **box_check)
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
    obj = model.objects.filter(pk=pk)
    obj.update(deleted_by_id=user_id)
    obj.delete()


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
