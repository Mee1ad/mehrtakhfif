import json
from operator import attrgetter
from statistics import mean, StatisticsError
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.core.mail import send_mail
from server.models import *
from server.serialize import *
from django.db.models import Q
from server.views.auth import Login, Activate
from django.contrib.auth import login
from mehr_takhfif.settings import TOKEN_SALT
from server.views.utils import *


class AdminView(LoginRequiredMixin, View):

    def serialized_objects(self, request, model, serializer):
        pk = request.GET.get('pk', None)
        if pk:
            obj = model.objects.get(pk=pk)
            return serializer().dump(obj)
        query = model.objects.all()
        return get_pagination(query, request.step, request.page, serializer)

    def get_data(self, request):
        token = get_token_from_cookie(request)
        assert check_access_token(token, request.user, model=None, pk=None)
        data = json.loads(request.body)
        remove = ['created_at', 'created_by', 'updated_at', 'updated_by', 'deleted_by', 'income', 'profit',
                  'rate', 'default_storage', 'sold_count', 'feature']
        [data.pop(k, None) for k in remove]
        box_id = data.get('box_id', None)
        data['box_id'] = self.validate_box_id(request.user, box_id)
        if request.method == "POST":
            data.pop('id', None)
        return data

    def validate_box_id(self, user, box_id=None):
        roll = get_roll(user)
        if roll == 'admin':
            return user.box.pk
        if roll in rolls:
            return box_id
        raise ValidationError

    def assign_default_value(self, product_id):
        storages = Storage.objects.filter(product_id=product_id)
        Product.objects.filter(pk=product_id).update(default_storage=min(storages, key=attrgetter('discount_price')))

    def create_object(self, request, model, serializer):
        data = self.get_data(request)
        user = request.user
        obj = model.objects.create(**data, created_by=user, updated_by=user)
        if model == Storage:
            self.assign_default_value(obj.product_id)
        return self.serialized_objects(request, model, serializer)

    def update_object(self, request, model):
        data = self.get_data(request)
        model.objects.filter(pk=data['id']).update(**data)

    def delete_base(self, request, model):
        pk = int(request.GET.get('id', None))
        if request.token:
            if self.delete_object(request, model, pk):
                return JsonResponse({})
            return JsonResponse({}, status=400)
        return self.prepare_for_delete(model, pk, request.user)

    def prepare_for_delete(self, model, pk, user):
        item = model.objects.get(pk=pk)
        collector = NestedObjects(using='default')
        collector.collect([item])
        data = collector.nested()
        related_objects = []
        deleted_item = None
        for item in data:
            if type(item) == list:
                for nested_item in item:
                    if type(nested_item) == list:
                        continue
                    related_objects.append({'model': f'{nested_item.__class__.__name__}', 'id': nested_item.pk,
                                            'name': f'{nested_item}'})
            else:
                deleted_item = f'{item}'
        if len(related_objects) > 0:
            res = JsonResponse({'deleted_item': deleted_item, 'related_objects': related_objects})
        else:
            res = JsonResponse({'deleted_item': deleted_item})
            res = set_token(user, res)
        return res

    def delete_object(self, request, model, pk):
        token = get_token_from_cookie(request)
        user = request.user
        if check_access_token(token, user, model, pk):
            safe_delete(Category, pk, user.id)
            return True
        return False


class Token(AdminView):
    def get(self, request):
        res = JsonResponse({'token': get_access_token(request.user)})
        res = set_token(request.user, res)
        return res


class AdminLogin(AdminView):
    def post(self, request):
        data = load_data(request)
        meli_code = data['meli_code']
        password = data['password']
        user = User.objects.get(Q(meli_code=meli_code), (Q(is_staff=True) | Q(is_superuser=True)))
        if user.is_ban:
            return JsonResponse({'message': 'user is banned'}, status=493)
        assert user.check_password(password)
        return set_token(user, Login.send_activation(user))


class AdminActivate(AdminView):
    def post(self, request):
        data = load_data(request)
        # TODO: get csrf code
        try:
            client_token = request.get_signed_cookie('token', False, salt=TOKEN_SALT)
            code = data['code']
            user = User.objects.get(Q(activation_code=code, token=client_token, is_ban=False,
                                    activation_expire__gte=timezone.now()), (Q(is_staff=True) | Q(is_superuser=True)))
            user.activation_expire = timezone.now()
            user.is_active = True
            user.save()
            login(request, user)
            res = JsonResponse(UserSchema().dump(user), status=201)  # signup without password
            if Login.check_password(user):
                res = JsonResponse(UserSchema().dump(user))  # successful login
                res.delete_cookie('token')
            return res
        except Exception:
            return JsonResponse({'message': 'code not found'}, status=406)


class CheckPrices(AdminView):
    def post(self, request):
        data = json.loads(request.body)
        sp = data['start_price']
        fp = data['final_price']
        dp = data.get('discount_price', None)
        dvp = data.get('vip_discount_price', None)
        dper = data.get('discount_percent', None)
        dvper = data.get('vip_discount_percent', None)

        if dp and dvp:
            dper = 100 - dp / fp * 100
            dvper = 100 - dvp / fp * 100
            if dper < sp or dvper < sp:
                return JsonResponse({}, status=res_code['bad_request'])
            return JsonResponse({'discount_percent': "%.2f" % dper, 'vip_discount_percent': "%.2f" % dvper})
        elif dper and dvper:
            pass


class CategoryView(AdminView):

    def get(self, request):
        return JsonResponse({'data': self.serialized_objects(request, Category, CategorySchema)})

    def post(self, request):
        last_items = self.create_object(request, Category, CategorySchema)
        return JsonResponse(last_items, status=201)

    def patch(self, request):
        data = self.get_data(request)
        category = Category.objects.filter(pk=data['category']).first()
        features = Feature.objects.filter(pk__in=data['features'])
        category.feature_set.add(*features)
        return JsonResponse({})

    def put(self, request):
        self.update_object(request, Category)
        return JsonResponse({})

    def delete(self, request):
        return self.delete_base(request, Category)


class FeatureView(AdminView):

    def get(self, request):
        return JsonResponse(self.serialized_objects(request, Feature, FeatureSchema))

    def post(self, request):
        items = self.create_object(request, Feature, FeatureSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        self.update_object(request, Feature)
        return JsonResponse({})

    def delete(self, request):
        return self.delete_base(request, Feature)


class ProductView(AdminView):

    def get(self, request):
        return self.serialized_objects(request, Product, ProductSchema)

    def post(self, request):
        items = self.create_object(request, Product, MinProductSchema)
        return JsonResponse(items, status=201)

    def patch(self, request):
        data = self.get_data(request)
        product = Product.objects.filter(pk=data['product']).first()
        tags = Tag.objects.filter(pk__in=data['tags'])
        media = Media.objects.filter(pk__in=data['media'])
        product.tag.add(*tags)
        product.media.add(*media)
        return JsonResponse({})

    def put(self, request):
        self.update_object(request, Product)
        return JsonResponse({})

    def delete(self, request):
        return self.delete_base(request, Product)


class StorageView(AdminView):

    def get(self, request):
        return self.serialized_objects(request, Storage, StorageSchema)

    def post(self, request):
        storage = self.create_object(request, Storage, MinStorageSchema)

        return JsonResponse(storage, status=201)

    def patch(self, request):
        data = self.get_data(request)
        storage = Storage.objects.filter(pk=data['storage']).first()
        features = Feature.objects.filter(pk__in=data['features'])
        storage.feature.add(*features)
        return JsonResponse({})

    def put(self, request):
        self.update_object(request, Storage)
        return JsonResponse({})

    def delete(self, request):
        return self.delete_base(request, Storage)


class MenuView(AdminView):

    def get(self, request):
        return self.serialized_objects(request, Menu, MenuSchema)

    def post(self, request):
        items = self.create_object(request, Menu, MenuSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        self.update_object(request, Menu)
        return JsonResponse({})

    def delete(self, request):
        return self.delete_base(request, Menu)


class TagView(AdminView):

    def get(self, request):
        return self.serialized_objects(request, Tag, TagSchema)

    def post(self, request):
        items = self.create_object(request, Tag, TagSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        self.update_object(request, Tag)
        return JsonResponse({})

    def delete(self, request):
        return self.delete_base(request, Tag)


class SpecialOfferView(AdminView):

    def get(self, request):
        return self.serialized_objects(request, SpecialOffer, SpecialOfferSchema)

    def post(self, request):
        items = self.create_object(request, SpecialOffer, SpecialOfferSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        self.update_object(request, SpecialOffer)
        return JsonResponse({})

    def delete(self, request):
        return self.delete_base(request, SpecialOffer)


class SpecialProductsView(AdminView):

    def get(self, request):
        return self.serialized_objects(request, SpecialProduct, SpecialProductSchema)

    def post(self, request):
        items = self.create_object(request, SpecialProduct, MinSpecialProductSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        self.update_object(request, SpecialProduct)
        return JsonResponse({})

    def delete(self, request):
        return self.delete_base(request, SpecialProduct)


class MediaView(AdminView):
    def post(self, request):
        data = json.loads(request.POST.get('data'))
        titles = data['titles']
        box_id = data['box_id']
        box_id = self.validate_box_id(request.user, box_id)
        if upload(request, titles, box_id):
            return JsonResponse({})
        return JsonResponse({}, status=res_code['bad_request'])


class BlogView(AdminView):

    def get(self, request):
        return self.serialized_objects(request, Blog, BlogSchema)

    def post(self, request):
        items = self.create_object(request, Blog, BlogSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        self.update_object(request, Blog)
        return JsonResponse({})

    def delete(self, request):
        return self.delete_base(request, Blog)


class BlogPostView(AdminView):

    def get(self, request):
        return self.serialized_objects(request, BlogPost, BlogPostSchema)

    def post(self, request):
        items = self.create_object(request, BlogPost, BlogPostSchema)
        return JsonResponse(items, status=201)

    def put(self, request):
        self.update_object(request, BlogPost)
        return JsonResponse({})

    def delete(self, request):
        return self.delete_base(request, BlogPost)


class MailView(AdminView):
    def post(self, request):
        send_mail(
            'Subject here',
            'Here is the message.',
            'from@example.com',
            ['to@example.com'],
            fail_silently=False,
        )


class CommentView(AdminView):
    def patch(self, request):
        data = self.get_data(request)
        pk = data['id']
        comment = Comment.objects.get(pk=pk)
        duplicate_comment = Comment.objects.filter(user=comment.user, type=2, product=comment.product,
                                                   approved=True).count() > 1
        comment.approved = True
        comment.save()
        rates = Comment.objects.filter(product_id=comment.product_id, approved=True, type=2).values_list('rate')
        try:
            if duplicate_comment:
                raise StatisticsError
            average_rate = round(mean([rate[0] for rate in rates]))
            Product.objects.filter(pk=comment.product_id).update(rate=average_rate)
        except StatisticsError:
            pass
        return JsonResponse({})

    def delete(self, request):
        pk = int(request.GET.get('id', None))
        Comment.objects.filter(pk=pk).update(suspend=True)
        return JsonResponse({})