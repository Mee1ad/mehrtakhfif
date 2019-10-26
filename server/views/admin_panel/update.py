from django.views import View
from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core import serializers
import json
from server.views.utils import View


class UpdateAdminView(View, PermissionRequiredMixin, LoginRequiredMixin):
    pass


class UpdateCategory(UpdateAdminView):
    permission_required = 'change_category'

    def put(self, request):
        data = json.loads(request.body)
        category_id = data['category_id']
        if 'box' not in request.session:
            request.session['box_id'] = request.user.box.id
        Category.objects.filter(
            pk=category_id).update(parent=data['parent'], box=request.session['box_id'],
                                   name=data['name'], deactive=data['deactive'], media=data['media'])
        return HttpResponse('ok', status=200)


class UpdateAddress(UpdateAdminView):
    permission_required = 'change_address'

    def put(self, request):
        data = json.loads(request.body)
        address_id = data['address_id']
        Address.objects.filter(
            pk=address_id).update(province=data['province'], city=data['city'], postal_code=data['postal_code'],
                                  address=data['address'], location=data['location'], user_id=data['user_id'])
        return HttpResponse('ok', status=200)


class UpdateFeature(UpdateAdminView):
    permission_required = 'change_feature'

    def put(self, request):
        data = json.loads(request.body)
        Feature.objects.filter(pk=data['feature_id']).update(name=data['name'], value=data['value'],
                                                             category=data['category'])
        return HttpResponse('ok', status=200)


class UpdateProduct(UpdateAdminView):
    permission_required = 'change_product'

    def put(self, request):
        data = json.loads(request.body)
        Product.objects.filter(pk=data['product_id']).update(
            name=data['name'], permalink=data['permalink'], category=data['category'], gender=data['gender'],
            short_description=data['short_description'], description=data['description'], media=data['media'],
            usage_condition=data['usage_condition'], location=data['location'], profit=data['profit'],
            deactive=data['deactive'], verify=data['verify'], type=data['type'])
        return HttpResponse('ok', status=200)


class UpdateStorage(UpdateAdminView):
    permission_required = 'change_storage'

    def put(self, request):
        data = json.loads(request.body)
        Storage.objects.filter(pk=data['storage_id']).update(
            product_id=data['product_id'], count=data['count'], discount_vip_price=data['discount_vip_price'],
            available_count_for_sale=data['available_count_for_sale'], available_count=data['available_count'],
            start_price=data['start_price'], final_price=data['final_price'], default=data['default'],
            transportation_price=data['transportation_price'], discount_price=data['discount_price'])
        return HttpResponse('ok', status=200)


class UpdateMenu(UpdateAdminView):
    permission_required = 'change_menu'

    def put(self, request):
        data = json.loads(request.body)
        Menu.objects.filter(pk=data['menu_id']).update(type=data['type'], name=data['name'], value=data['value'],
                                                       parent=data['parent'], priority=data['priority'])
        return HttpResponse('ok', status=200)


class UpdateTag(UpdateAdminView):
    permission_required = 'change_tag'

    def put(self, request):
        data = json.loads(request.body)
        if 'box' not in request.session:
            request.session['box_id'] = request.user.box.id
        Tag.objects.filter(pk=data['tag_id']).update(product=data['product_id'], name=data['name'],
                                                     box=request.session['box_id'])
        return HttpResponse('ok', status=200)


class UpdateSpecialOffer(UpdateAdminView):
    permission_required = 'change_specialoffer'

    def put(self, request):
        data = json.loads(request.body)
        if 'box' not in request.session:
            request.session['box_id'] = request.user.box.id
        SpecialOffer.objects.filter(
            pk=data['special_offer_id']).update(
            product=data['product_id'], name=data['name'],
            box=request.session['box_id'], code=data['code'],
            user_id=data['user_id'], not_accepted_products=data['not_accepted_products'],
            category=data['category'], discount_price=data['discount_price'], end_date=data['end_date'],
            discount_percent=data['discount_percent'], vip_discount_price=data['vip_discount_price'],
            vip_discount_percent=data['vip_discount_percent'], start_date=data['start_date'],
            least_count=data['least_count'], peak_price=data['peak_price'])
        return HttpResponse('ok', status=200)


class UpdateSpecialProducts(UpdateAdminView):
    permission_required = 'change_specialproducts'

    def put(self, request):
        data = json.loads(request.body)
        SpecialProducts.objects.filter(pk=data['special_product_it']).update(
            title=data['title'], link=data['link'], product_id=data['product_id'], media=data['media'],
            type=data['type'], description=data['description'])
        return HttpResponse('ok', status=200)


class UpdateBlog(UpdateAdminView):
    permission_required = 'change_blog'

    def put(self, request):
        data = json.loads(request.body)
        Blog.objects.filter(pk=data['blog_id']).update(
            title=data['title'], link=data['link'], product_id=data['product_id'], media=data['media'],
            type=data['type'], description=data['description'])
        return HttpResponse('ok', status=200)


class UpdateBlogPost(UpdateAdminView):
    permission_required = 'change_blogpost'

    def put(self, request):
        data = json.loads(request.body)
        BlogPost.objects.filter(pk=data['blog_post_id']).update(
            blog_id=data['blog_id'], body=data['body'], permalink=data['permalink'], media=data['media'])
        return HttpResponse('ok', status=200)


class UpdateTourism(UpdateAdminView):
    permission_required = 'change_tourism'

    def put(self, request):
        data = json.loads(request.body)
        Tourism.objects.filter(pk=data['tourism_id']).update(date=data['date'], date2=data['date2'],
                                                             price=data['price'])
        return HttpResponse('ok', status=200)
