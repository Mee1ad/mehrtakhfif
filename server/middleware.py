from mehr_takhfif.settings import TOKEN_SALT, ADMIN, DEFAULT_COOKIE_DOMAIN
from server.utils import default_step, default_page, res_code, set_csrf_cookie, check_csrf_token, set_signed_cookie, \
    get_signed_cookie
from server.models import User, Basket
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseNotFound
import json
from django.urls import resolve
import time
import pysnooper


class AuthMiddleware:
    def __init__(self, get_response):
        super().__init__()
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        path = request.path_info
        route = resolve(path).route
        app_name = resolve(path).app_name
        token_requests = ['POST', 'PUT', 'PATCH']
        allow_without_token = ['login', 'activate', 'resend_code', 'reset_password', 'privacy_policy', 'test']
        if request.method in token_requests and route not in allow_without_token:
            check_csrf_token(request)
            pass
        # Debug
        if ADMIN:
            request.user = User.objects.get(pk=1)
        if route == 'favicon.ico':
            return JsonResponse({})
        delay = request.GET.get('delay', None)
        if delay:
            time.sleep(float(delay))
        error = request.GET.get('error', None)
        if error:
            status_code = request.GET.get('status_code', 501)
            return JsonResponse({}, status=status_code)
        # print(request.headers)
        # print(json.loads(request.body))

        # assign request attributes
        request.step = int(request.GET.get('s', default_step))
        request.page = int(request.GET.get('p', default_page))
        try:
            request.lang = request.headers['language']
        except Exception:
            request.lang = 'fa'
        if app_name == 'server':
            request.params = {}
            # sync user basket count
            new_basket_count = None
            if request.user.is_authenticated:
                db_basket_count = None

                basket = Basket.objects.filter(user=request.user).order_by('-id')
                if basket.exists():
                    db_basket_count = basket.first().products.all().count()
                    user_basket_count = get_signed_cookie(request, 'basket_count', False)
                    if not db_basket_count == int(user_basket_count):
                        new_basket_count = db_basket_count
                    request.basket = basket

        elif app_name == 'mtadmin':
            request.token = request.headers.get('access-token', None)

            if not request.user.is_staff:
                # todo debug
                pass
                # raise PermissionDenied

        # set new basket count in cookie
        response = self.get_response(request)
        if app_name == 'server' and new_basket_count and 200 <= response.status_code <= 299 and request.method == 'GET':
            try:
                res = json.loads(response.content)
                res['new_basket_count'] = new_basket_count
                response.content = json.dumps(res)
                response = set_signed_cookie(response, 'basket_count', new_basket_count)
            except AttributeError:
                pass
        if request.method in token_requests:
            return set_csrf_cookie(response)
        return response
