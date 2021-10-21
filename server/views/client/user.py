from django.http import JsonResponse, FileResponse
from django.shortcuts import render_to_response

from mehr_takhfif.settings import INVOICE_ROOT
from server.serialize import *
from server.utils import *
from server.utils import LoginRequired


# from selenium import webdriver

class Profile(LoginRequired):
    def get(self, request):
        user = request.user
        res = {'user': UserSchema().dump(user)}
        if user.is_staff:
            res['user']['is_staff'] = True
            try:
                res['user']['roll'] = user.groups.first().name
            except AttributeError:
                if user.is_superuser:
                    res['user']['roll'] = 'superuser'
        return JsonResponse(res)

    def put(self, request):
        data = load_data(request)
        has_invoice = Invoice.objects.filter(user=request.user).exists()
        if has_invoice:
            required_keys = ['first_name', 'last_name', 'meli_code']
            data = remove_null_from_dict(required_keys, data)
        user = request.user
        user.first_name = data.get('first_name') or user.first_name
        user.last_name = data.get('last_name') or user.last_name
        user.gender = data.get('gender') or user.gender
        # user.language = data.get('language') or language
        user.email = data.get('email') or user.email
        user.meli_code = data.get('meli_code') or user.meli_code
        user.shaba = data.get('shaba') or user.shaba
        if data.get('birthday'):
            user.birthday = timestamp_to_datetime(data.get('birthday'))
        user.subscribe = data.get('subscribe') or user.subscribe
        user.save()
        return JsonResponse({'user': UserSchema().dump(user)})


class Orders(LoginRequired):
    def get(self, request):
        pk = request.GET.get('id', None)
        if pk:
            try:
                invoice = Invoice.objects.get(pk=pk, user=request.user)
            except Invoice.DoesNotExist:
                return JsonResponse({}, status=404)
            return JsonResponse({'data': InvoiceSchema(user=request.user).dump(invoice)})
        orders = user_data_with_pagination(Invoice, InvoiceSchema, request, extra={"final_price__isnull": False})
        return JsonResponse(orders)

    def optimized_get(self, request):
        pk = request.GET.get('id', None)
        only = ('id', 'created_at', 'amount', 'final_price', 'status')
        if pk:
            only += ('address', 'storages')
            invoice_storage_only_field = ('count', 'unit_price', 'discount_price', 'discount', 'storage')
            try:
                prefetch_storages = Storage.objects.all().only('id', 'title', 'invoice_title')
                invoice = Invoice.objects.only(*only).filter(pk=pk, user=request.user) \
                    .prefetch_related(Prefetch('invoice_storages__storage', queryset=prefetch_storages)).first()
            except Invoice.DoesNotExist:
                return JsonResponse({}, status=404)
            only += ('invoice',)
            return JsonResponse({'data': InvoiceSchema(user=request.user, only=only,
                                                       invoice_storage_only_field=invoice_storage_only_field)
                                .dump(invoice)})

        query = Invoice.objects.filter(user=request.user, final_price__isnull=False).only(*only)
        only_fields = {'only': only}
        res = get_pagination(request, query, InvoiceSchema, serializer_args=only_fields)
        return JsonResponse(res)


class InvoiceView(LoginRequired):
    def get(self, request, invoice_id):
        permission_group = ['support', 'accountants', 'superuser']
        user = {'user': request.user, 'status__in': Invoice.success_status}  # payed
        if request.user.groups.filter(name__in=permission_group) or request.user.is_superuser:
            user = {}
        invoice = get_invoice_file(request, invoice_id=invoice_id, user=user)
        return render_to_response('full_invoice.html', invoice)


class OrderProduct(LoginRequired):
    def get(self, request):
        pk = request.GET.get('id', None)
        invoice_product = InvoiceStorage.objects.get(pk=pk, invoice__user=request.user)
        product = invoice_product.storage.product
        # product_dict = ProductSchema(**request.schema_params).dump(product)
        invoice_product = InvoiceStorageSchema().dump(invoice_product)
        # invoice_product['product'] = product_dict
        return JsonResponse(invoice_product)


class Trips(LoginRequired):
    def get(self, request):
        books = user_data_with_pagination(Booking, BooksSchema, request)
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
        addresses = user_data_with_pagination(Address, AddressSchema, request, show_all=request.all)
        default_address = AddressSchema().dump(request.user.default_address) if request.user.default_address else None
        return JsonResponse({'addresses': addresses, 'default_address': default_address})

    # add address
    def post(self, request):
        data = load_data(request)
        try:
            address_count = Address.objects.filter(user=request.user).count()
            city = City.objects.get(pk=data['city_id'])
            address = Address(state=city.state, city=city, postal_code=data['postal_code'],
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
            return JsonResponse({})
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
        request.user.default_address = Address.objects.filter(user=request.user).order_by('-id').first()
        return JsonResponse({})


class UserCommentView(LoginRequired):
    def get(self, request):
        return JsonResponse(user_data_with_pagination(Comment, UserCommentSchema, request))


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
        notify = request.GET.get('notify', None)
        query = {'wish': True}
        if notify:
            query = {'notify': True}
        wishlists = WishList.objects.filter(user=request.user, **query)
        pg = get_pagination(request, wishlists, WishListSchema)
        return JsonResponse(pg)

    def post(self, request):
        data = load_data(request)
        wishlist = WishList.objects.filter(product_id=data['product_id'], user=request.user)
        if wishlist.exists():
            wishlist.update(notify=data.get('notify', F('notify')), wish=data.get('wish', F('wish')),
                            updated_by=request.user)
            return JsonResponse({}, status=200)

        WishList.objects.create(notify=data.get('notify', False), wish=data.get('wish', True),
                                product_id=data['product_id'], user=request.user,
                                created_by=request.user, updated_by=request.user)

        return JsonResponse({}, status=201)

    def delete(self, request):
        wishlist_id = request.GET.get('id', None)
        WishList.objects.filter(pk=wishlist_id, user_id=request.user).delete()
        return JsonResponse({})


class MyTransactions(LoginRequired):
    def get(self, request):
        pass


class WalletView(LoginRequired):
    def get(self, request):
        pass


class ShortLinkView(View):
    def get(self, request, key):
        filename = InvoiceStorage.objects.get(key=key).filename
        file = open(f"{INVOICE_ROOT}/{filename}.pdf", "rb")
        return FileResponse(file, as_attachment=True,
                            filename=f'MehrTakhfif-{filename[::-1].split("-", 1)[1][::-1]}.pdf')
