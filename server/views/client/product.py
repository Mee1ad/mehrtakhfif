import json

from django.http import JsonResponse

from server.models import *
from server.serialize import *
from server.views.utils import View, default_page, default_step
import pysnooper


class Single(View):
    @pysnooper.snoop()
    def get(self, request, permalink):
        lang = request.lang
        user = request.user
        try:
            product = Product.objects.filter(permalink=permalink).prefetch_related(*Product.prefetch).first()
            tags = product.tag.all()
            storages = Storage.objects.filter(product=product)
            product = ProductSchema(lang).dump(product)
            product['category'] = self.get_category(product['category'])
            product['storages'] = StorageSchema(lang).dump(storages, many=True)
            purchased = False
            if user.is_authenticated:
                purchased = self.purchase_status(user, storages)
            related_products = Product.objects.filter(tag__in=tags)[:5]
            related_products = MinProductSchema(lang).dump(related_products, many=True)
            return JsonResponse({'product': product, 'related_products': related_products, 'purchased': purchased})
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

    def purchase_status(self, user, storages):
        invoices = Invoice.objects.filter(user=user, status='payed').select_related(*Invoice.select)
        for invoice in invoices:
            purchased = BasketProduct.objects.filter(basket=invoice.basket, storage__in=storages)
            if purchased:
                return True
        return False


class RelatedProduct(View):
    def get(self, request, permalink):
        step = int(request.GET.get('s', default_step))
        page = int(request.GET.get('e', default_page))
        product = Product.objects.get(permalink=permalink)
        tags = product.tag.all()
        products = Product.objects.exclude(permalink=permalink).filter(tag__in=tags)[(page - 1) * step:step * page]
        return JsonResponse({'products': MinProductSchema().dump(products, many=True)})


class CommentView(View):
    def get(self, request):
        product_id = request.GET.get('product_id', None)
        blog_id = request.GET.get('blog_id', None)
        comment_type = request.GET.get('type', None)
        if product_id:
            comments = Comment.objects.filter(product_id=product_id, type=comment_type).order_by('-created_at')
            return JsonResponse({'comments': CommentSchema().dump(comments, many=True)})
        if blog_id:
            comments = Comment.objects.filter(blog_post_id=blog_id, type=comment_type).order_by('-created_at')
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
