from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server.views.utils import View, get_categories
from server.views.admin_panel.read import ReadAdminView
import json
import time
import pysnooper
from django.views.decorators.cache import cache_page
from django.db.models import Max, Min
from server.serialize import *


class Single(View):
    def get(self, request, permalink):
        lang = request.lang
        try:
            product = Product.objects.filter(permalink=permalink).first()
            features = product.feature.all()
            tags = product.tag.all()
            storages = Storage.objects.filter(product=product)
            product = ProductSchema(lang).dump(product)
            product['category'] = self.get_category(product['category'])
            product['storages'] = StorageSchema(lang).dump(storages, many=True)
            product['features'] = FeatureSchema(lang).dump(features, many=True)
            related_products = Product.objects.filter(tag__in=tags)[:5]
            related_products = MinProductSchema(lang).dump(related_products, many=True)
            return JsonResponse({'product': product, 'related_products': related_products})
        except Product.DoesNotExist:
            return JsonResponse({}, status=404)

    def get_category(self, category):
        try:
            category['parent']['child'] = category
            if category['parent'] is not None:
                category['parent']['child']['parent_id'] = category['parent']['id']
            category = category['parent']
            del category['child']['parent']
            return self.get_category(category)
        except TypeError:
            category['parent_id'] = None
            del category['parent']
            return category


class CommentView(View):
    def get(self, request):
        product_id = request.GET.get('product_id', None)
        blog_id = request.GET.get('blog_id', None)
        if product_id:
            comments = Comment.objects.filter(product_id=product_id).order_by('-created_at')
            return JsonResponse({'comments': CommentSchema().dump(comments, many=True)})
        if blog_id:
            comments = Comment.objects.filter(blog_post_id=blog_id).order_by('-created_at')
            return JsonResponse({'comments': CommentSchema().dump(comments, many=True)})
        comments = Comment.objects.filter(user=request.user).order_by('-created_at')
        return JsonResponse({'comments': CommentSchema().dump(comments, many=True)})

    def post(self, request):
        data = json.loads(request.body)
        try:
            if data['reply']:
                comment = Comment.objects.filter(pk=data['reply']).first()
                assert not comment.reply
            Comment(text=data['text'], user=request.user, reply_id=data['reply'], type=data['type'],
                    product_id=data['product_id']).save()
            return JsonResponse({}, status=201)
        except Exception:
            return JsonResponse({}, status=400)

    def delete(self, request):
        pk = request.GET.get('id', None)
        Comment.objects.filter(pk=pk, user=request.user).delete()
        return JsonResponse({})
