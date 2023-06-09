from datetime import timedelta

from django.db.models import Sum
from django.http import JsonResponse
from jdatetime import datetime as jdatetime, timedelta as jtimedelta

from mtadmin.dashboard_serializer import *
from mtadmin.views.tables import AdminView
from server.models import *


class DateProductCount(AdminView):
    def get(self, request):
        start_date = timezone.now() + timedelta(days=-14)
        categories = Category.objects.filter(parent=None)
        categories_list = []
        labels = [
            f'{(jdatetime.now() + jtimedelta(days=-14 + day)).month}-{(jdatetime.now() + jtimedelta(days=-13 + day)).day}'
            for day in range(14)]
        for category in categories:
            cp = []
            up = []
            for day in range(14):
                gte = start_date + timedelta(days=day)
                lte = start_date + timedelta(days=day + 1)
                updated_products = Product.objects.filter(category=category, updated_at__gte=gte,
                                                          updated_at__lte=lte).count()
                created_products = Product.objects.filter(category=category, created_at__gte=gte,
                                                          created_at__lte=lte).count()

                cp.append(created_products)
                up.append(updated_products)
            categories_list.append({'id': category.id, 'name': category.name, 'created_products': cp,
                                    'updated_products': up, 'settings': category.settings})
        data = {'label': labels, 'categories': categories_list}

        return JsonResponse(data)


class ProductCount(AdminView):
    def get(self, request):
        categories = Category.objects.filter(parent=None)
        return JsonResponse({'categories': ProductCountSchema().dump(categories, many=True)})


class SoldProductCount(AdminView):
    def get(self, request):
        category_id = request.GET.get('category_id')
        data = {}
        allowed_rolls = {'admin', 'support'}
        roll = request.user.groups.filter(name__in=allowed_rolls)
        if roll.exists() or request.user.is_superuser:
            products = InvoiceStorage.objects.filter(category_id=category_id, invoice__status=2)
            for status in deliver_status:
                data[status[1]] = products.filter(deliver_status=status[0]).count()
            return JsonResponse(data)
        return JsonResponse({})


class ProfitSummary(AdminView):
    permission_required = 'server.view_invoice'

    def get(self, request):
        start = request.GET.get('start')
        start = timezone.datetime.fromtimestamp(int(start)).replace(tzinfo=pytz.utc)
        end = request.GET.get('end')
        end = timezone.datetime.fromtimestamp(int(end)).replace(tzinfo=pytz.utc)
        categories = Category.objects.filter(parent=None)
        categories_list = []
        for category in categories:
            profit = InvoiceStorage.objects.filter(storage__product__category=category, invoice__payed_at__range=[start, end],
                                                   invoice__status__in=Invoice.success_status) \
                .aggregate(sold_count=Sum('count'), charity=Sum('charity'), dev=Sum('dev'), admin=Sum('admin'),
                           total_payment=Sum('discount_price'), start_prices=Sum('start_price'),
                           mt_profit=Sum('mt_profit'), post_price=Sum('invoice__post_invoice__amount'), tax=Sum('tax'))

            data = {'id': category.id, 'name': category.name, 'mt_profit': profit['mt_profit'] or 0, 'settings': category.settings,
                    'charity': profit['charity'] or 0, 'sold_count': profit['sold_count'] or 0,
                    'total_payment': profit['total_payment'] or 0, 'start_price': profit['start_prices'] or 0,
                    'post_price': profit['post_price'] or 0, 'dev': profit['dev'] or 0, 'admin': profit['admin'] or 0,
                    'tax': profit['tax'] or 0}
            categories_list.append(data)
        total = {'charity': 0, 'total_payment': 0, 'mt_profit': 0, 'start_price': 0, 'post_price': 0, 'dev': 0,
                 'admin': 0, 'tax': 0}
        for b in categories_list:
            total['charity'] += b['charity']
            total['mt_profit'] += b['mt_profit']
            total['dev'] += b['dev']
            total['admin'] += b['admin']
            total['total_payment'] += b['total_payment']
            total['start_price'] += b['start_price']
            total['post_price'] += b['post_price']
            total['tax'] += b['tax']
        return JsonResponse({'categories': categories_list, 'total': total})
