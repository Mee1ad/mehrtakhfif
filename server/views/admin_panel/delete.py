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
from django.views.generic.edit import DeleteView
from django.urls import reverse_lazy
from django.contrib.admin.utils import NestedObjects
import jwt
from mehr_takhfif.settings import TOKEN_SECRET


class DeleteAdminView(View, PermissionRequiredMixin):
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


class DeleteCategory(DeleteAdminView):
    permission_required = 'delete_category'

    def get(self, request, pk):
        category = Category.objects.filter(pk=pk).first()
        token = self.get_token(category, serialize.category)
        related_objects = serialize.related_objects(self.collect_related(category))
        if category.box == request.user.box:
            return JsonResponse({'related_objects': related_objects, 'token': token})
        return HttpResponse(status=403)

    def delete(self, request, pk):
        return self.base_delete(request, pk, Category, serialize.category)


class DeleteAddress(DeleteAdminView):
    permission_required = 'delete_address'

    def get(self, request, pk):
        return self.get_related(pk, Address, serialize.address)

    def delete(self, request, pk):
        self.base_delete(request, pk, Address, serialize.address)


class DeleteFeatureData(DeleteAdminView):
    permission_required = 'delete_featuredata'

    def get(self, request, pk):
        return self.get_related(pk, FeatureData, serialize.feature_data)

    def delete(self, request, pk):
        self.base_delete(request, pk, FeatureData, serialize.feature_data)


class DeleteFeature(DeleteAdminView):
    permission_required = 'delete_feature'

    def get(self, request, pk):
        return self.get_related(pk, Feature, serialize.feature)

    def delete(self, request, pk):
        self.base_delete(request, pk, Feature, serialize.feature)


class DeleteProduct(DeleteAdminView):
    permission_required = 'delete_product'

    def get(self, request, pk):
        return self.get_related(pk, Product, serialize.product)

    def delete(self, request, pk):
        self.base_delete(request, pk, Product, serialize.product)


class DeleteStorage(DeleteAdminView):
    permission_required = 'delete_storage'

    def get(self, request, pk):
        return self.get_related(pk, Storage, serialize.storage)

    def delete(self, request, pk):
        self.base_delete(request, pk, Storage, serialize.storage)


class DeleteMenu(DeleteAdminView):
    permission_required = 'delete_menu'

    def get(self, request, pk):
        return self.get_related(pk, Menu, serialize.menu)

    def delete(self, request, pk):
        self.base_delete(request, pk, Menu, serialize.menu)


class DeleteTag(DeleteAdminView):
    permission_required = 'delete_tag'

    def get(self, request, pk):
        return self.get_related(pk, Tag, serialize.tag)

    def delete(self, request, pk):
        self.base_delete(request, pk, Tag, serialize.tag)


class DeleteSpecialOffer(DeleteAdminView):
    permission_required = 'delete_specialoffer'

    def get(self, request, pk):
        return self.get_related(pk, SpecialOffer, serialize.special_offer)

    def delete(self, request, pk):
        self.base_delete(request, pk, SpecialOffer, serialize.special_offer)


class DeleteSpecialProducts(DeleteAdminView):
    permission_required = 'delete_specialproducts'

    def get(self, request, pk):
        return self.get_related(pk, SpecialProducts, serialize.special_product)

    def delete(self, request, pk):
        self.base_delete(request, pk, SpecialProducts, serialize.special_product)


class DeleteBlog(DeleteAdminView):
    permission_required = 'delete_blog'

    def get(self, request, pk):
        return self.get_related(pk, Blog, serialize.blog)

    def delete(self, request, pk):
        self.base_delete(request, pk, Blog, serialize.blog)


class DeleteBlogPost(DeleteAdminView):
    permission_required = 'delete_blogpost'

    def get(self, request, pk):
        return self.get_related(pk, BlogPost, serialize.blog_post)

    def delete(self, request, pk):
        self.base_delete(request, pk, BlogPost, serialize.blog_post)


class DeleteTourism(DeleteAdminView):
    permission_required = 'delete_tourism'

    def get(self, request, pk):
        return self.get_related(pk, Tourism, serialize.tourism)

    def delete(self, request, pk):
        self.base_delete(request, pk, Tourism, serialize.tourism)
