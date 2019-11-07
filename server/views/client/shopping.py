from server.views.utils import *
from django.http import HttpResponse
from django.template.loader import render_to_string
# from weasyprint import HTML
import tempfile


class Buy(View):

    def get(self, request):
        products = BasketProduct.objects.select_related('storage', 'basket').filter(basket__user=request.user)
        basket = BasketSchema(request.lang).dump(products[0].basket)
        basket['products'] = BasketProductSchema(request.lang).dump(products, many=True)
        return JsonResponse({'basket': basket})

    def post(self, request):
        data = json.loads(request.body)
        print(data)
        basket = None
        try:
            assert request.user.is_authenticated
            basket = Basket.objects.get(user=request.user, status=0)
        except Basket.DoesNotExist:
            basket = Basket(user=request.user, created_by=request.user, updated_by=request.user, status=0)
            basket.save()
        except AssertionError:
            return JsonResponse({}, status=401)
        basket_count = self.add_to_basket(basket, data['products'])
        return JsonResponse({'basket_count': basket_count})

    def delete(self, request):
        storage_id = request.GET.get('product_id', None)
        try:
            basket = Basket.objects.get(user=request.user, status=0)
            assert BasketProduct.objects.filter(basket__user=request.user, basket_id=basket.id,
                                                storage_id=storage_id).exists()
            BasketProduct.objects.filter(basket_id=basket.id, storage_id=storage_id).delete()
            return JsonResponse(response['ok'])
        except (AssertionError, Basket.DoesNotExist):
            return JsonResponse(response['bad'], status=400)

    @pysnooper.snoop()
    def add_to_basket(self, basket, products):
        for product in products:
            pk = int(product['id'])
            count = int(product['count'])
            try:
                product = BasketProduct.objects.filter(basket=basket, storage_id=pk). \
                    select_related('storage')
                if product:
                    available_count = product.first().storage.available_count_for_sale
                    assert available_count >= count
                    product.update(count=count)
                    continue
                product = Storage.objects.filter(id=pk)
                if product.exists():
                    BasketProduct(basket=basket, storage_id=pk, count=count).save()
                    continue
            except AssertionError:
                product.update(count=count)
        basket.count = basket.products.all().count()
        basket.save()
        return basket.count

    def get_basket_count(self, basket_id, user):
        basket = Basket.objects.filter(pk=basket_id, user=user, status=0).prefetch_related('product')
        products = basket.product.all()
        count = 0
        for product in products:
            count += product.count
        return count


class ShowCodes(View):
    def get(self, request):
        """Generate pdf."""
        # Model data

        # Rendered
        html_string = render_to_string('test.html', {'people': []})
        html = HTML(string=html_string)
        result = html.write_pdf()

        # Creating http response
        response = HttpResponse(content_type='application/pdf;')
        response['Content-Disposition'] = 'inline; filename=list_people.pdf'
        response['Content-Transfer-Encoding'] = 'binary'
        with tempfile.NamedTemporaryFile(delete=True) as output:
            output.write(result)
            output.flush()
            output = open(output.name, 'r')
            response.write(output.read())

        return response
