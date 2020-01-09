import json

from django.http import JsonResponse

from server.models import *
from server.serialize import *
from server.views.utils import View, load_data


class BookingView(View):
    def post(self, request):
        data = load_data(request)
        Book.objects.create(user=request.user, house_id=data['house_id'], start_date=data['start_date'],
                            end_date=data['end_date'])
        return JsonResponse({})
