from django.views import View
from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core import serializers
import json
from server.views.utils import View
from django.contrib.admin.utils import NestedObjects
from mehr_takhfif.settings import TOKEN_SECRET
import jwt


class AdminView(View, PermissionRequiredMixin, LoginRequiredMixin):
    @staticmethod
    def get_data(request, model, serializer):
        pk = request.GET.get('pk', None)
        start = int(request.GET.get('s', 0))
        end = int(request.GET.get('e', 50))
        try:
            data = model.objects.get(pk=pk)
        except Exception:
            data = model.objects.all().order_by('-created_at')[start:end]
        return JsonResponse({'data': serializer(data)}, status=200)

    def get_token(self, obj, serializer):
        data = {'object': serializer(obj)}
        return jwt.encode(data, TOKEN_SECRET, algorithm='HS256')

    def check_token(self, obj, token, serializer):
        new_token = self.get_token(obj, serializer)
        if token == new_token:
            return True
        return False

    def collect_related(self, obj):
        collector = NestedObjects(using='default')
        collector.collect([obj])
        return collector.nested()

    def get_related(self, pk, model, serializer):
        data = model.objects.filter(pk=pk).first()
        token = self.get_token(data, serializer)
        related_objects = serialize.related_objects(self.collect_related(data))
        return JsonResponse({'related_objects': related_objects, 'token': token})

    def base_delete(self, request, pk, model, serializer):
        token = request.GET.get('token', None)
        data = model.objects.get(pk=pk)
        if not self.check_token(data, token, serializer):
            return HttpResponse(status=404)
        self.safe_delete(data, request.user)
        return HttpResponse('ok')


class NewCategory(AdminView):
    permission_required = 'add_category'

    def post(self, request):
        data = json.loads(request.body)
        if 'box' not in request.session:
            request.session['box_id'] = request.user.box.id
        Category(parent=data['parent'], box=request.session['box_id'], name=data['name'], deactive=data['deactive'],
                 media=data['media'])
        return HttpResponse('ok', status=201)


class NewAddress(AdminView):
    permission_required = 'add_address'

    def post(self, request):
        data = json.loads(request.body)
        Address(province=data['province'], city=data['city'], postal_code=data['postal_code'], address=data['address'],
                 location=data['location'], user_id=data['user_id'])
        return HttpResponse('ok', status=201)


class NewFeature(AdminView):
    permission_required = 'add_feature'

    def post(self, request):
        data = json.loads(request.body)
        Feature(name=data['name'], value=data['value'], category=data['category'])
        return HttpResponse('ok', status=201)


class NewProduct(AdminView):
    permission_required = 'add_product'

    def post(self, request):
        data = json.loads(request.body)
        Product(name=data['name'], permalink=data['permalink'], category=data['category'], gender=data['gender'],
                 short_description=data['short_description'], description=data['description'], media=data['media'],
                 usage_condition=data['usage_condition'], location=data['location'], profit=data['profit'],
                 deactive=data['deactive'], verify=data['verify'], type=data['type'])
        return HttpResponse('ok', status=201)


class NewStorage(AdminView):
    permission_required = 'add_storage'

    def post(self, request):
        data = json.loads(request.body)
        Storage(product_id=data['product_id'], count=data['count'], discount_vip_price=data['discount_vip_price'],
                 available_count_for_sale=data['available_count_for_sale'], available_count=data['available_count'],
                 start_price=data['start_price'], final_price=data['final_price'], default=data['default'],
                 transportation_price=data['transportation_price'], discount_price=data['discount_price'])
        return HttpResponse('ok', status=201)


class NewMenu(AdminView):
    permission_required = 'add_menu'

    def post(self, request):
        data = json.loads(request.body)
        Menu(type=data['type'], name=data['name'], value=data['value'], parent=data['parent'],
                 priority=data['priority'])
        return HttpResponse('ok', status=201)


class NewTag(AdminView):
    permission_required = 'add_tag'

    def post(self, request):
        data = json.loads(request.body)
        if 'box' not in request.session:
            request.session['box_id'] = request.user.box.id
        Tag(product=data['product_id'], name=data['name'], box=request.session['box_id'])
        return HttpResponse('ok', status=201)


class NewSpecialOffer(AdminView):
    permission_required = 'add_specialoffer'

    def post(self, request):
        data = json.loads(request.body)
        if 'box' not in request.session:
            request.session['box_id'] = request.user.box.id
        SpecialOffer(product=data['product_id'], name=data['name'], box=request.session['box_id'], code=data['code'],
                     user_id=data['user_id'], not_accepted_products=data['not_accepted_products'],
                     category=data['category'], discount_price=data['discount_price'], end_date=data['end_date'],
                     discount_percent=data['discount_percent'], vip_discount_price=data['vip_discount_price'],
                     vip_discount_percent=data['vip_discount_percent'], start_date=data['start_date'],
                     least_count=data['least_count'], peak_price=data['peak_price'])
        return HttpResponse('ok', status=201)


class NewSpecialProducts(AdminView):
    permission_required = 'add_specialproducts'

    def post(self, request):
        data = json.loads(request.body)
        SpecialProducts(title=data['title'], link=data['link'], product_id=data['product_id'], media=data['media'],
                        type=data['type'], description=data['description'])
        return HttpResponse('ok', status=201)


class NewBlog(AdminView):
    permission_required = 'add_blog'

    def post(self, request):
        data = json.loads(request.body)
        Blog(title=data['title'], link=data['link'], product_id=data['product_id'], media=data['media'],
             type=data['type'], description=data['description'])
        return HttpResponse('ok', status=201)


class NewBlogPost(AdminView):
    permission_required = 'add_blogpost'

    def post(self, request):
        data = json.loads(request.body)
        BlogPost(blog_id=data['blog_id'], body=data['body'], permalink=data['permalink'], media=data['media'])
        return HttpResponse('ok', status=201)


class NewTourism(AdminView):
    permission_required = 'add_tourism'

    def post(self, request):
        data = json.loads(request.body)
        Tourism(date=data['date'], date2=data['date2'], price=data['price'])
        return HttpResponse('ok', status=201)
