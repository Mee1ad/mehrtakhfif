from django.http import JsonResponse
from server.utils import get_pagination, get_token_from_cookie, set_token, check_access_token
from server.error import AuthError
from django.core.exceptions import ValidationError, FieldError
from django.contrib.admin.utils import NestedObjects
from server.models import Storage, Product, Category, Tag, Media
from mtadmin.serializer import tables
from operator import attrgetter
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
import pysnooper

rolls = ['superuser', 'backup', 'admin', 'accountants']


class AdminView(LoginRequiredMixin, View):
    pass


def serialized_objects(request, model, serializer, single_serializer=None):
    pk = request.GET.get('id', None)
    params = get_params(request)
    if pk:
        obj = model.objects.get(pk=pk)
        return {"data": single_serializer().dump(obj)}
    try:
        query = model.objects.filter(**params['filter']).order_by(*params['order'])
        return get_pagination(query, request.step, request.page, serializer)
    except (FieldError, ValueError):
        query = model.objects.all()
        return get_pagination(query, request.step, request.page, serializer)


def get_params(request):
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
        if key == 'o':
            orderby += value
            continue
        if len(value) == 1:
            filterby[key] = value[0]
            continue
        filterby[key + '__in'] = value
    return {'filter': filterby, 'order': orderby}


def get_data(request):
    token = get_token_from_cookie(request)
    assert check_access_token(token, request.user)
    data = json.loads(request.body)
    remove = ['created_at', 'created_by', 'updated_at', 'updated_by', 'deleted_by', 'income', 'profit',
              'rate', 'default_storage', 'sold_count', 'feature']
    [data.pop(k, None) for k in remove]
    box_id = data.get('box_id', None)
    data['box_id'] = validate_box_id(request.user, box_id)
    if request.method == "POST":
        data.pop('id', None)
    return data


def get_roll(user):
    try:
        if user.is_superuser:
            return 'superuser'
        return user.groups.first().name
    except AttributeError:
        raise AuthError


def get_box_permission(user):
    return user.box_permission.all()


def validate_box_id(user, box_id=None):
    roll = get_roll(user)
    if roll == 'admin':
        return user.box.pk
    if roll in rolls:
        return box_id
    raise ValidationError


def assign_default_value(product_id):
    storages = Storage.objects.filter(product_id=product_id)
    Product.objects.filter(pk=product_id).update(default_storage=min(storages, key=attrgetter('discount_price')))


def create_object(request, model, serializer):
    data = get_data(request)
    user = request.user
    obj = model.objects.create(**data, created_by=user, updated_by=user)
    if model == Product:
        product = obj
        tags = Tag.objects.filter(pk__in=data['tags'])
        media = Media.objects.filter(pk__in=data['media'])
        product.tag.add(*tags)
        product.media.add(*media)
    if model == Storage:
        assign_default_value(obj.product_id)
    return serialized_objects(request, model, serializer)


def update_object(request, model):
    data = get_data(request)
    model.objects.filter(pk=data['id']).update(**data)


def delete_base(request, model):
    pk = int(request.GET.get('id', None))
    if request.token:
        if delete_object(request, model, pk):
            return JsonResponse({})
        return JsonResponse({}, status=400)
    return prepare_for_delete(model, pk, request.user)


def prepare_for_delete(model, pk, user):
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


def get_model_filter(model):
    filter_list = model.objects.extra(select={'name': "name->>'fa'"}).values('id', 'name')
    return {'name': model.__name__.lower(), 'filters': list(filter_list)}


def get_table_filter(table):
    schema = tables.get(table, None)
    list_filter = schema.list_filter
    filters = [get_model_filter(model) for model in list_filter]
    return filters
