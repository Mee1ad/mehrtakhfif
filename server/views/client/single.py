from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server.views.utils import View
from server.views.admin_panel.read import ReadAdminView
import json
import time
import pysnooper
from django.views.decorators.cache import cache_page
from django.db.models import Max, Min
from server.serialize import *


class Single(View):
    @pysnooper.snoop()
    def get(self, request, pk):
        lang = request.lang
        storage = Storage.objects.filter(pk=pk).first()
        features = storage.product.feature.all()
        tags = storage.product.tag.all()
        storage = StorageSchema(lang).dump(storage)
        storage['product']['features'] = FeatureSchema(lang).dump(features, many=True)
        related_product = Storage.objects.filter(product__tag__in=tags)
        related_product = StorageSchema(lang).dump(related_product, many=True)
        return JsonResponse({'storage': storage, 'related_product': related_product})


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
