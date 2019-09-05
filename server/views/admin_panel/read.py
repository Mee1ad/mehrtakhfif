from django.views import View
from server.models import *
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server import serializer as serialize
from server.views.mylib import Tools


class ReadAdminView(Tools):

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


class GetCategory(PermissionRequiredMixin, ReadAdminView):
    permission_required = 'server.view_category'

    def get(self, request):
        return self.get_data(request, Category, serialize.category)


class GetAddress(ReadAdminView):
    permission_required = 'read_address'

    def get(self, request):
        return self.get_data(request, Address, serialize.address)


class GetFeature(ReadAdminView):
    permission_required = 'read_feature'

    def get(self, request):
        return self.get_data(request, Feature, serialize.feature)


class GetProduct(ReadAdminView):
    permission_required = 'read_product'

    def get(self, request):
        return self.get_data(request, Product, serialize.product)


class GetStorage(ReadAdminView):
    permission_required = 'read_storage'

    def get(self, request):
        return self.get_data(request, Storage, serialize.storage)


class GetMenu(ReadAdminView):
    permission_required = 'read_menu'

    def get(self, request):
        return self.get_data(request, Menu, serialize.menu)


class GetTag(ReadAdminView):
    permission_required = 'read_tag'

    def get(self, request):
        return self.get_data(request, Tag, serialize.tag)


class GetSpecialOffer(ReadAdminView):
    permission_required = 'read_specialoffer'

    def get(self, request):
        return self.get_data(request, SpecialOffer, serialize.special_offer)


class GetSpecialProducts(ReadAdminView):
    permission_required = 'read_specialproducts'

    def get(self, request):
        return self.get_data(request, SpecialProducts, serialize.special_product)


class GetBlog(ReadAdminView):
    permission_required = 'read_blog'

    def get(self, request):
        return self.get_data(request, Blog, serialize.blog)


class GetBlogPost(ReadAdminView):
    permission_required = 'read_blogpost'

    def get(self, request):
        return self.get_data(request, BlogPost, serialize.blog_post)


class GetTourism(ReadAdminView):
    permission_required = 'read_tourism'

    def get(self, request):
        return self.get_data(request, Tourism, serialize.tourism)
