from django.core.mail import send_mail
from os import listdir
from mtadmin.utils import *
from server.utils import get_access_token, random_data
import json
from mtadmin.serializer import *
from django.utils.crypto import get_random_string
import pysnooper
from server.utils import *
from django.contrib.auth import login
from server.documents import *
import requests
from mehr_takhfif.settings import ARVAN_API_KEY
from time import sleep
from os import listdir
from elasticsearch_dsl import Q


class Token(AdminView):
    def get(self, request):
        res = JsonResponse({'token': get_access_token(request.user)})
        res = set_token(request.user, res)
        return res


class CheckPrices(AdminView):
    def post(self, request):
        data = json.loads(request.body)
        fp = data['final_price']
        dp = data.get('discount_price', None)
        vdp = data.get('vip_discount_price', None)
        dper = data.get('discount_percent', None)
        vdper = data.get('vip_discount_percent', None)

        if dp and vdp:
            dper = int(100 - dp / fp * 100)
            return JsonResponse({'discount_percent': dper})
        elif dper and vdper:
            dp = int(fp - fp * dper / 100)
            return JsonResponse({'discount_price': dp})
        return JsonResponse({})


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
        box = get_box_permission(user, 'box_id', box_id)
        # todo filter per month for invoice
        monthes = []
        if table in no_box:
            box = {}
        if table == 'storage':
            box = {'product__box_id': box_id}
            return JsonResponse({'disable': [{'id': 0, 'name': False}, {'id': 1, 'name': True}]})
        if table == 'media':
            media_types = Media.objects.order_by('type').distinct('type')
            return JsonResponse({'types': [{'id': item.type, 'name': item.get_type_display()} for item in media_types]})
        elif table == 'invoice':
            invoice_status = Invoice.objects.order_by('status').distinct('status')
            return JsonResponse({'types': [{'id': item.status, 'name': item.get_status_display()} for item in invoice_status]})
        filters = get_table_filter(table, box)
        return JsonResponse({'data': filters})


class CheckLoginToken(AdminView):
    # def options(self, request, *args, **kwargs):
    #     return JsonResponse({"test": "ok"})

    def get(self, request):
        user = request.user
        permissions = user.box_permission.all()
        boxes = BoxASchema().dump(permissions, many=True)
        roll = get_roll(user)
        user = UserSchema().dump(user)
        user['roll'] = roll
        res = {'user': user, 'boxes': boxes}
        return JsonResponse(res)


class Search(AdminView):

    def get(self, request):
        params = dict(request.GET)
        model = request.GET.get('type', None)
        switch = {'supplier': self.supplier, 'tag': self.tag, 'product': self.product}
        return JsonResponse(switch[model](**params))

    def tag(self, q, **kwargs):
        tags_id = []
        s = TagDocument.search()
        r = s.query("multi_match", query=q[0], fields=['name_fa', 'name'])
        for hit in r:
            print(hit.name)
        if r.count() == 0 and not q[0]:
            r = s.query("match_all")[:10]
        [tags_id.append(tag.id) for tag in r]
        tags = Tag.objects.in_bulk(tags_id)
        tags = [tags[x] for x in tags_id]
        return {'tags': TagASchema().dump(tags, many=True)}
    @pysnooper.snoop()
    def product(self, q, box_id, **kwargs):
        product_types = kwargs.get('types[]', [])
        products_id = []
        s = ProductDocument.search()
        type_query = Q('bool', should=[Q("match", type=product_type) for product_type in product_types])
        r = s.query('match', box_id=box_id[0]).query(type_query).query('match', name_fa=q[0])
        if r.count() == 0 and not q[0]:
            r = s.query('match', box_id=box_id[0]).query(type_query).query('match_all')[:10]
        [products_id.append(product.id) for product in r]
        products = Product.objects.in_bulk(products_id)
        products = [products[x] for x in products_id]
        return {'products': ProductESchema().dump(products, many=True)}

    def supplier(self, q, **kwargs):
        items = []
        s = SupplierDocument.search()
        r = s.query("multi_match", query=q[0],
                    fields=['first_name', 'last_name', 'username']).filter("term", is_supplier="true")[:5]
        if r.count() == 0:
            r = s.query("match_all").filter("term", is_supplier="true")[:5]

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
        box_check = get_box_permission(request.user, self.box_key[model])
        model = self.models[model]
        box_settings = model.objects.filter(pk=pk, **box_check).values('settings').first()
        return JsonResponse({'data': box_settings})

    def patch(self, request, model):
        data = json.loads(request.body)
        box_check = get_box_permission(request.user, self.box_key[model])
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