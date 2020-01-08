import json

from django.http import JsonResponse

from server.models import *
from server.serialize import *
from server.views.utils import View, default_page, default_step


class Single(View):
    def get(self, request, permalink):
        pass
