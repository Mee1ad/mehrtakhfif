import time

from django.http import JsonResponse, HttpResponseNotFound
from django.urls import resolve
from sentry_sdk import configure_scope

from mehr_takhfif.settings import ROLL_NAME, HOST, MAINTENANCE
from server.models import User, Basket
from server.utils import default_step, admin_default_step, default_page, get_custom_signed_cookie,\
    set_custom_signed_cookie, get_basket_count, res_code


class AuthMiddleware:
    def __init__(self, get_response):
        super().__init__()
        self.get_response = get_response
        # One-time configuration and initialization.

    def get_user(self, roll_name):
        pk = {'admin': 1, 'post': 10, 'accountants': 4}
        return User.objects.get(pk=pk[roll_name])

    def attach_pagination(self, request, application):
        ds = {'server': default_step, 'mtadmin': admin_default_step}[application]
        try:
            request.step = int(request.GET.get('s', ds))
            request.page = int(request.GET.get('p', default_page))
            request.all = request.GET.get('all', False)
        except ValueError:
            pass
        return request

    def __call__(self, request):
        if MAINTENANCE:
            return JsonResponse({}, status=res_code['maintenance_mode'])
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
            request.lang = request.headers['language']
        except Exception:
            request.lang = 'fa'
        # prefetch user attr per route: filter: vip_types, default: basket,
        # try:  # temp
        #     request.user = User.objects.filter(pk=request.user.pk).prefetch_related('vip_types').first()
        # except Exception:
        #     pass
        request.schema_params = {'language': request.lang, 'user': request.user}
        if app_name == 'server':
            request = self.attach_pagination(request, 'server')
            request.params = {}
            # sync user basket count

        # else:
        #     new_basket_count = 0

        elif app_name == 'mtadmin':
            request = self.attach_pagination(request, 'mtadmin')
            request.token = request.headers.get('access-token', None)
            try:
                request.allowed_categories_id = list(request.user.category_permissions.all().values_list('id',
                                                                                                         flat=True))
            except AttributeError:
                request.allowed_categories_id = []
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
        if request.method in token_requests and app_name != 'admin':
            # return set_csrf_cookie(response)
            pass
        return response
