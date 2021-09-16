from os import listdir
from time import sleep

from django.core.mail import send_mail
from django.http import HttpResponseBadRequest, HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import render_to_response, render
from django_telegram_login.authentication import verify_telegram_authentication
from django_telegram_login.errors import TelegramDataIsOutdatedError, NotTelegramDataError
from elasticsearch_dsl import Search
from guardian.shortcuts import get_objects_for_user

from mehr_takhfif.settings import ARVAN_API_KEY, TELEGRAM_BOT_TOKEN
from mehr_takhfif.settings import ES_CLIENT
from mtadmin.serializer import *
from mtadmin.utils import *
from server.documents import *
from server.utils import *
from server.views.client.home import PromotedCategories
from server.views.client.product import ProductView as ClientProductView  # conflict with client product


class Cache(TableView):
    permission_required = 'is_superuser'

    def get(self, request):
        page = request.page
        step = request.step
        q = request.GET.get('q', '')
        data = cache.keys(f'*{q}*')[(page - 1) * step:(page - 1) * step + step]
        key = q.strip().replace('*', '')
        if len(key) < 3:
            delete_url = ''
            return JsonResponse({'data': data, 'delete': delete_url})
        caches = cache.keys(f'*{key}*')
        token = request.GET.get('token', None)
        if token:
            verified = check_access_token(token, request.user, data=caches)
            if verified:
                cache.delete_many(caches)
                return JsonResponse({'message': ' deleted successfully'})
            return HttpResponseNotFound()
        token = get_access_token(request.user, data=caches)
        delete_url = ""
        if caches:
            delete_url = HOST + f"/admin/cache?q={key}&token={token}"
        return JsonResponse({'data': data, 'delete': delete_url})


class Token(AdminView):
    def get(self, request):
        res = JsonResponse({'token': get_access_token(request.user)})
        res = set_token(request.user, res)
        return res


class ReviewPrice(AdminView):
    def post(self, request):
        data = get_data(request, require_category=False)

        # fp = data['final_price']
        # dp = data.get('discount_price', None)
        # vdp = data.get('vip_discount_price', None)
        # dper = data.get('discount_percent', None)
        # vdper = data.get('vip_discount_percent', None)
        #
        # if dp and vdp:
        #     dper = int(100 - dp / fp * 100)
        #     return JsonResponse({'discount_percent': dper})
        # elif dper and vdper:
        #     dp = int(fp - fp * dper / 100)

        category = Category.objects.only('settings', 'pk').get(pk=data['category_id'])
        data = translate_types(data, Storage)
        storage = {'count': 1, 'storage': '', 'tax_type': data['tax_type'], 'discount_price': data['discount_price'],
                   'start_price': data['start_price'], 'final_price': data['final_price']}
        storage = type('Storage', (), {**storage})()
        storage.product = type('Product', (), {})()
        storage.product.category = type('Category', (), {'share': category.settings['share'], 'pk': category.pk})()
        storage.storage = storage
        share = get_share(storage)
        profit = share['charity'] + share['dev'] + share['admin'] + share['mt_profit']
        if not request.user.is_superuser or get_group(request.user) in ['superuser', 'accountants']:
            remove_fields = ['dev', 'admin', 'charity', 'mt_profit']
            [share.pop(field, None) for field in remove_fields]
        try:
            dper = ceil(100 - data['discount_price'] / data['final_price'] * 100)
        except ZeroDivisionError:
            pass
            dper = 0
        share = {**share, 'discount_price': data['discount_price'], 'shipping_cost': data['shipping_cost'],
                 'profit': profit, 'discount_percent': dper}
        return JsonResponse({'data': share})


class GenerateCode(AdminView):
    def post(self, request):
        data = json.loads(request.body)
        storage_id = data['storage_id']
        count = data['count']
        code_len = len(data['count'])
        storage = Storage.objects.get(pk=storage_id)
        prefix = data.get('prefix', storage.title['fa'][:2])
        codes = [prefix + '-' + get_random_string(code_len, random_data) for c in range(count)]
        while len(set(codes)) < count:
            codes = list(set(codes))
            codes += [prefix + '-' + get_random_string(code_len, random_data) for c in range(count - len(set(codes)))]
        user = request.user
        items = [DiscountCode(code=code, storage=storage, created_by=user, updated_by=user) for code in codes]
        DiscountCode.objects.bulk_create(items)
        return JsonResponse({})


class MailView(AdminView):
    def post(self, request):
        send_mail(
            'Subject here',
            'Here is the message.',
            'from@example.com',
            ['to@example.com'],
            fail_silently=False,
        )


class TableFilter(AdminView):
    def __init__(self):
        super().__init__()
        self.category_id = None
        self.user = None

    def get(self, request, table):
        # todo filter per month for invoice
        self.category_id = request.GET.get('category_id', None)
        self.user = request.user
        check_user_permission(self.user, f'view_{table}')
        filters = {'feature': self.get_feature_filters, 'product': self.get_product_filters,
                   'invoice': self.get_invoice_filters}.get(table, self.get_default_filters)
        return JsonResponse({"data": filters()})

    def get_default_filters(self):
        return []

    def get_feature_filters(self):
        types = Feature.types
        types = map(lambda t: {"id": t[0], "name": t[1]}, types)
        types = list(types)
        return [{"name": "type", "filters": types}]

    def get_product_filters(self):
        categories = self.get_categories()
        brands = self.get_brands()
        return [{"name": "categories", "filters": categories}, {"name": "brand", "filters": brands}]

    def get_invoice_filters(self):
        statuses = Invoice.statuss
        statuses = map(lambda t: {"id": t[0], "name": t[1]}, statuses)
        statuses = list(statuses)
        return [{"name": "status", "filters": statuses}]

    def get_categories(self):
        category_id = self.category_id
        has_access(self.user, category_id)
        categories = Category.objects.filter(Q(parent_id=category_id) | Q(parent__parent_id=category_id)) \
            .values('id', 'name__fa')
        categories = map(lambda d: {"id": d['id'], "name": d["name__fa"]}, categories)
        return list(categories)

    def get_brands(self):
        s = Search(using=ES_CLIENT, index="product")
        query = {"query": {"term": {"category_id": self.category_id}}}
        brands = s.from_dict({"_source": "brand", "collapse": {"field": "brand.id"}, **query})
        brands = brands.execute()
        brands = [hit.brand.to_dict() for hit in brands if hit.brand]
        return brands


class CheckLoginToken(AdminView):
    # def options(self, request, *args, **kwargs):
    #     return JsonResponse({"test": "ok"})

    def get(self, request):
        user = request.user
        permissions = get_objects_for_user(user, 'server.manage_category').filter(parent=None)
        categories = CategoryASchema(user=request.user, exclude=['media']).dump(permissions, many=True)
        roll = get_roll(user)
        user = UserASchema(exclude=['default_address']).dump(user)
        user['roll'] = roll
        res = {'user': user, 'categories': categories}
        return JsonResponse(res)


class PSearch(AdminView):
    def get(self, request):
        params = get_request_params(request)
        # switch = {'media': self.supplier, 'tag': self.tag,}
        rank = get_rank(params['q'], 'fa', 'title')
        medias = Media.objects.annotate(rank=rank).filter(rank__gt=0).order_by('-rank')[:5]
        medias = MediaASchema().dump(medias, many=True)
        return JsonResponse({"media": medias})


class SearchView(AdminView):
    def get(self, request):
        model = request.GET.get('type', None)
        switch = {'supplier': self.supplier, 'tag': self.tag, 'product': self.product, 'cat': self.category,
                  'media': self.media}
        params = get_request_params(request)
        username = request.user.username
        return JsonResponse(switch[model](**params, username=username))

    def multi_match(self, q, model, serializer, document, output):
        ids = []
        s = document.search()
        r = s.query("multi_match", query=q, fields=['name_fa', 'name'])
        if r.count() == 0 and not q:
            r = s.query("match_all")[:10]
        [ids.append(item.id) for item in r]
        items = model.objects.in_bulk(ids)
        items = [items[x] for x in ids]
        return {output: serializer().dump(items, many=True)}

    def tag(self, q, **kwargs):
        return self.multi_match(q, Tag, TagASchema, TagDocument, 'tags')

    def media(self, q, **kwargs):
        return self.multi_match(q, Media, MediaASchema, MediaDocument, 'media')

    def category(self, q, **kwargs):
        return self.multi_match(q, Category, CategoryASchema, CategoryDocument, 'categories')

    def product(self, q, **kwargs):
        category_id = kwargs.get('category_id')
        types = kwargs.get('types')
        products_id = []
        s = ProductDocument.search()
        # type_query = Q('bool', should=[Q("match", type=product_type) for product_type in types])
        # r = s.query('match', category_id=category_id).query(must=[Q('match', name_fa=q), Q('match', disable=False)])
        if category_id:
            only_fields = ['id', 'name', 'storages', 'thumbnail.id', 'thumbnail.title', 'thumbnail.image']
            category_info = {'category_id': category_id}
            s = s.query('match', **category_info).query('match', name_fa=q).query('match', disable=False)
            # r = s.query('match', category_id=category_id).query(type_query).query('match', name_fa=q)
            if s.count() == 0 and not q and category_info:
                s = s.query('match', **category_info).query('match', disable=False)
        else:
            s = s.query('match', name_fa=q).query('match', disable=False)
            only_fields = ['id', 'name', 'category', 'categories']
            # r = s.query('match', category_id=category_id).query('match_all')[:10]
        [products_id.append(product.id) for product in s]
        products = Product.objects.select_related('thumbnail').prefetch_related('storages').in_bulk(products_id)
        products = [products[x] for x in products_id]

        return {'products': ProductESchema(
            only=only_fields,
            include_storage=True).dump(products, many=True)}

    def supplier(self, q, username, **kwargs):
        items = []
        s = SupplierDocument.search()
        r = s.query("multi_match", query=q or username,
                    fields=['first_name', 'last_name', 'username']).filter("term", is_supplier="true")[:5]
        # if r.count() == 0:
        #     r = s.query("match_all").filter("term", is_supplier="true")[:5]

        for hit in r:
            supplier = {'id': hit.id, 'first_name': hit.first_name, 'last_name': hit.last_name,
                        'username': hit.username}
            items.append(supplier)
        return {'suppliers': items}


class BoxSettings(AdminView):
    models = {'category': Category, 'product': Product}
    category_key = {'category': 'id', 'product': 'category_id'}

    def get(self, request, model):
        pk = request.GET.get('id')
        category_check = get_category_permission(request, self.category_key[model])
        model = self.models[model]
        category_settings = model.objects.filter(pk=pk, **category_check).values('settings').first()
        return JsonResponse({'data': category_settings})

    def patch(self, request, model):
        data = json.loads(request.body)
        category_check = get_category_permission(request, self.category_key[model])
        model = self.models[model]
        if model.objects.filter(pk=data['id'], **category_check).update(settings=data['settings']):
            return JsonResponse({})
        return HttpResponseBadRequest()


class Snapshot(AdminView):
    url = "https://napi.arvancloud.com/ecc/v1"
    region = "ir-thr-at1"
    headers = {'Authorization': ARVAN_API_KEY}

    def get(self, request):
        return JsonResponse({'data': self.get_snapshots()})

    def get_snapshots(self, name=None):
        images = requests.get(self.url + f'/regions/{self.region}/images?type=server', headers=self.headers).json()
        if name:
            return [image for image in images['data'] if name == image['abrak'].split('_', 1)[0]]
        return images['data']

    def post(self, request):
        res = {'failed': []}
        servers = requests.get(self.url + f'/regions/{self.region}/servers', headers=self.headers).json()
        for server in servers['data']:
            data = {'name': server['name']}
            new_snapshot = requests.post(self.url + f'/regions/{self.region}/servers/{server["id"]}/snapshot',
                                         headers=self.headers, data=data)
            if new_snapshot.status_code == 202:
                images = self.get_snapshots(server['name'])
                while images[0]['status'] != 'active':
                    sleep(5)
                    images = self.get_snapshots(server['name'])
                last_item = -1
                while len(images) > 2:
                    if requests.delete(self.url + f'/regions/{self.region}/images/{images[last_item]["id"]}',
                                       headers=self.headers).status_code == 200:
                        images = self.get_snapshots(server['name'])
                        continue
                    if last_item == -1:
                        last_item = -2
                        continue
                    res['failed'].append({'id': server['id'], 'name': server['name']})
                    break
        res['data'] = self.get_snapshots()
        return JsonResponse(res)


class Icon(AdminView):
    def get(self, request, key):
        with open("icons.json", "r") as read_file:
            icons = json.load(read_file)
        if key == 'all':
            return JsonResponse({'data': icons})
        icons = [icon for icon in icons if icon[key] is True]

        # self.create_json_from_directory()
        # icons = "ok"
        return JsonResponse({'data': icons})

    def create_json_from_directory(self):
        icons = listdir('media/icon/boom-gardi')
        icon_list = []
        for i in icons:
            icon_list.append({'name': i, 'feature': True})
        with open("icons.json", "w") as read_file:
            json.dump(icon_list, read_file)


class RecipientInfo(AdminView):
    def get(self, request):
        invoice_id = request.GET.get('i')
        size = request.GET.get('s', None)
        invoice = Invoice.objects.get(pk=invoice_id)
        if invoice.status in Invoice.success_status:
            if size == '6':
                return render_to_response('recipient_info A6.html', invoice.address)
            return render_to_response('recipient_info A5.html', invoice.address)
        return JsonResponse({})


class TelegramLogin(AdminView):
    def get(self, request):
        return render(request, 'tg_login.html')


class TelegramRegister(View):
    def get(self, request):
        try:
            params = verify_telegram_authentication(bot_token=TELEGRAM_BOT_TOKEN, request_data=request.GET).dict()
            User.objects.filter(pk=request.user.pk).update(tg_id=params['id'], tg_username=params.get('username'),
                                                           tg_first_name=params.get('first_name'),
                                                           avatar=params.get('photo_url'))
        except TelegramDataIsOutdatedError:
            return HttpResponse('Authentication was received more than a day ago.')

        except NotTelegramDataError:
            return HttpResponse('The data is not related to Telegram!')
        return HttpResponseRedirect('https://admin.mehrtakhfif.com')


class SetOrder(View):
    def put(self, request):
        # check_user_permission(request.user, 'change_feature')
        data = get_data(request, require_category=False)
        data = to_obj(data)
        model = {'product_feature': ProductFeature, 'feature_value': FeatureValue,
                 'feature_group_feature': FeatureGroupFeature, 'category': Category}[data.model]
        ids = data.ids
        objects = model.objects.filter(pk__in=ids)
        for obj in objects:
            obj.priority = ids.index(obj.pk)
        model.objects.bulk_update(objects, ['priority'])
        return JsonResponse({**responses['priority']}, status=202)


class ProductPreview(ClientProductView):
    pass


class PromoteCategory(AdminView, PromotedCategories):

    def put(self, request):
        data = json.loads(request.body)
        category_ids = data['category_ids']
        user = request.user
        if not user.is_superuser and not user.groups.filter(name="superuser").exists():
            raise PermissionDenied
        Category.objects.filter(promote=True).update(promote=False)
        Category.objects.filter(pk__in=category_ids).update(promote=True)
        return JsonResponse({**responses['202']}, status=202)


class Categories(View):
    def get(self, request):
        parent_id = request.GET.get('id', None)
        categories = get_categories({"parent_id": parent_id}, admin=True)
        return JsonResponse({'data': categories})
