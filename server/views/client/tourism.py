import json

from django.http import JsonResponse

from server.models import *
from server.serialize import *
from server.views.utils import View, load_data
import pysnooper


class BookingView(View):
    def post(self, request):
        data = load_data(request)
        Book.objects.create(user=request.user, house_id=data['house_id'], start_date=data['start_date'],
                            end_date=data['end_date'])
        return JsonResponse({})

    def get(self, request):
        self.create_invoice(1)
        return JsonResponse({})

    def create_invoice(self, house_id):
        house = House.objects.get(pk=house_id)
        prices = HouseSchema.get_prices(house)
