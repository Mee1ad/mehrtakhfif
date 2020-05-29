import jdatetime
from django.http import JsonResponse
from jdatetime import datetime

from server.models import *
from server.serialize import *
from server.utils import View, load_data, add_minutes


class HouseView(View):
    def get(self, request):
        pass
        # houses = House.objects.filter(people__gte=)


class BookingView(View):
    def post(self, request):
        user = request.user
        data = load_data(request)
        start_date = data['start_date']
        end_date = data['end_date']
        guest_count = data['guest']
        house = House.objects.get(pk=data['house_id'])
        price = self.calculate_book_price(request, house, start_date, end_date, guest_count)
        invoice = Invoice.objects.create(created_by=user, updated_by=user, user=user,
                                         amount=price, type=1, address=data.get('address', None),
                                         final_price=price, expire=add_minutes(1))
        Booking.objects.create(user=request.user, house=house, invoice=invoice, people_count=guest_count,
                               start_date=start_date, end_date=end_date)
        return JsonResponse({})

    def calculate_book_price(self, request, house, start_date, end_date, guest_count=0):
        price = HousePriceSchema(**request.schema_params).dump(house)['price']
        guest_price = price['guest']
        price = price['months']
        assert datetime.strptime(start_date, '%Y-%m-%d') <= datetime.strptime(end_date, '%Y-%m-%d')
        start_date = start_date.split('-')
        end_date = end_date.split('-')
        start_year, start_month, start_day = int(start_date[0]), int(start_date[1]), int(start_date[2])
        end_year, end_month, end_day = int(end_date[0]), int(end_date[1]), int(end_date[2])
        assert end_year - start_year < 2
        book_month = next(month for month in price if month['month'] == start_month and month['year'] == start_year)
        amount = 0
        if end_month != start_month:
            days = book_month['days'][start_day - 1:]
            current_index = price.index(book_month)
            months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            for month in months[start_month:end_month] or months[start_month:] + months[:end_month]:
                current_index += 1
                if month == end_month:
                    days += price[current_index]['days'][:end_day]
                    continue
                days += price[current_index]['days']
        else:
            days = book_month['days'][start_day - 1:end_day]
        for day in days:
            amount += day['price'] + guest_count * guest_price
        return amount

    def get_booking_price(self, request):
        house = House.objects.get(pk=1)
        price = HousePriceSchema(**request.schema_params).dump(house)['price']['months']
        start_date = '1399-2-5'
        end_date = '1400-8-8'
        assert jdatetime.datetime.strptime(start_date, '%Y-%m-%d') <= jdatetime.datetime.strptime(end_date, '%Y-%m-%d')
        start_date = ['1399', '2', '15']
        end_date = ['1399', '2', '30']
        start_year, start_month, start_day = int(start_date[0]), int(start_date[1]), int(start_date[2])
        end_year, end_month, end_day = int(end_date[0]), int(end_date[1]), int(end_date[2])
        assert end_year - start_year < 2
        book_month = next(month for month in price if month['month'] == start_month and month['year'] == start_year)
        amount = 0
        if end_month != start_month:
            days = book_month['days'][start_day - 1:]
            current_index = price.index(book_month)
            months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            for month in months[start_month:end_month] or months[start_month:] + months[:end_month]:
                current_index += 1
                if month == end_month:
                    days += price[current_index]['days'][:end_day]
                    continue
                days += price[current_index]['days']
        else:
            days = book_month['days'][start_day - 1:end_day]
        for day in days:
            amount += day['price']
        return JsonResponse({'amount': amount})
