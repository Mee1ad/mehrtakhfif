from server.models import *
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from server import serializer as serialize
from server.views.mylib import Tools
from server.views.admin_panel.read import ReadAdminView
import json
import time
from django.views.decorators.cache import cache_page


class Home(Tools):
    def get(self, request):
        # time.sleep(2)
        try:
            language = request.headers['language']
        except Exception:
            language = 'persian'
        slider = Slider.objects.select_related('media').all()
        special_offer = SpecialOffer.objects.select_related('media').all()
        special_product = SpecialProduct.objects.select_related('storage', 'storage__product', 'media').all()
        best_sell_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
            default=True).order_by('-product__sold_count')[:5]
        special_products = {}
        best_seller = {}
        all_box = Box.objects.all()
        for box, index in zip(all_box, range(len(all_box))):
            box_special_product = SpecialProduct.objects.select_related('storage', 'media').filter(
                box=box).order_by('-created_by')[:self.end]
            special_products['id'] = box.pk
            special_products['name'] = box.name[language]
            special_products['items'] = (serialize.special_product(box_special_product))
            best_seller_storage = Storage.objects.select_related('product', 'product__thumbnail').filter(
                default=True).order_by('-product__sold_count')[:5]
            best_seller['id'] = box.pk
            best_seller['name'] = box.name[language]
            best_seller['items'] = serialize.storage(best_seller_storage)
        res = {'slider': serialize.slider(slider, True), 'special_offer': serialize.special_offer(special_offer, True),
               'box_special_product': special_products, 'best_sell_product': serialize.storage(best_sell_storage, True),
               'best_seller': best_seller, 'special_product': serialize.special_product(special_product, True)}
        return JsonResponse(res)


class GetMenu(Tools):
    def get(self, request):
        return serialize.menu(Menu.objects.select_related('media', 'parent').all())


class BoxView(Tools):
    def get(self, request, pk):
        box = Box.objects.filter(pk=pk).first()
        categories = Category.objects.select_related('media', 'parent').filter(
            box_id=pk, deactive=False).order_by('-priority')
        latest = Storage.objects.filter(box_id=pk).select_related(
            'product', 'product__thumbnail').order_by('-updated_by')[:self.end]
        best_seller = Storage.objects.select_related('product', 'product__thumbnail').filter(
            box_id=pk).order_by('-product__sold_count')[:5]
        special_offer = SpecialOffer.objects.filter(box_id=pk).select_related('media')
        special_product = SpecialProduct.objects.filter(box_id=pk).select_related('storage', 'storage__product', 'media')
        return JsonResponse({'box': serialize.box(box), 'categories': serialize.category(categories),
                             'latest': serialize.storage(latest), 'best_seller': serialize.storage(best_seller),
                             'special_offer': serialize.special_offer(special_offer, True),
                             'special_product': serialize.special_product(special_product)})


class CategoryView(Tools):
    def get(self, request, pk):
        start = int(request.GET.get('s', self.start))
        end = int(request.GET.get('e', self.end))
        storage = Storage.objects.filter(category_id=pk).select_related(
                'product', 'product__thumbnail').order_by('-updated_at')[start:end]
        special_products = serialize.special_product(
            SpecialProduct.objects.filter(category_id=pk).select_related('product'))
        return JsonResponse({'products': serialize.storage(storage, True),
                             'special_products': serialize.special_product(special_products, True)})


class Single(Tools):
    def get(self, request, pk):
        storage = Storage.objects.filter(pk=pk).select_related('product').first()
        feature = storage.product.feature.all()
        # related_product
        res = {'storage': serialize.storage(storage), 'feature': serialize.feature(feature)}
        return JsonResponse(res)


class TagView(Tools):
    def get(self, request, pk):
        start = int(request.GET.get('s', self.start))
        end = int(request.GET.get('e', self.end))
        tag = Tag.objects.filter(pk=pk).first()
        products = tag.product.all()[start:end]
        return JsonResponse({'products': serialize.product(products)})


class Profile(Tools):
    def get(self, request):
        return JsonResponse({'user': serialize.user(request.user)})

    def put(self, request):
        data = json.loads(request.body)
        request.user.update(first_name=data['first_name'], last_name=data['last_name'], gender=data['gender'],
                            language=data['language'], email=data['email'], meli_code=data['meli_code'])
        return HttpResponse('ok', status=200)


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


class AddressView(Tools):
    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        return JsonResponse({'addresses': addresses})

    def post(self, request):
        data = json.loads(request.body)
        Address(province=data['province'], city=data['city'], postal_code=data['postal_code'],
                address=data['address'], location=data['location'], user=request.user)

    def delete(self, request):
        address_id = request.GET.get('address_id', None)
        address = Comment.objects.filter(pk=address_id, user=request.user).first()
        address.delete()
        return HttpResponse('ok')


class WishlistView(Tools):
    def get(self, request):
        wishlists = WishList.objects.filter(user_id=request.user)
        return JsonResponse({'wishlists': serialize.wishlist(wishlists)})

    def post(self, request):
        data = json.loads(request.body)
        WishList(type=data['type'], notify=data['notify'], product_id=data['product_id'], user_id=request.user,
                 created_by=request.user, updated_by=request.user).save()
        return HttpResponse(status=201)

    def delete(self, request):
        product_id = request.GET.get('product_id', None)
        address = WishList.objects.filter(pk=product_id, user_id=request.user).first()
        address.delete()
        return HttpResponse('ok')


class NotifyView(Tools):
    def get(self, request):
        notify = WishList.objects.filter(user_id=request.user)
        return JsonResponse({'wishlists': serialize.notify(notify)})

    def post(self, request):
        data = json.loads(request.body)
        NotifyUser(type=data['type'], notify=data['notify'], product_id=data['product_id'], user_id=request.user).save()
        return HttpResponse(status=201)

    def delete(self, request):
        notify_id = request.GET.get('product_id', None)
        address = WishList.objects.filter(pk=notify_id, user_id=request.user).first()
        address.delete()
        return HttpResponse('ok')


class Buy(Tools):
    def get(self, request):
        basket = Basket.objects.filter(user=request.user)
        return JsonResponse({'basket': serialize.basket(basket)})

    def post(self, request):
        data = json.loads(request.body)
        basket = Basket(user_id=request.user, count=data['count'], description=data['description'],
                        created_by_id=request.user, updated_by_id=request.user, product=data['product'])
        basket.save()
        return JsonResponse({'basket_id': basket.pk})

    def put(self, request):
        data = json.loads(request.body)
        basket = Basket.objects.get(pk=data['basket_id'])
        product = Storage.objects.filter(pk=data['product_id'])
        basket.product.add(product)
        return HttpResponse('ok')


class MyTransactions(Tools):
    def get(self, request):
        pass


class WalletView(Tools):
    def get(self, request):
        pass


class BlogView(Tools):
    def get(self, request):
        pass


class Search(Tools):
    def get(self, request):
        pass
