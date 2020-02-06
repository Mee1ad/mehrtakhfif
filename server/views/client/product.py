from django.http import JsonResponse
from server.models import *
from server.serialize import *
from server.utils import View, get_pagination, load_data


class ProductView(View):
    def get(self, request, permalink):
        lang = request.lang
        user = request.user
        product = Product.objects.filter(permalink=permalink).prefetch_related(*Product.prefetch).first()
        if product is None:
            return JsonResponse({}, status=404)
        storages = product.storage_set.filter(start_time__lte=timezone.now())
        product = ProductSchema(lang).dump(product)
        product['category'] = self.get_category(product['category'])
        product['storages'] = StorageSchema(lang).dump(storages, many=True)
        purchased = False
        if user.is_authenticated:
            purchased = self.purchase_status(user, storages)
        return JsonResponse({'product': product, 'purchased': purchased})

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
        return True if Invoice.objects.filter(user=user, status='payed', storages__in=storages).exists() else False


class RelatedProduct(View):
    def get(self, request, permalink):
        product = Product.objects.get(permalink=permalink)
        tags = product.tag.all()
        products = Product.objects.filter(tag__in=tags).order_by('-id').distinct('id')
        return JsonResponse(get_pagination(products, request.step, request.page, MinProductSchema))


class CommentView(View):
    def get(self, request):
        product_id = request.GET.get('product_id', None)
        post_id = request.GET.get('post_id', None)
        comment_id = request.GET.get('comment_id', None)
        comment_type = request.GET.get('type', None)
        if comment_id:
            comments = Comment.objects.filter(reply_to_id=comment_id)
            return JsonResponse(get_pagination(comments, request.step, request.page, CommentSchema))
        filterby = {"product_id": product_id} if product_id else {"blog_post_id": post_id}
        filterby = {"type": comment_type, **filterby}
        comments = Comment.objects.filter(**filterby, approved=True).exclude(reply_to__isnull=False)
        return JsonResponse(get_pagination(comments, request.step, request.page, CommentSchema))

    def post(self, request):
        data = load_data(request)
        reply_to_id = data.get('reply_to_id', None)
        rate = data.get('rate', None)
        satisfied = data.get('satisfied', None)
        cm_type = data['type']
        product_id = data.get('product_id')
        blog_post_id = data.get('blog_post_id')
        post = {"product_id": product_id} if product_id else {"blog_post_id": blog_post_id}
        if reply_to_id:
            assert Comment.objects.filter(pk=reply_to_id).exists()
        Comment.objects.create(text=data['text'], user=request.user, reply_to_id=reply_to_id, type=cm_type,
                               rate=rate, satisfied=satisfied, **post)
        return JsonResponse({}, status=201)

    def delete(self, request):
        pk = request.GET.get('id', None)
        Comment.objects.filter(pk=pk, user=request.user).delete()
        return JsonResponse({})
