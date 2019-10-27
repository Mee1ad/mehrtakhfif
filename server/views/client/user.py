from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import PermissionRequiredMixin
from server.views.utils import View
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
        print('this is user profile')
        return JsonResponse({'user': serialize.user(request.user)})

    def put(self, request):
        data = json.loads(request.body)
        request.user.update(first_name=data['first_name'], last_name=data['last_name'], gender=data['gender'],
                            language=data['language'], email=data['email'], meli_code=data['meli_code'])
        return HttpResponse('ok', status=200)


class ShoppingList(View):
    def get(self, request):
        shopping_list = Factor.objects.filter(user=request.user).order_by('created_at')
        return JsonResponse({'shopping_list': FactorSchema().dump(shopping_list, many=True)})


class UserComment(View):
    def get(self, request):
        comments = Comment.objects.filter(user=request.user).order_by('created_at')
        return JsonResponse({'comments': CommentSchema().dump(comments, many=True)})


class AddressView(View):
    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        return JsonResponse({'addresses': AddressSchema().dump(addresses, many=True),
                             'default_address': request.user.default_address})

    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        try:
            assert City.objects.filter(pk=data['city_id'], state_id=data['state_id'])
            address_count = Address.objects.filter(user=request.user).count()
            address = Address(state_id=data['state_id'], city_id=data['city_id'], postal_code=data['postal_code'],
                              address=data['address'], location=data['location'], user=request.user,
                              name=data['name'], phone=data['phone'])
            address.save()
            if address_count < 2 or data['set_default']:
                request.user.default_address = address.pk
                request.user.save()
            return JsonResponse(AddressSchema().dump(address))
        except AssertionError:
            return JsonResponse({}, status=400)

    def patch(self, request):
        data = json.loads(request.body)
        try:
            request.user.default_address = data['id']
            request.user.save()
            return JsonResponse({'message': 'ok'})
        except Exception:
            return JsonResponse({}, status=400)

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
            WishList.objects.filter(user=request.user, product_id=data['product_id'])\
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


class MyTransactions(View):
    def get(self, request):
        pass


class WalletView(View):
    def get(self, request):
        pass