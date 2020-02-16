from mehr_takhfif.settings import TOKEN_SALT, ADMIN
from server.utils import default_step, default_page, res_code
from mtadmin.utils import get_roll
from server.models import User, Basket
from django.http import JsonResponse, HttpResponseNotFound
import json
from django.urls import resolve
import time
from server.error import AuthError


class AuthMiddleware:
    def __init__(self, get_response):
        super().__init__()
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        path = request.path_info
        route = resolve(path).route
        app_name = resolve(path).app_name

        # Debug
        if ADMIN:
            request.user = User.objects.get(pk=1)
        if route == 'favicon.ico':
            return JsonResponse({})
        delay = request.GET.get('delay', None)
        if delay:
            print(delay)
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
        if app_name == 'server':
            request.params = {}
            try:
                request.lang = request.headers['language']
            except Exception:
                request.lang = 'fa'

            # sync user basket count
            new_basket_count = None
            if request.user.is_authenticated:
                db_basket_count = None
                try:
                    basket = Basket.objects.filter(user=request.user, active=True)
                    if basket.exists():
                        db_basket_count = basket.first().products.all().count()
                        user_basket_count = request.get_signed_cookie('basket_count', False, salt=TOKEN_SALT)
                        assert db_basket_count == int(user_basket_count)
                        request.basket = basket
                except AssertionError:
                    new_basket_count = db_basket_count
        elif app_name == 'mtadmin':
            request.token = request.headers.get('access-token', None)
            try:
                get_roll(request.user)
            except AuthError:
                return JsonResponse({}, status=res_code['unauthorized'])

        # set new basket count in cookie
        response = self.get_response(request)
        if app_name == 'server' and new_basket_count and 200 <= response.status_code <= 299:
            res = json.loads(response.content)
            res['new_basket_count'] = new_basket_count
            response.content = json.dumps(res)
            response.set_signed_cookie('basket_count', new_basket_count, salt=TOKEN_SALT)
        return response
