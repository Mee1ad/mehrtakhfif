from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.db.models import Count, Q
from django.utils.functional import SimpleLazyObject

from server.utils import get_custom_signed_cookie
from .models import User
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, _get_user_session_key, load_backend,\
    constant_time_compare
from django.urls import resolve

UserModel = get_user_model()


class MyModelBackend(ModelBackend):
    @staticmethod
    def get_user1(request):
        if not hasattr(request, '_cached_user'):
            request._cached_user = MyModelBackend.get_user2(request)
        return request._cached_user

    @staticmethod
    def get_user2(request):
        """
        Return the user model instance associated with the given request session.
        If no user is retrieved, return an instance of `AnonymousUser`.
        """
        user = None
        try:
            user_id = _get_user_session_key(request)
            backend_path = request.session[BACKEND_SESSION_KEY]
        except KeyError:
            pass
        else:
            if backend_path in settings.AUTHENTICATION_BACKENDS:
                backend = load_backend(backend_path)
                user = backend.get_user3(user_id, request)
                # Verify the session
                if hasattr(user, 'get_session_auth_hash'):
                    session_hash = request.session.get(HASH_SESSION_KEY)
                    session_hash_verified = session_hash and constant_time_compare(
                        session_hash,
                        user.get_session_auth_hash()
                    )
                    if not session_hash_verified:
                        request.session.flush()
                        user = None

        return user or AnonymousUser()

    def what_to_prefetch(self, request):
        route = resolve(request.path_info).route
        data = {'test': {'select': [], 'prefetch': []},
                'profile': {'select': ['default_address__city', 'default_address__state'], 'prefetch': ['vip_types']}}
        data.update(dict.fromkeys(['product/<str:permalink>'], {'select': [], 'prefetch': ['vip_types']}))
        return data.get(route, {'select': [], 'prefetch': []})

    def get_user3(self, user_id, request):
        prefetch = self.what_to_prefetch(request)
        try:
            # user = UserModel._default_manager.get(pk=user_id)
            user = User.objects.filter(pk=user_id).select_related(*prefetch['select'])\
                .prefetch_related(*prefetch['prefetch']).\
                annotate(basket_count=Count('baskets__products', filter=Q(baskets__sync=0))).first()
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None

    @staticmethod
    def get_user_from_cookie(request):
        try:
            client_token = get_custom_signed_cookie(request, 'token', False)
            return User.objects.get(token=client_token, is_ban=False)
        except Exception:
            return None


class MyAuthenticationMiddleware(AuthenticationMiddleware):
    def process_request(self, request):
        assert hasattr(request, 'session'), (
            "The Django authentication middleware requires session middleware "
            "to be installed. Edit your MIDDLEWARE%s setting to insert "
            "'django.contrib.sessions.middleware.SessionMiddleware' before "
            "'django.contrib.auth.middleware.AuthenticationMiddleware'."
        ) % ("_CLASSES" if settings.MIDDLEWARE is None else "")
        request.user = SimpleLazyObject(lambda: MyModelBackend.get_user1(request))
