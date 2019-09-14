from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server import serializer as serialize
from server.views.mylib import Tools
from server.views.admin_panel.read import ReadAdminView
import json
import time
import pysnooper
from django.views.decorators.cache import cache_page
from django.db.models import Max, Min
from server.serialize import *


class Single(Tools):
    def get(self, request, pk):
        storage = Storage.objects.filter(pk=pk).select_related('product').first()
        feature = storage.product.feature.all()
        related_product = Storage.objects.filter(product__tag__in=storage.product.tag.all())
        return JsonResponse({'storage': serialize.storage(storage), 'feature': serialize.feature(feature),
                             'related_product': serialize.storage(related_product)})


class CommentView(Tools):
    def get(self, request):
        product_id = request.GET.get('product_id', None)
        blog_id = request.GET.get('blog_id', None)
        if product_id:
            comments = Comment.objects.filter(product_id=product_id).order_by('-created_at')
            return JsonResponse({'comments': serialize.comment(comments)})
        if blog_id:
            comments = Comment.objects.filter(blog_post_id=blog_id).order_by('-created_at')
            return JsonResponse({'comments': serialize.comment(comments)})
        comments = Comment.objects.filter(user=request.user).order_by('-created_at')
        return JsonResponse({'comments': serialize.comment(comments)})

    def post(self, request):
        data = json.loads(request.body)
        Comment(text=data['text'], user=request.user, reply=data['reply'], type=data['type'],
                product_id=data['product_id']).save()
        return HttpResponse(status=201)

    def delete(self, request):
        comment_id = request.GET.get('comment_id', None)
        comment = Comment.objects.filter(pk=comment_id, user=request.user).first()
        comment.delete()
        return HttpResponse('ok')