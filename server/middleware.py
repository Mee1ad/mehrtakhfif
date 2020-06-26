from mehr_takhfif.settings import TOKEN_SALT, ADMIN, DEFAULT_COOKIE_DOMAIN, HA_ACCOUNTANTS, MT_ACCOUNTANTS
from server.utils import default_step, default_page, res_code, set_csrf_cookie, check_csrf_token, \
    get_custom_signed_cookie, \
    set_custom_signed_cookie
from server.models import User, Basket
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseNotFound
import json
from django.urls import resolve
import time
import pysnooper
from django.contrib.auth import login
from sentry_sdk import configure_scope
from server.decorators import try_except


class AuthMiddleware:
    def __init__(self, get_response):
        super().__init__()
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # print(request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR'))
        path = request.path_info
        route = resolve(path).route
        app_name = resolve(path).app_name
        token_requests = ['POST', 'PUT', 'PATCH']
        allow_without_token = ['login', 'activate', 'resend_code', 'reset_password', 'privacy_policy', 'test']
        if request.method in token_requests and route not in allow_without_token and app_name != 'admin':
            # check_csrf_token(request)
            pass
        # Debug
        if ADMIN:
            request.user = User.objects.order_by('id').first()
            # request.user = User.objects.get(pk=133)
        if HA_ACCOUNTANTS:
            request.user = User.objects.get(pk=3)
        if MT_ACCOUNTANTS:
            request.user = User.objects.get(pk=4)
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
        request.all = request.GET.get('all', False)
        try:
            request.lang = request.headers['language']
        except Exception:
            request.lang = 'fa'

        request.schema_params = {'language': request.lang, 'user': request.user}

        if app_name == 'server':
            request.params = {}
            # sync user basket count
            new_basket_count = None
            if request.user.is_authenticated:
                basket = Basket.objects.filter(user=request.user).order_by('-id')
                if basket.exists():
                    db_basket_count = basket.first().products.all().count()
                    user_basket_count = get_custom_signed_cookie(request, 'basket_count', -1)
                    # new_basket_count = int(user_basket_count)
                    if not db_basket_count == int(user_basket_count):
                        new_basket_count = db_basket_count
                    request.basket = basket
                else:
                    new_basket_count = 0

        elif app_name == 'mtadmin':
            request.token = request.headers.get('access-token', None)

            if not request.user.is_staff:
                # todo debug
                pass
                # raise PermissionDenied
        elif app_name == 'admin':
            if request.user.is_superuser is False:
                return HttpResponseNotFound()
        # set new basket count in cookie
        with configure_scope() as scope:
            user = request.user
            if user.is_authenticated:
                scope.user = {"email": user.email, 'first_name': user.first_name, 'last_name': user.last_name}

        response = self.get_response(request)
        if app_name == 'server' and new_basket_count is not None and 200 <= response.status_code <= 299 and request.method == 'GET':
            response = set_custom_signed_cookie(response, 'basket_count', new_basket_count)
        if request.method in token_requests and app_name != 'admin':
            # return set_csrf_cookie(response)
            pass
        return response
