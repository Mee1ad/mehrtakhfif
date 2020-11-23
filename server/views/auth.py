import random

from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.backends import ModelBackend
from django.http import JsonResponse
from django.db.models import ProtectedError
from server.utils import *
from server.serialize import UserSchema
import pysnooper
from secrets import token_hex
from mehr_takhfif.settings import DEFAULT_COOKIE_DOMAIN, DEBUG, SAFE_IP, TEST_USER
from django.contrib.sessions.backends.db import SessionStore as OriginalSessionStore
from django.utils.crypto import get_random_string
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from push_notifications.models import APNSDevice, GCMDevice


class Backend(ModelBackend):
    @staticmethod
    def get_user_from_cookie(request):
        try:
            client_token = get_custom_signed_cookie(request, 'token', False)
            return User.objects.get(token=client_token, is_ban=False)
        except Exception:
            return None


class SessionStore(OriginalSessionStore):
    def _get_new_session_key(self):
        while True:
            session_key = get_random_string(40, random_data)
            if not self.exists(session_key):
                break
        return session_key


class Login(View):
    @pysnooper.snoop()
    def post(self, request):
        data = load_data(request, check_token=False)
        cookie_age = 30 * 60
        username = data['username']
        password = data.get('password', None)
        try:  # Login
            user = User.objects.get(username=username)
            is_staff = user.is_staff
            if user.is_ban:
                return JsonResponse({'message': 'user is banned'}, status=res_code['banned'])
            if password is None and not is_staff:  # otp
                if user.privacy_agreement:  # 202 need activation code (login)
                    return set_token(user, self.send_activation(user, request))
                # res = JsonResponse({}, status=251) # please agree privacy policy (signup)
                # return self.set_token(user, res)
                raise User.DoesNotExist  # redirect to signup
            if not user.is_active:  # incomplete signup
                raise User.DoesNotExist  # redirect to signup
            if not user.check_password(password):
                raise ValidationError(_('شماره موبایل یا پسورد نامعتبر است'))
            if is_staff:
                return set_token(user, self.send_activation(user, request))
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            res = {'user': UserSchema().dump(user)}
            basket = Basket.objects.filter(user=user).order_by('-id')
            res['basket_count'] = 0
            if basket.exists():
                res['basket_count'] = basket.first().products.all().count()
            basket_count = res['basket_count']
            res = JsonResponse(res)
            set_custom_signed_cookie(res, 'basket_count', basket_count)
            set_custom_signed_cookie(res, 'is_login', True)
            sync_session_basket(request)
            return res
        except User.DoesNotExist:  # Signup
            try:
                user.set_password(password)
            except UnboundLocalError:
                user = User.objects.create_user(username=username, password=password)
            res = JsonResponse({}, status=res_code['signup_with_pp'])  # please agree privacy policy
            return set_token(user, res)
        except AssertionError:  # invalid password
            return JsonResponse({}, status=res_code['invalid_password'])

    @staticmethod
    def send_activation(user, request=None):
        resend_timeout = 0.5
        activation_expire = 2
        if timezone.now() < add_minutes(resend_timeout - activation_expire, time=user.activation_expire):
            raise PermissionDenied
        user.activation_code = random.randint(10000, 99999)
        user.activation_expire = add_minutes(activation_expire)
        user.save()
        ip = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR')
        res = {'resend_timeout': resend_timeout, 'timeout': activation_expire, 'code': user.activation_code}
        if not (DEBUG or (ip in SAFE_IP and user.username == TEST_USER)):
            send_sms(user.username, "verify", user.activation_code)
            res = {'resend_timeout': resend_timeout, 'timeout': activation_expire}
        return JsonResponse(res, status=res_code['updated'])

    @staticmethod
    def check_password(user):
        return user.password[:6] == 'argon2'


class PrivacyPolicy(View):
    def put(self, request):
        try:
            user = Backend.get_user_from_cookie(request)
            user.privacy_agreement = True
            user.save()
            return Login.send_activation(user, request)  # need activation code
        except Exception:
            return JsonResponse({}, status=res_code['unauthorized'])

    @staticmethod
    def get_user(request):
        client_token = get_custom_signed_cookie(request, 'token', False)
        return User.objects.get(token=client_token)


class SetPassword(View):
    @pysnooper.snoop()
    def put(self, request):
        try:
            user = Backend.get_user_from_cookie(request)
            data = json.loads(request.body)
            user.set_password(data['password'])
            user.save()
            return JsonResponse({'user': UserSchema().dump(user)})
        except Exception:
            return JsonResponse({}, status=res_code['bad_request'])


class ResendCode(View):
    def post(self, request):
        try:
            user = Backend.get_user_from_cookie(request)
            res = Login.send_activation(user, request)
            res.status_code = 204
            return res
        except Exception:
            return JsonResponse({'message': 'token not found'}, status=res_code['bad_request'])


class Activate(View):
    def post(self, request):
        data = load_data(request)
        # TODO: get csrf code
        try:
            client_token = get_custom_signed_cookie(request, 'token', False)
            code = data['code']
            user = User.objects.get(activation_code=code, token=client_token, is_ban=False,
                                    activation_expire__gte=timezone.now())
            user.activation_expire = timezone.now()
            user.is_active = True
            user.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            res = {'user': UserSchema().dump(user)}  # signup without password
            if user.is_staff:
                res['user']['is_staff'] = user.is_staff
            basket = Basket.objects.filter(user=user).order_by('-id')
            res['basket_count'] = 0
            if basket.exists():
                res['basket_count'] = basket.first().products.all().count()
            if data.get('new_password'):
                user.set_password(data['new_password'])
                user.save()
            response = JsonResponse(res, status=res_code['signup_with_pass'])
            if Login.check_password(user):
                response = JsonResponse(res)  # successful login
                set_custom_signed_cookie(response, 'basket_count', res['basket_count'])
                set_custom_signed_cookie(response, 'is_login', True)
                response.delete_cookie('token')
                sync_session_basket(request)
            return response
        except Exception:
            return JsonResponse({'message': 'code not found'}, status=res_code['unauthorized'])


class LogoutView(View):
    def post(self, request):
        try:
            logout(request)
            res = JsonResponse({})
            res.delete_cookie('basket_count', domain=DEFAULT_COOKIE_DOMAIN)
            set_custom_signed_cookie(res, 'is_login', False)
            return res
        except Exception:
            return JsonResponse({}, status=res_code['forbidden'])


class AddDevice(View):
    def post(self, request):
        data = load_data(request, check_token=False)
        client = Client.objects.filter(device_id=data['device_id'])
        if client.exists():
            GCMDevice.objects.filter(client=client.first()).update(registration_id=data['token'],
                                                                   name=request.user_agent.device.family)
            return JsonResponse({})
        if request.user.is_anonymous:
            request.user = None
        gcm_device = GCMDevice.objects.create(registration_id=data['token'], cloud_message_type="FCM", active=True,
                                              name=request.user_agent.device.family, user=request.user)
        Client.objects.create(device_id=data['device_id'], user_agent=request.user_agent, gcm_device=gcm_device)
        return JsonResponse({})
