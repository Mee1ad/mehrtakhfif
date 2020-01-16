import json
import pysnooper

from django.http import JsonResponse

from server.serialize import *
from server.views.utils import *
from server.views.utils import LoginRequired
from server.decorators import try_except
from mehr_takhfif.settings import HOST


class Profile(View):
    def get(self, request):
        return JsonResponse({'user': UserSchema().dump(request.user)})

    @try_except
    def put(self, request):
        data = json.loads(request.body)
        # validation(data)
        user = request.user
        user.first_name = data.get('first_name') or user.first_name
        user.last_name = data.get('last_name') or user.last_name
        user.gender = data.get('gender') or user.gender
        # user.language = data.get('language') or user.language
        user.email = data.get('email') or user.email
        user.meli_code = data.get('meli_code') or user.meli_code
        user.shaba = data.get('shaba') or user.shaba
        user.birthday = data.get('birthday') or user.birthday
        user.subscribe = data.get('subscribe') or user.subscribe
        user.save()
        return JsonResponse({'user': UserSchema().dump(user)})


class Avatar(View):
    def post(self, request):
        user = request.user
        pre_avatar_id = None
        if user.avatar:
            pre_avatar_id = user.avatar.id
        title = {"user_id": f"{user.id}"}
        media = upload(request, title, avatar=True)
        if media:
            user.avatar = media
            user.save()
            if pre_avatar_id:
                Media.objects.filter(pk=pre_avatar_id).delete()
            return JsonResponse({"url": HOST + media.file.url})
        return JsonResponse({}, status=400)

    def delete(self, request):
        user = request.user
        user.avatar.delete()
        user.avatar = None
        user.save()
        return JsonResponse({})


class Orders(View):
    def get(self, request):
        orders = user_data_with_pagination(Invoice, InvoiceSchema, request)
        return JsonResponse(orders)


class Trips(View):
    def get(self, request):
        books = user_data_with_pagination(Book, BooksSchema, request)
        return JsonResponse(books)


class AddressView(LoginRequired):
    def get(self, request):
        addresses = user_data_with_pagination(Address, AddressSchema, request)
        default_address = AddressSchema().dump(request.user.default_address)
        return JsonResponse({'addresses': addresses, 'default_address': default_address})

    # add address
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        validation(data)
        try:
            assert City.objects.filter(pk=data['city_id'], state_id=data['state_id'])
            address_count = Address.objects.filter(user=request.user).count()
            address = Address(state_id=data['state_id'], city_id=data['city_id'], postal_code=data['postal_code'],
                              address=data['address'], location=load_location(data['location']), user=request.user,
                              name=data['fullname'], phone=data['phone'])
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
                           address=data['address'], location=load_location(data['location']), user=request.user,
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
        return JsonResponse({})


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
        import time
        time.sleep(5)
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('p', default_page))
        wishlists = WishList.objects.filter(user_id=request.user)
        last_page_info = last_page(wishlists, step)
        wishlists = wishlists[(page - 1) * step:step * page]
        for w, i in zip(wishlists, range(step)):
            w.product.name['persian'] += f'{(step * (page - 1)) + i}'
        wishlists = WishListSchema(request.lang).dump(wishlists, many=True)
        return JsonResponse({'wishlists': wishlists, **last_page_info})

    def post(self, request):
        data = json.loads(request.body)
        try:
            assert WishList.objects.filter(user=request.user, product_id=data['product_id']).exists()
            WishList(type=data['type'], notify=data['notify'], product_id=data['product_id'], user=request.user,
                     created_by=request.user, updated_by=request.user).save()
            return JsonResponse({'message': 'ok'}, status=201)
        except AssertionError:
            WishList.objects.filter(user=request.user, product_id=data['product_id']) \
                .update(type=data['type'])
            return JSONField({'message': 'updated'}, status=204)

    def delete(self, request):
        wishlist_id = request.GET.get('wishlist_id', None)
        try:
            address = WishList.objects.get(pk=wishlist_id, user_id=request.user)
            address.delete()
            return JsonResponse({'message': 'ok'})
        except WishList.DoesNotExist:
            return JsonResponse({'message': 'product does not exist'}, status=406)


class NotifyView(View):
    def get(self, request):
        notify = WishList.objects.filter(user_id=request.user)
        return JsonResponse({'wishlists': WishListSchema().dump(notify(notify))})

    def post(self, request):
        data = json.loads(request.body)
        NotifyUser(type=data['type'], notify=data['notify'], product_id=data['product_id'], user_id=request.user).save()
        return JsonResponse({}, status=201)

    def delete(self, request):
        notify_id = request.GET.get('product_id', None)
        address = WishList.objects.filter(pk=notify_id, user_id=request.user).first()
        address.delete()
        return JsonResponse({'message': 'ok'})


class MyTransactions(View):
    def get(self, request):
        pass


class WalletView(View):
    def get(self, request):
        pass
