import time

from django.http import JsonResponse, HttpResponseNotFound
from django.urls import resolve
from sentry_sdk import configure_scope

from mehr_takhfif.settings import ROLL_NAME, HOST
from server.models import User, Basket
from server.utils import default_step, default_page, get_custom_signed_cookie, set_custom_signed_cookie


class AuthMiddleware:
    def __init__(self, get_response):
        super().__init__()
        self.get_response = get_response
        # One-time configuration and initialization.

    def get_user(self, roll_name):
        pk = {'admin': 1, 'post': 10, 'accountants': 4}
        return User.objects.get(pk=pk[roll_name])

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
        if HOST == 'http://api.mt.com':
            request.user = self.get_user(ROLL_NAME)
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
        try:
            request.step = int(request.GET.get('s', default_step))
            request.page = int(request.GET.get('p', default_page))
            request.all = request.GET.get('all', False)
        except ValueError:
            pass
        try:
            request.lang = request.headers['language']
        except Exception:
            request.lang = 'fa'

        request.schema_params = {'language': request.lang, 'user': request.user}

        if app_name == 'server':
            request.params = {}
            # sync user basket count
            new_basket_count = None
            try:
                basket = Basket.objects.filter(user=request.user).order_by('-id')
                db_basket_count = basket.first().products.all().count()
                request.basket = basket.first()
            except TypeError:
                db_basket_count = len(request.session.get('basket', []))
            except AttributeError:
                db_basket_count = 0
            user_basket_count = get_custom_signed_cookie(request, 'basket_count', -1)
            # new_basket_count = int(user_basket_count)
            if not db_basket_count == int(user_basket_count):
                new_basket_count = db_basket_count

        # else:
        #     new_basket_count = 0

        elif app_name == 'mtadmin':
            request.token = request.headers.get('access-token', None)
            try:
                request.allowed_boxes_id = list(request.user.box_permission.all().values_list('id', flat=True))
            except AttributeError:
                request.allowed_boxes_id = []
            if not request.user.is_staff:
                # todo debug
                pass
                # raise PermissionDenied
        elif app_name == 'admin':
            if not request.user.is_superuser and not request.user.groups.filter(name='accountants').exists():
                return HttpResponseNotFound()
        # set new basket count in cookie
        with configure_scope() as scope:
            user = request.user
            if user.is_authenticated:
                scope.user = {"email": user.email, 'first_name': user.first_name, 'last_name': user.last_name}

        response = self.get_response(request)
        is_login = get_custom_signed_cookie(request, 'is_login', error=None)
        if is_login is None:
            response = set_custom_signed_cookie(response, 'is_login', request.user.is_authenticated)
        if app_name == 'server' and new_basket_count is not None and 200 <= response.status_code <= 299 and request.method == 'GET':
            response = set_custom_signed_cookie(response, 'basket_count', new_basket_count)
        if request.method in token_requests and app_name != 'admin':
            # return set_csrf_cookie(response)
            pass
        return response
