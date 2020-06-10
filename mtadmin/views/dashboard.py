from server.models import *
from mtadmin.views.tables import AdminView
from django.http import JsonResponse
from mtadmin.dashboard_serializer import *
from datetime import datetime, timedelta
from jdatetime import datetime as jdatetime, timedelta as jtimedelta
from server.models import *


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
            boxes_list.append({'id': box.id, 'name': box.name['fa'], 'created_products': cp,
                               'updated_products': up, 'setting': box.settings})
        data = {'label': labels, 'boxes': boxes_list}

        return JsonResponse(data)


class ProductCount(AdminView):
    @pysnooper.snoop()
    def get(self, request):
        products = Product.objects.all()
        for product in products:
            data = product.properties
            if data:
                res = {"data": {
                    "ar": {
                        "items": []
                    },
                    "en": {
                        "items": []
                    },
                    "fa": {
                        "items": []
                    }
                }}

                property = {
                    "id": 1,
                    "type": {
                        "key": "attributes",
                        "label": "ویژگی ها"
                    },
                    "items": []
                }
                usage_condition = {
                    "id": 2,
                    "type": {
                        "key": "term_of_use",
                        "label": "شرایط استفاده"
                    },
                    "items": []
                }

                if 'fa' in data:
                    if 'property' in data["fa"]:
                        for item in data["fa"]["property"]:
                            property["items"].append({
                                "id": item["id"],
                                "icon": item["icon"],
                                "text": item["text"],
                                "priority": item["priority"]
                            })
                        res["data"]["fa"]["items"].append(property)
                if 'fa' in data:
                    if 'usage_condition' in data['fa']:
                        if data["fa"]["usage_condition"]:
                            for item in data["fa"]["usage_condition"]:
                                usage_condition["items"].append({
                                    "id": item["id"],
                                    "icon": item["icon"],
                                    "text": item["text"],
                                    "priority": item["priority"]
                                })
                            res["data"]["fa"]["items"].append(usage_condition)

                product.properties = res
                product.save()
        print('tammam')
        return JsonResponse({'message': 'taamaam'})
        # boxes = Box.objects.all()
        # return JsonResponse({'boxes': ProductCountSchema().dump(boxes, many=True)})
