from server.models import *
from mtadmin.views.tables import AdminView
from django.http import JsonResponse
from mtadmin.dashboard_serializer import *
from datetime import datetime, timedelta
from jdatetime import datetime as jdatetime, timedelta as jtimedelta


class DateProductCount(AdminView):
    def get(self, request):
        start_date = timezone.now() + timedelta(days=-14)
        boxes = Box.objects.all()
        boxes_list = []
        labels = [
            f'{(jdatetime.now() + jtimedelta(days=-14 + day)).month}-{(jdatetime.now() + jtimedelta(days=-13 + day)).day}'
            for day in range(14)]
        for box in boxes:
            cp = []
            up = []
            for day in range(14):
                gte = start_date + timedelta(days=day)
                lte = start_date + timedelta(days=day + 1)
                updated_products = Product.objects.filter(box=box, updated_at__gte=gte, updated_at__lte=lte).count()
                created_products = Product.objects.filter(box=box, created_at__gte=gte, created_at__lte=lte).count()

                cp.append(created_products)
                up.append(updated_products)
            boxes_list.append({'id': box.id, 'name': box.name, 'created_products': cp,
                               'updated_products': up, 'settings': box.settings})
        data = {'label': labels, 'boxes': boxes_list}

        return JsonResponse(data)


class ProductCount(AdminView):
    def get(self, request):
        boxes = Box.objects.all()
        return JsonResponse({'boxes': ProductCountSchema().dump(boxes, many=True)})


class SoldProductCount(AdminView):
    def get(self, request):
        box_id = request.GET.get('b')
        data = {}
        allowed_rolls = {'admin', 'support'}
        roll = request.user.groups.filter(name__in=allowed_rolls)
        if roll.exists() or request.user.is_superuser:
            products = InvoiceStorage.objects.filter(box_id=box_id, invoice__status=2)
            for status in deliver_status:
                data[status[1]] = products.filter(deliver_status=status[0]).count()
            return JsonResponse(data)
        return JsonResponse({})

