from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server import serializer as serialize
from server.views.mylib import Tools
from server.views.admin_panel.read import ReadAdminView
import json
import time
import pysnooper
from django.views.decorators.cache import cache_page
from django.db.models import Max, Min
from server.serialize import *


class Profile(Tools):
    def get(self, request):
        return JsonResponse({'user': serialize.user(request.user)})

    def put(self, request):
        data = json.loads(request.body)
        request.user.update(first_name=data['first_name'], last_name=data['last_name'], gender=data['gender'],
                            language=data['language'], email=data['email'], meli_code=data['meli_code'])
        return HttpResponse('ok', status=200)


class AddressView(Tools):
    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        return JsonResponse({'addresses': addresses})

    def post(self, request):
        data = json.loads(request.body)
        Address(province=data['province'], city=data['city'], postal_code=data['postal_code'],
                address=data['address'], location=data['location'], user=request.user)

    def delete(self, request):
        address_id = request.GET.get('address_id', None)
        address = Comment.objects.filter(pk=address_id, user=request.user).first()
        address.delete()
        return HttpResponse('ok')


class WishlistView(Tools):
    def get(self, request):
        wishlists = WishList.objects.filter(user_id=request.user)
        return JsonResponse({'wishlists': serialize.wishlist(wishlists)})

    def post(self, request):
        data = json.loads(request.body)
        WishList(type=data['type'], notify=data['notify'], product_id=data['product_id'], user_id=request.user,
                 created_by=request.user, updated_by=request.user).save()
        return HttpResponse(status=201)

    def delete(self, request):
        product_id = request.GET.get('product_id', None)
        address = WishList.objects.filter(pk=product_id, user_id=request.user).first()
        address.delete()
        return HttpResponse('ok')


class NotifyView(Tools):
    def get(self, request):
        notify = WishList.objects.filter(user_id=request.user)
        return JsonResponse({'wishlists': serialize.notify(notify)})

    def post(self, request):
        data = json.loads(request.body)
        NotifyUser(type=data['type'], notify=data['notify'], product_id=data['product_id'], user_id=request.user).save()
        return HttpResponse(status=201)

    def delete(self, request):
        notify_id = request.GET.get('product_id', None)
        address = WishList.objects.filter(pk=notify_id, user_id=request.user).first()
        address.delete()
        return HttpResponse('ok')


class MyTransactions(Tools):
    def get(self, request):
        pass


class WalletView(Tools):
    def get(self, request):
        pass