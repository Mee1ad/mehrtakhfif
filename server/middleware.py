from mehr_takhfif.settings import TOKEN_SALT
from server.views.utils import *
from django.http import JsonResponse
import json
from django.urls import resolve
import pysnooper
import time


class AuthMiddleware:

    def __init__(self, get_response):
        super().__init__()
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # print(request.headers)
        # print(json.loads(request.body))
        path = request.path_info
        route = resolve(path).route
        app_name = resolve(path).app_name
        request.user = User.objects.get(pk=1)
        if route == 'favicon.ico':
            return JsonResponse({})
        try:
            if request.headers.get('admin', None) == 'True':
                print('this is admin')
                request.user = User.objects.get(pk=1)
            request.lang = request.headers['language']
        except Exception:
            request.lang = 'persian'
        try:
            request.params = filter_params(request)
        except Exception:
            request.params = {}
        new_basket_count = None
        if request.user.is_authenticated:
            try:
                basket = Basket.objects.filter(user=request.user, active=True)
                if basket.exists():
                    db_basket_count = basket.first().products.all().count()
                    user_basket_count = request.get_signed_cookie('basket_count', False, salt=TOKEN_SALT)
                    assert db_basket_count == int(user_basket_count)
                    request.basket = basket
            except AssertionError:
                new_basket_count = db_basket_count
            except Exception as e:
                print(e)

        try:
            pass
            # app_name = resolve(request.path_info).app_name
            # route = resolve(request.path_info).route
            # if app_name == 'mehrpeyk':
            #     import time
            #     time.sleep(.6)
            #     s = ['mehrpeyk/login', 'mehrpeyk/sign_up', 'mehrpeyk/activate',
            #          'mehrpeyk/resend_activation', 'mehrpeyk/get_location/<str:factor>', 'mehrpeyk/get_locations']
            #     if route not in s:
            #         try:
            #             token = request.headers['Authorization']
            #             first_decrypt = jwt.decode(token[7:-20], token[-20:], algorithms=['HS256'])
            #             second_decrypt = jwt.decode(first_decrypt['data'].encode(), TOKEN_SECRET, algorithms=['HS256'])
            #             request.peyk_id = second_decrypt['user']['id']
            #         except Exception as e:
            #             print(e)
            #             if route != 'mehrpeyk/splash':
            #                 return JsonResponse({'message': f'{e}'}, status=401)
            # if app_name == 'server':
            #     request.user = User.objects.get(pk=1)
            #     try:
            #         token = request.headers['Authorization']
            #         assert User.objects.filter(access_token=token[7:-32]).exists()
            #         counter = str.encode(f"amghezi{request.session.get('counter')}")
            #         counter = hashlib.md5(counter).hexdigest()
            #         assert token == request.user.access_token + counter
            #         request.session['counter'] += 1
            #     except Exception:
            #         print('token issue')
            #         try:
            #             assert request.headers['Postman-Token']
            #         except Exception:
            #             pass
            # return JsonResponse({}, status=401)
            delay = request.GET.get('delay', None)
            # print(request.GET)
            if delay:
                print(delay)
                time.sleep(float(delay))
            error = request.GET.get('error', None)
            if error:
                status_code = request.GET.get('status_code', 501)
                return JsonResponse({}, status=status_code)

        except json.decoder.JSONDecodeError:
            return HttpResponse('')
        response = self.get_response(request)
        if app_name == 'server' and new_basket_count and 200 <= response.status_code <= 299:
            res = json.loads(response.content)
            res['new_basket_count'] = new_basket_count
            response.content = json.dumps(res)
            response.set_signed_cookie('basket_count', new_basket_count, salt=TOKEN_SALT)
        return response
