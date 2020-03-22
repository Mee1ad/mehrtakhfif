from django.core.mail import send_mail

from mtadmin.utils import *
from server.utils import get_access_token
import json
from mtadmin.serializer import *


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


# todo
class GenerateCode(AdminView):
    def post(self, request):
        data = json.loads(request.body)
        product = data.get('start_price')
        special_product = data.get('special_product')
        special_offer = data.get('special_offer')
        price = data.get['price']


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
        if table == 'media':
            media = Media.objects.order_by('type').distinct('type')
            return JsonResponse({'types': [{'id': item.type, 'name': item.get_type_display()} for item in media]})
        filters = get_table_filter(table)
        return JsonResponse({'data': filters})


class CheckLoginToken(AdminView):
    def post(self, request):
        data = json.loads(request.body)
        user = User.objects.get(pk=request.user.pk, admin_token=data['admin_token'])
        boxes = BoxSchema().dump(get_box_permission(user), many=True)
        return JsonResponse({'roll': get_roll(user), 'boxes': boxes})
