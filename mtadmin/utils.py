import json

import xlsxwriter
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.core.exceptions import FieldError, PermissionDenied
from django.db.models.query import QuerySet
from django.http import JsonResponse
from django.views import View

from mtadmin.serializer import tables
from server.models import *
from server.utils import get_pagination, get_token_from_cookie, set_token, check_access_token, res_code

rolls = ['superuser', 'backup', 'admin', 'accountants']


def success_response(message):
    return {'message': message, 'variant': 'success'}


responses = {'201': success_response('با موفقیت ایجاد شد'), '202': success_response('با موفقیت به روز رسانی شد'),
             'priority': success_response('مرتب شد :)')}


class TableView(LoginRequiredMixin, PermissionRequiredMixin, View):
    pass


class AdminView(LoginRequiredMixin, View):
    pass


def serialized_objects(request, model, serializer=None, single_serializer=None, box_key='box_id', error_null_box=True,
                       params=None, required_fields=[]):
    pk = request.GET.get('id', None)
    box_check = get_box_permission(request, box_key) if error_null_box and box_key else {}
    if pk:
        sip = {}
        filter_fields = {'exclude': model.exclude_fields}
        try:
            if params:
                sip = params.get('sip', {})
                if params.get('filter', []).get('debug', None) is True:
                    params['filter'].pop('debug', None)
                    obj = model.objects.select_related(*model.select).prefetch_related(*model.prefetch). \
                        filter(pk=pk, **box_check).first()
                else:
                    obj = model.objects.select_related(*model.select).prefetch_related(*model.prefetch). \
                        filter(pk=pk, **box_check).first()
            else:
                obj = model.objects.select_related(*model.select).prefetch_related(*model.prefetch). \
                    filter(pk=pk, **box_check).first()
            if params['exclude_fields']:
                filter_fields = {'exclude': params['exclude_fields'] + model.exclude_fields}
            if params['only_fields']:
                filter_fields = {'only': params['only_fields']}
            data = single_serializer(user=request.user, **filter_fields, **sip).dump(obj)
            return {"data": data}
        except model.DoesNotExist:
            raise PermissionDenied
        except TypeError:
            return {"data": single_serializer(**filter_fields, **sip).dump(obj)}
    if not params:
        params = get_params(request, box_key)
    try:
        if error_null_box and not params['filter'].get(box_key) and not params['filter'].get(box_key[:-3]) and \
                not set(required_fields).issubset(params['filter']):
            try:
                if int(params['filter']['type']) not in model.no_box_type:
                    raise PermissionDenied
            except KeyError:
                raise PermissionDenied
        distinct_by = []
        if params['distinct']:
            distinct_by = [item.replace('-', '') for item in params['order'] if item.replace('-', '') not in model.m2m]
        # query = model.objects.filter(**params['filter']).order_by(*params['order'], '-id')
        query = model.objects.select_related(*model.table_select).prefetch_related(*model.table_prefetch) \
            .annotate(**model.table_annotate).filter(**params['filter']).exclude(**params['exclude']). \
            order_by(*params['order']).distinct(
            *distinct_by)
        # todo duplicate data when order by manytomany fields, need distinct
        # query = model.objects.filter(**params['filter']).order_by(*params['order'])
        if params.get('aggregate', None):
            # todo tax
            pass
        annotate_list = ['name__fa']  # http://localhost/admin/product?box_id=15&name__fa=نامیرا
        common_items = list(set(params['filter']).intersection(annotate_list))
        if common_items or params['annotate']:
            for item in common_items:
                params['filter'][item + '__contains'] = params['filter'][item]
                params['filter'].pop(item)
            common_items = [item.split('__') for item in common_items]
            annotate = {}
            for index, item in enumerate(common_items):
                annotate[item[0] + '__' + item[1]] = KeyTextTransform(item[1], item[0])
            try:
                query = model.objects.annotate(**annotate, **params['annotate'], **model.table_annotate).select_related(
                    *model.table_select).prefetch_related(*model.table_prefetch).filter(**params['filter']). \
                    exclude(**params['exclude']).distinct(*distinct_by).order_by(*params['order'])
                return get_pagination(request, query, serializer, show_all=request.all)
            except Exception:
                query = model.objects.annotate(**annotate, **params['annotate'], **model.table_annotate).select_related(
                    *model.table_select).prefetch_related(*model.table_prefetch).filter(**params['filter']). \
                    exclude(**params['exclude'])
                return {**get_pagination(request, query, serializer, show_all=request.all), 'ignore_order': True}
        # print(query.explain())
        return get_pagination(request, query, serializer, show_all=request.all)
    except (FieldError, ValueError):
        raise FieldError


# used in discount code
def translate_params(params, params_new_name, date_key='created_at'):
    params_new_name = {**params_new_name, 'sd': f'{date_key}__gte', 'ed': f'{date_key}__lte'}
    new_params = {}
    for k in params.keys():
        if params[k] in ['false', 'true']:
            params[k] = json.loads(params[k].lower())
        if k in ['ed', 'sd']:
            params[k] = datetime.datetime.utcfromtimestamp(int(params[k])).replace(tzinfo=pytz.utc)
        try:
            new_params[params_new_name[k]] = params[k]
        except KeyError:
            new_params[k] = params[k]
    return new_params


def get_params(request, box_key=None, date_key='created_at'):
    remove_param = ['s', 'p', 'delay', 'error', 'all']
    serializer_init_params = ['only_selectable']
    sip = {}
    filterby = {}
    excludeby = {}
    orderby = []
    annotate = {}
    distinct = False
    try:
        params = request.GET
        new_params = dict(params)
        only_fields = new_params.pop('only_fields[]', None)
        exclude_fields = new_params.pop('exclude_fields[]', None)
        [new_params.pop(key, None) for key in remove_param]
        keys = new_params.keys()
    except AttributeError:
        return {'filter': filterby, 'exclude': excludeby, 'order': orderby, 'annotate': annotate, 'distinct': False,
                'sip': sip}
    for key in keys:
        value = params.getlist(key)
        if key in serializer_init_params:
            sip['only_selectable'] = value[0]
        if key == 'sd':
            filterby[f'{date_key}__gte'] = value[0]
            continue
        if key == 'ed':
            filterby[f'{date_key}__lte'] = value[0]
            continue
        if key == 'b':
            # if int(value[0]) in request.user.box_permission.all().values_list('id', flat=True):
            # if User.objects.filter(pk=request.user.id, box_permission=int(value[0])).exists():
            if int(value[0]) in request.allowed_boxes_id:
                filterby[f'{box_key}'] = value[0]
                continue
            raise PermissionDenied
        if key == 'o':
            orderby = value
            continue
        if key == 'distinct':
            distinct = True
            continue
        if key == 'q':
            annotate['text'] = KeyTextTransform('fa', 'name')
            filterby['text__contains'] = value[0]
            orderby = ['text']
            continue
        if re.search('\[\]', key):
            filterby[key.replace('[]', '__in')] = value
            continue
        filterby[key] = value[0]
    return {'filter': filterby, 'exclude': excludeby, 'order': orderby, 'annotate': annotate, 'distinct': distinct,
            'exclude_fields': exclude_fields, 'only_fields': only_fields, 'sip': sip}


def get_data(request, require_box=True):
    data = json.loads(request.body)
    remove = ['created_at', 'created_by', 'updated_at', 'updated_by', 'deleted_by', 'income', 'profit',
              'rate', 'default_storage', 'sold_count', 'is_superuser', 'is_staff',
              'box_permission', 'wallet_credit', 'suspend_expire_date', 'activation_expire'] + ['feature', ]
    if data.get('permalink'):
        data['permalink'] = clean_permalink(data['permalink'])
    [data.pop(k, None) for k in remove]
    boxes = request.user.box_permission.all()
    # if require_box and data.get('box_id') not in boxes.values_list('id', flat=True):
    #     raise PermissionDenied
    if request.method == "POST":
        data.pop('id', None)
    return data


def get_message(key):
    res_pattern = {'updated': 'دسترسی شما محدود شده است لطفا بعدا تلاش کنید'}
    return {'message': res_pattern[key]}


def clean_permalink(permalink):
    permalink = permalink.strip()
    if permalink[-1] == '-':
        return permalink[:-1]
    return permalink


def get_roll(user):
    try:
        if user.is_superuser:
            return 'superuser'
        return user.groups.first().name
    except AttributeError:
        raise PermissionDenied


def get_m2m_fields(model, data):
    m2m = {}
    custom_m2m = {}
    remove_fields = {}
    ordered_m2m = {}
    for item in model.m2m:
        try:
            m2m[item] = data.pop(item)
        except KeyError:
            continue
    for item in model.custom_m2m:
        try:
            custom_m2m[item] = data.pop(item)
        except KeyError:
            continue
    for item in model.ordered_m2m:
        try:
            ordered_m2m[item] = data.pop(item)
        except KeyError:
            continue
    for item in model.remove_fields:
        try:
            remove_fields[item] = data.pop(item)
        except KeyError:
            continue
    return [data, m2m, custom_m2m, ordered_m2m, remove_fields]


def create_object(request, model, box_key='box', return_item=False, serializer=None, error_null_box=True, data=None,
                  return_obj=False, restrict_objects=(), restrict_m2m=(), used_product_feature_ids=()):
    if not request.user.has_perm(f'server.add_{model.__name__.lower()}'):
        raise PermissionDenied
    data = data or get_data(request, require_box=error_null_box)
    data = translate_types(data, model)
    user = request.user
    boxes = user.box_permission.all()
    if box_key == 'product__box':
        if not Product.objects.filter(pk=data['product_id'], box__in=boxes).exists():
            raise PermissionDenied
    data, m2m, custom_m2m, ordered_m2m, remove_fields = get_m2m_fields(model, data)
    # obj = model(**data, created_by=user, updated_by=user)
    data = {**data, 'created_by': user, 'updated_by': user}
    obj = serializer(user=user).load(data)
    save_data = {}
    if model == Storage:
        save_data = {'admin': True}
    obj.save(**remove_fields, **save_data)
    add_m2m(user, obj, m2m, custom_m2m, ordered_m2m, restrict_m2m, used_product_feature_ids)
    # for field in custom_m2m:
    #     add_custom_m2m(obj, field, custom_m2m[field], user, 'custom_m2m', restrict_m2m, used_product_feature_ids)
    # for field in ordered_m2m:
    #     add_custom_m2m(obj, field, ordered_m2m[field], user, 'ordered_m2m', restrict_m2m, used_product_feature_ids)
    if return_item:
        request.GET._mutable = True
        request.GET['id'] = obj.pk
        items = serialized_objects(request, model, single_serializer=serializer, box_key=box_key,
                                   error_null_box=error_null_box)
        return JsonResponse({**items, **responses['201']}, status=201)
    if return_obj:
        obj.refresh_from_db()
        return obj
    return JsonResponse({'id': obj.pk, **responses['201']}, status=201)


def get_m2m_field(obj, field, m2m, used_product_feature_ids=(), clear=True):
    many_to_many_model = getattr(obj, m2m)[field]
    if clear:
        try:
            getattr(obj, field).clear()
        except AttributeError:
            getattr(obj, field).all().delete()
    m2m_class = obj.__class__.__name__ + field[0].upper() + field[1:-1]
    if m2m_class == 'ProductFeature':
        ProductFeature.objects.filter(Q(product=obj), ~Q(id__in=used_product_feature_ids)).delete()
    return many_to_many_model


def m2m_footprint(many_to_many_model, user):
    user = {'created_by_id': user.pk, 'updated_by_id': user.pk}
    if many_to_many_model not in m2m_footprint_required:
        user = {}
    return user


def add_ordered_m2m(obj, field, item_list, user, m2m_type='ordered_m2m'):
    """
    :param obj: obj
    :param field: str
    :param item_list: list
    :param user: obj
    :param m2m_type: str
    :return: None
    """
    many_to_many_model = get_m2m_field(obj, field, m2m_type)
    user = m2m_footprint(many_to_many_model, user)
    extra_fields = {obj.__class__.__name__.lower(): obj}
    items = []
    for pk in item_list:
        related = {getattr(obj, field).model.__name__.lower() + '_id': pk}
        try:
            items.append(many_to_many_model(priority=item_list.index(pk), **extra_fields, **related))
        except TypeError:
            related = related[getattr(obj, field).model.__name__.lower() + '_id']
            items.append(many_to_many_model(priority=item_list.index(pk), **extra_fields, **related, **user))
    many_to_many_model.objects.bulk_create(items)


def add_custom_m2m(obj, field, item_list, user, m2m_type, restrict_m2m, used_product_feature_ids):
    priority = {}
    related = {}
    if field in restrict_m2m:
        # restrict_feature_ids = list(restrict_objects.values_list('id', flat=True))
        many_to_many_model = get_m2m_field(obj, field, m2m_type, clear=False,
                                           used_product_feature_ids=used_product_feature_ids)
        user = m2m_footprint(many_to_many_model, user)
        extra_fields = {obj.__class__.__name__.lower(): obj}
        items = []
        for item in item_list:
            if m2m_type == 'ordered_m2m':
                # related = {getattr(obj, field).model.__name__.lower() + '_id': item}
                priority = {"priority": item_list.index(item)}
            updated = many_to_many_model.objects.filter(feature_id=item['feature_id'],
                                                        feature_value_id=item['feature_value_id'],
                                                        product=obj) \
                .update(settings=item['settings'], updated_by_id=user['updated_by_id'], **priority)
            if updated:
                continue
            items.append(many_to_many_model(**item, **extra_fields, **user, **priority))
        many_to_many_model.objects.bulk_create(items)
    else:
        many_to_many_model = get_m2m_field(obj, field, m2m_type, clear=field not in obj.keep_m2m_data)
        user = m2m_footprint(many_to_many_model, user)
        extra_fields = {obj.__class__.__name__.lower(): obj}
        items = []
        for item in item_list:
            if m2m_type == 'ordered_m2m':
                last_priority = 0
                if many_to_many_model in append_on_priority:
                    last_priority = many_to_many_model.objects.filter(**extra_fields).count()
                # priority = {}
                # if 'priority' not in item:
                priority = {"priority": last_priority + item_list.index(item)}
            if type(item) != dict:  # because simple ordered m2m is int
                related = {getattr(obj, field).model.__name__.lower() + '_id': item}
                item = {}
            items.append(many_to_many_model(**item, **extra_fields, **user, **priority, **related))
        many_to_many_model.objects.bulk_create(items)


def add_m2m(user, obj, m2m, custom_m2m, ordered_m2m, restrict_m2m, used_product_feature_ids):
    if m2m:
        [getattr(obj, field).set(m2m[field]) for field in m2m]
    if custom_m2m:
        for field in custom_m2m:
            add_custom_m2m(obj, field, custom_m2m[field], user, 'custom_m2m', restrict_m2m,
                           used_product_feature_ids)
    if ordered_m2m:
        for field in ordered_m2m:
            add_custom_m2m(obj, field, ordered_m2m[field], user, 'ordered_m2m', restrict_m2m,
                           used_product_feature_ids)


def update_object(request, model, box_key='box', return_item=False, serializer=None, data=None, require_box=True,
                  extra_response={}, restrict_objects=(), restrict_m2m=(), used_product_feature_ids=(), notif=True):
    user = request.user
    if not user.has_perm(f'server.change_{model.__name__.lower()}'):
        raise PermissionDenied
    data = data or get_data(request, require_box=False)
    data = translate_types(data, model)
    try:
        data, m2m, custom_m2m, ordered_m2m, remove_fields = get_m2m_fields(model, data)
    except AttributeError:
        m2m, custom_m2m, ordered_m2m, remove_fields = None, None, None, None
    pk = data['id']
    box_check = get_box_permission(request, box_key) if require_box else {}
    footprint = {'updated_by': user, 'updated_at': timezone.now()}
    # items = model.objects.filter(pk=pk, **box_chqeck)
    item = model.objects.get(pk=pk, **box_check)
    data = serializer(user=user, return_dict=True).load(data)
    try:
        # items.update(**data, remove_fields=remove_fields, **footprint)
        item.__dict__.update(**data, remove_fields=remove_fields, **footprint)
    except FieldDoesNotExist:
        try:
            # items.update(**data, **footprint)
            item.__dict__.update(**data, **footprint)
        except FieldDoesNotExist:
            # items.update(**data)
            item.__dict__.update(**data)
    # item = items.first()
    add_m2m(user, item, m2m, custom_m2m, ordered_m2m, restrict_m2m, used_product_feature_ids)
    try:
        if item.disable is False:
            item.full_clean()
            item.validation()
    except AttributeError:
        pass
    item.save()
    message = {}
    if notif:
        message = responses['202']
    if return_item:
        request.GET._mutable = True
        request.GET['id'] = item.pk
        items = serialized_objects(request, model, single_serializer=serializer, error_null_box=require_box)
        return JsonResponse({"data": items, **extra_response, **message}, status=res_code['updated'])
    return JsonResponse({**extra_response, **message}, status=res_code['updated'])


def delete_base(request, model, require_box=False):
    pk = int(request.GET.get('id', None))
    if request.token:
        if delete_object(request, model, pk):
            return JsonResponse({})
        return JsonResponse({}, status=400)
    return prepare_for_delete(model, pk, request.user, require_box=require_box)


def get_box_permission(request, box_key='box', box_id=None):
    allowed_boxes_id = request.allowed_boxes_id
    if allowed_boxes_id:
        if box_id:
            if int(box_id) not in allowed_boxes_id:
                raise PermissionDenied
            return {f'{box_key}': box_id}
        return {f'{box_key}__in': allowed_boxes_id}
    raise PermissionDenied


def check_user_permission(user, permission):
    if not user.has_perm(f'server.{permission}'):
        raise PermissionDenied


def prepare_for_delete(model, pk, user, box_key='box', require_box=True):
    if not user.has_perm(f'server.delete_{model.__name__.lower()}'):
        raise PermissionDenied
    box_check = get_box_permission(request, box_key)
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
    name = model.__name__.lower()
    try:
        name = {'category': 'categories', 'featuregroup': 'groups'}[name]
    except KeyError:
        name = name
    return {'name': name, 'filters': list(filter_list)}


def get_table_filter(table, box):
    schema = tables.get(table, None)
    try:
        list_filter = schema.list_filter
        filters = [get_model_filter(model, box) for model in list_filter]
        return filters
    except AttributeError:
        return {}


def get_group(user):
    return getattr(User.objects.get(pk=user.pk).groups.first(), 'name', None)


def get_obj_type(obj=None, type_id=None, class_name=None):
    class_name = class_name or obj.__class__
    types = class_name.types
    type_id = type_id or obj.type
    return next((value[1] for index, value in enumerate(types) if value[0] == type_id), '')


def generate_post_discount_code(username):
    from mtadmin.views.tables import random_data
    from django.utils.crypto import get_random_string
    code = get_random_string(10, random_data)
    user = User.objects.get(username=username)
    DiscountCode.objects.create(code=code, type=3, created_by=user, updated_by=user)


def distinct_list_of_dict(l, k):  # list, key
    distinct_list = []
    for item in l:
        if next((v for i, v in enumerate(distinct_list) if getattr(v, k) == getattr(item, k)), None) is None:
            distinct_list.append(item)
    return distinct_list

