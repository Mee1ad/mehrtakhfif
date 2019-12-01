from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import PermissionRequiredMixin
from server.views.utils import *
from server.views.admin_panel.read import ReadAdminView
import json
import time
import pysnooper
from django.views.decorators.cache import cache_page
from django.db.models import Max, Min
from server.serialize import *
from server.views.utils import LoginRequired


class Profile(View):
    def get(self, request):
        return JsonResponse({'user': UserSchema().dump(request.user)})

    def put(self, request):
        data = json.loads(request.body)
        # validation(data, 'full_name')
        user = request.user
        user.full_name = data.get('full_name') or user.full_name
        user.gender = data.get('gender') or user.gender
        user.language = data.get('language') or user.language
        user.email = data.get('email') or user.email
        user.meli_code = data.get('meli_code') or user.meli_code
        user.save()
        return JsonResponse({'user': UserSchema().dump(user)})


class ShoppingList(View):
    def get(self, request):
        shopping_list = Invoice.objects.filter(user=request.user)
        return JsonResponse({'shopping_list': InvoiceSchema().dump(shopping_list, many=True)})


class UserComment(View):
    def get(self, request):
        comments = Comment.objects.filter(user=request.user).order_by('created_at')
        return JsonResponse({'comments': CommentSchema().dump(comments, many=True)})


class AddressView(LoginRequired):
    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        addresses = AddressSchema().dump(addresses, many=True)
        default_address = AddressSchema().dump(request.user.default_address)
        return JsonResponse({'addresses': addresses, 'default_address': default_address})

    # add address
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        print(data)
        try:
            assert City.objects.filter(pk=data['city_id'], state_id=data['state_id'])
            address_count = Address.objects.filter(user=request.user).count()
            address = Address(state_id=data['state_id'], city_id=data['city_id'], postal_code=data['postal_code'],
                              address=data['address'], location=data['location'], user=request.user,
                              name=data['name'], phone=data['phone'])
            address.save()
            if address_count < 2 or data['set_default']:
                request.user.default_address_id = address.pk
                request.user.save()
            return JsonResponse(AddressSchema().dump(address))
        except AssertionError:
            return JsonResponse({}, status=400)

    # set default
    @pysnooper.snoop()
    def patch(self, request):
        data = json.loads(request.body)
        try:
            request.user.default_address_id = data['id']
            request.user.save()
            return JsonResponse({'message': 'ok'})
        except Exception:
            return JsonResponse({}, status=400)

    # edit address
    @pysnooper.snoop()
    def put(self, request):
        data = json.loads(request.body)
        try:
            address = Address.objects.filter(pk=data['id'], user=request.user)
            assert address.exists()
            address.update(state_id=data['state_id'], city_id=data['city_id'], postal_code=data['postal_code'],
                           address=data['address'], location=data['location'], user=request.user,
                           name=data['name'], phone=data['phone'])
            if data['set_default']:
                request.user.default_address = address.first().id
                request.user.save()
            return JsonResponse({'message': 'ok'})
        except Exception:
            return JsonResponse({}, status=400)

    def delete(self, request):
        address_id = request.GET.get('id', None)
        Address.objects.filter(pk=address_id, user=request.user).delete()
        return HttpResponse('ok')


class GetState(LoginRequired):
    def get(self, request):
        states = State.objects.all()
        return JsonResponse({'states': StateSchema().dump(states, many=True)})


class GetCity(View):
    def get(self, request, state_id):
        cities = City.objects.filter(state_id=state_id)
        return JsonResponse({'cities': CitySchema().dump(cities, many=True)})


class WishlistView(View):
    def get(self, request):
        wishlists = WishList.objects.filter(user_id=request.user)
        return JsonResponse({'wishlists': WishListSchema(request.lang).dump(wishlists, many=True)})

    def post(self, request):
        data = json.loads(request.body)
        try:
            assert WishList.objects.filter(user=request.user, product_id=data['product_id']).exists()
            WishList(type=data['type'], notify=data['notify'], product_id=data['product_id'], user=request.user,
                     created_by=request.user, updated_by=request.user).save()
            return HttpResponse('ok', status=201)
        except AssertionError:
            WishList.objects.filter(user=request.user, product_id=data['product_id']) \
                .update(type=data['type'])
            return HttpResponse('updated', status=204)

    def delete(self, request):
        product_id = request.GET.get('product_id', None)
        try:
            assert not WishList.objects.filter(user=request.user, product_id=product_id).exists()
            address = WishList.objects.filter(pk=product_id, user_id=request.user).first()
            address.delete()
            return HttpResponse('ok')
        except AssertionError:
            return HttpResponse('product does not exist', status=406)


class NotifyView(View):
    def get(self, request):
        notify = WishList.objects.filter(user_id=request.user)
        return JsonResponse({'wishlists': WishListSchema().dump(notify(notify))})

    def post(self, request):
        data = json.loads(request.body)
        NotifyUser(type=data['type'], notify=data['notify'], product_id=data['product_id'], user_id=request.user).save()
        return HttpResponse(status=201)

    def delete(self, request):
        notify_id = request.GET.get('product_id', None)
        address = WishList.objects.filter(pk=notify_id, user_id=request.user).first()
        address.delete()
        return HttpResponse('ok')


class MyTransactions(View):
    def get(self, request):
        pass


class WalletView(View):
    def get(self, request):
        pass
