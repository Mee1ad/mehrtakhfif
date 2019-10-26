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
    def get(self, request, pk):
        storage = Storage.objects.filter(pk=pk).select_related('product').first()
        feature = storage.product.feature.all()
        related_product = Storage.objects.filter(product__tag__in=storage.product.tag.all())
        lang = request.lang
        return JsonResponse({'storage': StorageSchema(lang).dump(storage),
                             'feature': FeatureSchema(lang).dump(feature, many=True),
                             'related_product': StorageSchema(lang).dump(related_product, many=True)})


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
            return JsonResponse(self.response['ok'], status=201)
        except Exception:
            return JsonResponse(self.response['bad'], status=400)

    def delete(self, request):
        pk = request.GET.get('id', None)
        Comment.objects.filter(pk=pk, user=request.user).delete()
        return JsonResponse(self.response['ok'])
