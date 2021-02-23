from os import listdir
from time import sleep

from django.core.mail import send_mail
from django.http import HttpResponseBadRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, render
from django.utils.crypto import get_random_string
from django_telegram_login.authentication import verify_telegram_authentication
from django_telegram_login.errors import TelegramDataIsOutdatedError, NotTelegramDataError

from mehr_takhfif.settings import ARVAN_API_KEY, TELEGRAM_BOT_TOKEN
from mtadmin.serializer import *
from mtadmin.utils import *
from server.documents import *
from server.utils import *


class Token(AdminView):
    def get(self, request):
        res = JsonResponse({'token': get_access_token(request.user)})
        res = set_token(request.user, res)
        return res


class ReviewPrice(AdminView):
    def post(self, request):
        data = get_data(request, require_box=False)

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

        box = Box.objects.only('share', 'pk').get(pk=data['b'])
        data = translate_types(data, Storage)
        storage = {'count': 1, 'storage': '', 'tax_type': data['tax_type'], 'discount_price': data['discount_price'],
                   'start_price': data['start_price'], 'final_price': data['final_price']}
        storage = type('Storage', (), {**storage})()
        storage.product = type('Product', (), {})()
        storage.product.box = type('Box', (), {'share': box.share, 'pk': box.pk})()
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
        code_len = data.get('len', 5)
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
    def get(self, request, table):
        box_id = request.GET.get('b')
        user = request.user
        no_box = ['tag', 'invoice', 'invoice_storage', 'comment']
        check_user_permission(user, f'view_{table}')
        box = get_box_permission(request, 'box_id', box_id)
        # todo filter per month for invoice
        monthes = []
        if table in no_box:
            box = {}
        if table == 'storage':
            box = {'product__box_id': box_id}
            return JsonResponse({'disable': [{'id': 0, 'name': False}, {'id': 1, 'name': True}]})
        if table == 'media':
            types = Media.objects.order_by('type').distinct('type')
            return JsonResponse({'types': [{'id': item.type, 'name': item.get_type_display()} for item in types]})
        elif table == 'invoice':
            invoice_status = Invoice.objects.order_by('status').distinct('status')
            return JsonResponse(
                {'data': {'name': 'types',
                          'filters': [{'id': item.status, 'name': item.get_status_display()} for item in
                                      invoice_status]}})
        filters = get_table_filter(table, box)
        return JsonResponse({'data': filters})


class CheckLoginToken(AdminView):
    # def options(self, request, *args, **kwargs):
    #     return JsonResponse({"test": "ok"})

    def get(self, request):
        user = request.user
        permissions = user.box_permission.all().select_related('owner')
        boxes = BoxASchema(user=request.user, exclude=['media']).dump(permissions, many=True)
        roll = get_roll(user)
        user = UserASchema(exclude=['default_address']).dump(user)
        user['roll'] = roll
        res = {'user': user, 'boxes': boxes}
        return JsonResponse(res)


class PSearch(AdminView):
    def get(self, request):
        params = get_request_params(request)
        # switch = {'media': self.supplier, 'tag': self.tag,}
        rank = get_rank(params['q'], 'fa', 'title')
        medias = Media.objects.annotate(rank=rank).filter(rank__gt=0).order_by('-rank')[:5]
        medias = MediaASchema().dump(medias, many=True)
        return JsonResponse({"media": medias})


class Search(AdminView):

    def get(self, request):
        model = request.GET.get('type', None)
        switch = {'supplier': self.supplier, 'tag': self.tag, 'product': self.product, 'cat': self.category}
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

    def category(self, q, **kwargs):
        return self.multi_match(q, Category, CategoryASchema, CategoryDocument, 'categories')

    def product(self, q, **kwargs):
        box_id = kwargs.get('box_id')
        types = kwargs.get('types')
        products_id = []
        s = ProductDocument.search()
        # type_query = Q('bool', should=[Q("match", type=product_type) for product_type in types])
        # r = s.query('match', box_id=box_id).query(must=[Q('match', name_fa=q), Q('match', disable=False)])
        if box_id:
            only_fields = ['id', 'name', 'storages', 'thumbnail.id', 'thumbnail.title', 'thumbnail.image']
            box_info = {'box_id': box_id}
            s = s.query('match', **box_info).query('match', name_fa=q).query('match', disable=False)
            # r = s.query('match', box_id=box_id).query(type_query).query('match', name_fa=q)
            if s.count() == 0 and not q and box_info:
                s = s.query('match', **box_info).query('match', disable=False)
        else:
            s = s.query('match', name_fa=q).query('match', disable=False)
            only_fields = ['id', 'name', 'box', 'categories']
            # r = s.query('match', box_id=box_id).query('match_all')[:10]
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
    models = {'box': Box, 'product': Product}
    box_key = {'box': 'id', 'product': 'box_id'}

    def get(self, request, model):
        pk = request.GET.get('id')
        box_check = get_box_permission(request, self.box_key[model])
        model = self.models[model]
        box_settings = model.objects.filter(pk=pk, **box_check).values('settings').first()
        return JsonResponse({'data': box_settings})

    def patch(self, request, model):
        data = json.loads(request.body)
        box_check = get_box_permission(request, self.box_key[model])
        model = self.models[model]
        if model.objects.filter(pk=data['id'], **box_check).update(settings=data['settings']):
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
        data = get_data(request, require_box=False)
        data = to_obj(data)
        model = {'product_feature': ProductFeature, 'feature_value': FeatureValue,
                 'feature_group_feature': FeatureGroupFeature, 'category': Category}[data.model]
        ids = data.ids
        objects = model.objects.filter(pk__in=ids)
        for obj in objects:
            obj.priority = ids.index(obj.pk)
        model.objects.bulk_update(objects, ['priority'])
        return JsonResponse({**responses['priority']}, status=202)


class Test(View):
    def get(self, request):
        pk = request.GET.get('pk')
        product = Product.objects.filter(pk=pk).select_related('brand', 'house', 'box', 'thumbnail',
                                                               ). \
            prefetch_related().first()
        product = ProductESchema(only=['fg']).dump(product)
        return JsonResponse({**product})


class Test2(View):
    def get(self, request):
        pk = request.GET.get('pk')
        storage = Storage.objects.filter(pk=pk).first()
        storage = StorageESchema(only=['items']).dump(storage)
        return JsonResponse({**storage})
