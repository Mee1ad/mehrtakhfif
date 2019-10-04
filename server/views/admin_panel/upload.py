from django.views import View
from server.models import *
from django.http import JsonResponse, HttpResponse
from django.utils.timezone import localdate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core import serializers
import json
from server.views.utils import Tools
from server.decorators import try_except


class AdminView(Tools, PermissionRequiredMixin, LoginRequiredMixin):
    pass


class BoxMedia(AdminView):
    permission_required = 'add_media'

    @try_except
    def post(self, request):
        data = json.loads(request.POST.get('data'))
        title = data['title']
        # box = request.user.box
        if self.upload(request, title, box=1):
            return HttpResponse('ok')
        return HttpResponse('error')
