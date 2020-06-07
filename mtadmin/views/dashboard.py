from server.models import *
from mtadmin.views.tables import AdminView
from django.http import JsonResponse
from mtadmin.dashboard_serializer import *
from jdatetime import datetime as jdatetime
from datetime import datetime


class DateProductCount(AdminView):
    def get(self, request):
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')
        start_date = jdatetime.utcfromtimestamp(int(start_date))
        end_date = jdatetime.utcfromtimestamp(int(end_date))
        days = (end_date - start_date).days
        boxes = Box.objects.all()
        if days > 14:
            for day in days:
                boxes_list = []
                # gte = start_date +
                for box in boxes:
                    product_counts = Product.objects.filter(created_at__gte='', created_at__lte='')

        return JsonResponse({'boxes': 'ok'})


class ProductCount(AdminView):
    def get(self, request):
        boxes = Box.objects.all()
        return JsonResponse({'boxes': ProductCountSchema().dump(boxes, many=True)})
