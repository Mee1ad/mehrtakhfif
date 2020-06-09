from server.models import *
from mtadmin.views.tables import AdminView
from django.http import JsonResponse
from mtadmin.dashboard_serializer import *
from datetime import datetime, timedelta
from jdatetime import datetime as jdatetime


class DateProductCount(AdminView):
    def get(self, request):
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')
        start_date = datetime.fromtimestamp(int(start_date)).replace(tzinfo=pytz.utc)
        end_date = datetime.fromtimestamp(int(end_date)).replace(tzinfo=pytz.utc)
        days = (end_date - start_date).days
        boxes = Box.objects.all()
        data = []
        for day in range(days):
            boxes_list = []
            gte = start_date + timedelta(days=day)
            lte = start_date + timedelta(days=day + 1)
            label = f'{jdatetime.fromgregorian(datetime=gte).month}-{jdatetime.fromgregorian(datetime=gte).day}'
            for box in boxes:
                product_count = Product.objects.filter(box=box, created_at__gte=gte, created_at__lte=lte).count()
                active_product_count = Product.objects.filter(box=box, created_at__gte=gte, created_at__lte=lte,
                                                              disable=False).count()
                boxes_list.append({'name': box.name['fa'], 'product_count': product_count,
                                   'active_product_count': active_product_count, 'setting': box.settings})
            data.append({'label': label, 'boxes': boxes_list})

        return JsonResponse({'data': data})


class ProductCount(AdminView):
    def get(self, request):
        boxes = Box.objects.all()
        return JsonResponse({'boxes': ProductCountSchema().dump(boxes, many=True)})
