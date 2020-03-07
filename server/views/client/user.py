from django.http import JsonResponse, HttpResponse, FileResponse, HttpResponseRedirect

from server.serialize import *
from server.utils import *
from server.utils import LoginRequired
from mehr_takhfif.settings import INVOICE_ROOT
import pysnooper


class Profile(LoginRequired):
    def get(self, request):
        return JsonResponse({'user': UserSchema().dump(request.user)})

    def put(self, request):
        data = load_data(request)
        user = request.user
        user.first_name = data.get('first_name') or user.first_name
        user.last_name = data.get('last_name') or user.last_name
        user.gender = data.get('gender') or user.gender
        # user.language = data.get('language') or language
        user.email = data.get('email') or user.email
        user.meli_code = data.get('meli_code') or user.meli_code
        user.shaba = data.get('shaba') or user.shaba
        user.birthday = data.get('birthday') or user.birthday
        user.subscribe = data.get('subscribe') or user.subscribe
        user.save()
        return JsonResponse({'user': UserSchema().dump(user)})


class Avatar(LoginRequired):
    def post(self, request):
        user = request.user
        pre_avatar_id = None
        if user.avatar:
            pre_avatar_id = user.avatar.id
        title = {"user_id": f"{user.id}"}
        media = upload(request, [title], 'avatar')
        if media:
            user.avatar = media
            user.save()
            if pre_avatar_id:
                Media.objects.filter(pk=pre_avatar_id).delete()
            return JsonResponse({"media": MediaSchema().dump(media, many=True)})
        return JsonResponse({}, status=400)

    def delete(self, request):
        user = request.user
        user.avatar.delete()
        user.avatar = None
        user.save()
        return JsonResponse({})


class Orders(LoginRequired):
    @pysnooper.snoop()
    def get(self, request):
        pk = request.GET.get('id', None)
        if pk:
            invoice_exists = Invoice.objects.filter(pk=pk, user=request.user)
            assert invoice_exists
            products = InvoiceStorage.objects.filter(invoice_id=pk)
            invoice = invoice_exists.first()
            address = AddressSchema().dump(invoice.address)
            products = InvoiceStorageSchema().dump(products, many=True)
            return JsonResponse({"products": products, 'address': address,
                                 'status': invoice.get_status_display(), 'amount': invoice.amount})
        orders = user_data_with_pagination(Invoice, InvoiceSchema, request)
        return JsonResponse(orders)


class OrderProduct(LoginRequired):
    def get(self, request):
        pk = request.GET.get('id', None)
        invoice_product = InvoiceStorage.objects.get(pk=pk, invoice__user=request.user)
        product = invoice_product.storage.product
        # product_dict = ProductSchema(language=request.lang).dump(product)
        invoice_product = InvoiceStorageSchema().dump(invoice_product)
        # invoice_product['product'] = product_dict
        return JsonResponse(invoice_product)


class Trips(LoginRequired):
    def get(self, request):
        books = user_data_with_pagination(Book, BooksSchema, request)
        return JsonResponse(books)


class AddressView(LoginRequired):
    """
        Display an individual :model:`server.Address`.

        **Context**

        ``Address``
            An instance of :model:`server.Address`.

        **Template:**

        :template:`server/my_template.html`
    """

    def get(self, request):
        addresses = user_data_with_pagination(Address, AddressSchema, request)
        default_address = AddressSchema().dump(request.user.default_address)
        return JsonResponse({'addresses': addresses, 'default_address': default_address})

    # add address
    def post(self, request):
        data = load_data(request)
        try:
            assert City.objects.filter(pk=data['city_id'], state_id=data['state_id'])
            address_count = Address.objects.filter(user=request.user).count()
            address = Address(state_id=data['state_id'], city_id=data['city_id'], postal_code=data['postal_code'],
                              address=data['address'], location=load_location(data['location']), user=request.user,
                              name=data['name'], phone=data['phone'])
            address.save()
            if address_count < 2 or data['set_default']:
                request.user.default_address_id = address.pk
                request.user.save()
            return JsonResponse(AddressSchema().dump(address))
        except AssertionError:
            return JsonResponse({}, status=400)

    # set default
    def patch(self, request):
        data = load_data(request)
        try:
            request.user.default_address_id = data['id']
            request.user.save()
            return JsonResponse({'message': 'ok'})
        except Exception:
            return JsonResponse({}, status=400)

    # edit address
    def put(self, request):
        data = load_data(request)
        address = Address.objects.filter(pk=data['id'], user=request.user)
        assert address.exists()
        address.update(state_id=data['state_id'], city_id=data['city_id'], postal_code=data['postal_code'],
                       address=data['address'], location=load_location(data['location']), user=request.user,
                       name=data['name'], phone=data['phone'])
        if data['set_default']:
            request.user.default_address = address.first().id
            request.user.save()
        return JsonResponse(AddressSchema().dump(address.first()))

    def delete(self, request):
        address_id = request.GET.get('id', None)
        Address.objects.filter(pk=address_id, user=request.user).delete()
        return JsonResponse({})


class CommentView(LoginRequired):
    def get(self, request):
        return JsonResponse(user_data_with_pagination(Comment, CommentSchema, request))


class GetState(LoginRequired):
    def get(self, request):
        states = State.objects.all()
        return JsonResponse({'states': StateSchema().dump(states, many=True)})


class GetCity(LoginRequired):
    def get(self, request, state_id):
        cities = City.objects.filter(state_id=state_id)
        return JsonResponse({'cities': CitySchema().dump(cities, many=True)})


class WishlistView(LoginRequired):
    def get(self, request):
        wishlists = WishList.objects.filter()
        pg = get_pagination(wishlists, request.step, request.page, WishListSchema)

        return JsonResponse(pg)

    def post(self, request):
        data = load_data(request)
        WishList.objects.update_or_create(type=data['type'], notify=data['notify'], product_id=data['product_id'],
                                          user=request.user,
                                          created_by=request.user, updated_by=request.user)
        return JsonResponse({}, status=201)

    def delete(self, request):
        wishlist_id = request.GET.get('id', None)
        WishList.objects.filter(pk=wishlist_id, user_id=request.user).delete()
        return JsonResponse({})


class NotifyView(LoginRequired):
    def get(self, request):
        notify = WishList.objects.filter(user_id=request.user)
        return JsonResponse({'wishlists': WishListSchema().dump(notify(notify))})

    def post(self, request):
        data = load_data(request)
        NotifyUser(type=data['type'], notify=data['notify'], product_id=data['product_id'], user_id=request.user).save()
        return JsonResponse({}, status=201)

    def delete(self, request):
        notify_id = request.GET.get('product_id', None)
        address = WishList.objects.filter(pk=notify_id, user_id=request.user).first()
        address.delete()
        return JsonResponse({'message': 'ok'})


class MyTransactions(LoginRequired):
    def get(self, request):
        pass


class WalletView(LoginRequired):
    def get(self, request):
        pass


import io


class ShortLinkView(View):
    @pysnooper.snoop()
    def get(self, request, key):
        name = InvoiceStorage.objects.get(key=key).storage.product.name['fa']
        file = open(f"{INVOICE_ROOT}/456.pdf", "rb")
        return FileResponse(file, filename='test6.pdf')

