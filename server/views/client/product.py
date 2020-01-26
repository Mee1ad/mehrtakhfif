import json

from django.http import JsonResponse

from server.models import *
from server.serialize import *
from server.views.utils import View, default_page, default_step, get_pagination


class Single(View):

    def get(self, request, permalink):
        lang = request.lang
        user = request.user
        try:
            product = Product.objects.filter(permalink=permalink).prefetch_related(*Product.prefetch).first()
            if product is None:
                return JsonResponse({}, status=404)
            storages = Storage.objects.filter(product=product)
            product = ProductSchema(lang).dump(product)
            product['category'] = self.get_category(product['category'])
            product['storages'] = StorageSchema(lang).dump(storages, many=True)
            purchased = False
            if user.is_authenticated:
                purchased = self.purchase_status(user, storages)
            return JsonResponse({'product': product, 'purchased': purchased})
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
        product = Product.objects.get(permalink=permalink)
        tags = product.tag.all()
        products = Product.objects.filter(tag__in=tags).order_by('-id').distinct('id')
        return JsonResponse(get_pagination(products, request.step, request.page, MinProductSchema))


class CommentView(View):
    def get(self, request):
        product_id = request.GET.get('product_id', None)
        blog_id = request.GET.get('blog_id', None)
        comment_type = request.GET.get('type', None)
        filterby = {"product_id": product_id} if product_id else {"blog_id": blog_id}
        filterby = {"type": comment_type, **filterby}
        comments = Comment.objects.filter(**filterby, approved=True)
        return JsonResponse(get_pagination(comments, request.step, request.page, CommentSchema))

    def post(self, request):
        data = json.loads(request.body)
        reply_id = data.get('reply_id', None)
        rate = data.get('rate', None)
        if reply_id:
            assert Comment.objects.filter(pk=reply_id).exists()
        Comment.objects.create(text=data['text'], user=request.user, reply_id=reply_id, type=data['type'],
                               product_id=data['product_id'], rate=rate)
        return JsonResponse({}, status=201)

    def delete(self, request):
        pk = request.GET.get('id', None)
        Comment.objects.filter(pk=pk, user=request.user).delete()
        return JsonResponse({})
