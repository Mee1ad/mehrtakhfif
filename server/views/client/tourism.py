from django.http import JsonResponse

from server.models import *
from server.serialize import *
from server.utils import View, load_data


class HouseView(View):
    def get(self, request):
        pass
        # houses = House.objects.filter(people__gte=)


class BookingView(View):
    def post(self, request):
        data = load_data(request)
        house = House.objects.get(pk=data['house_id'])
        price = HousePriceSchema().dump(house)['price']
        start_date = data['start_date'].split('-')
        end_date = data['end_date'].split('-')
        end_year, end_month, end_day = end_date[0], end_date[1], end_date[2]
        Booking.objects.create(user=request.user, house=house, invoice=invoice, people_count=data['people'],
                               start_date=data['start_date'], end_date=data['end_date'])
        return JsonResponse({})

    def get(self, request):
        self.create_invoice(1)
        return JsonResponse({})

    def create_invoice(self, house_id):
        house = House.objects.get(pk=house_id)
        prices = HouseSchema.get_prices(house)
