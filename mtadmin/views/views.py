from django.core.mail import send_mail

from mtadmin.utils import *
from server.utils import get_access_token, random_data
import json
from mtadmin.serializer import *
from django.utils.crypto import get_random_string
import pysnooper
from server.utils import *
from django.contrib.auth import login


class Test(View):
    def get(self, request):
        @pysnooper.snoop()
        def get_child_count(category, sibling=0, childes=None):
            sibling_categories = Category.objects.filter(parent_id=category.pk)
            if not childes:
                childes = list(sibling_categories)
            childes += list(sibling_categories)
            sibling_count = sibling_categories.count()
            if sibling_count == 0:
                return sibling
            for sibl in sibling_categories:
                new_childes = get_child_count(sibl, childes=childes)
                if new_childes:
                    sibling_count += new_childes['child_count']
            childes = list(set(childes))
            return {'child_count': sibling_count, 'childes': CategoryASchema().dump(childes, many=True)}

        category = Category.objects.get(pk=1)
        a = get_child_count(category)
        return JsonResponse(a)

    def post(self, request):
        print(request.headers)
        print(request.headers['X-Csrf-Token'])
        return JsonResponse({"message": "wubalubadubdubbbbbbb"})


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
            dvper = int(100 - vdp / fp * 100)
            return JsonResponse({'discount_percent': dper, 'vip_discount_percent': dvper})
        elif dper and vdper:
            dp = int(fp - fp * dper / 100)
            vdp = int(fp - fp * vdper / 100)
            return JsonResponse({'discount_price': dp, 'vip_discount_price': vdp})
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
        check_box_permission(user, box_id)
        box = {'box_id': box_id}
        if table == 'storage':
            box = {'product__box_id': box_id}
        elif table in no_box:
            box = {}
        elif table == 'media':
            media = Media.objects.order_by('type').distinct('type')
            return JsonResponse({'types': [{'id': item.type, 'name': item.get_type_display()} for item in media]})
        filters = get_table_filter(table, box)
        return JsonResponse({'data': filters})


class CheckLoginToken(AdminView):
    def get(self, request):
        user = request.user
        permissions = user.box_permission.all()
        boxes = BoxASchema().dump(permissions, many=True)
        roll = get_roll(user)
        user = UserSchema().dump(user)
        user['roll'] = roll
        res = {'user': user, 'boxes': boxes}
        return JsonResponse(res)
