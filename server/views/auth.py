import random
import traceback

from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.sessions.backends.db import SessionStore as OriginalSessionStore
from django.http import JsonResponse
from django.utils.crypto import get_random_string

from mehr_takhfif.settings import SAFE_IP, TEST_USER
from server.authentication import MyModelBackend
from server.utils import *

UserModel = get_user_model()


class SessionStore(OriginalSessionStore):
    def _get_new_session_key(self):
        while True:
            session_key = get_random_string(40, random_data)
            if not self.exists(session_key):
                break
        return session_key


class Login_old(View):
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
                return JsonResponse({'message': 'شماره موبایل یا پسورد نامعتبر است'}, status=res_code['unauthorized'])
            if is_staff:
                return set_token(user, self.send_activation(user, request))
            login(request, user, backend='server.authentication.MyModelBackend')
            # login(request, user)
            res = {'user': UserSchema().dump(user)}
            basket_count = get_basket_count(user=user)
            res = JsonResponse(res)
            res = set_custom_signed_cookie(res, 'basket_count', basket_count)
            res = set_custom_signed_cookie(res, 'is_login', True)
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


class Login(View):
    def post(self, request):
        data = load_data(request, check_token=False)
        cookie_age = 30 * 60
        username = data['username']
        password = data.get('password', None)
        code = data.get('code', None)
        try:  # Login
            user = User.objects.get(username=username)
            is_staff = user.is_staff
            if user.is_ban:
                return JsonResponse({'message': 'user is banned'}, status=res_code['banned'])
            if code:
                return self.check_code(request, code)
            if user.password[0] == '!':
                request.session['login_with_password'] = False
                res = JsonResponse({'status': 'otp_required'})
                return set_token(user, res)
            if (password is None and user.password) or not user.is_active:
                res = JsonResponse({'status': 'registered_user'})
                return set_token(user, res)
            if not user.check_password(password):
                return JsonResponse({'message': 'شماره موبایل یا پسورد نامعتبر است'}, status=res_code['unauthorized'])
            if is_staff and user.check_password(password) and not request.session.get('login_with_otp'):
                request.session['login_with_password'] = True
                res = JsonResponse({'status': 'otp_required'})
                return set_token(user, res)
            login(request, user, backend='server.authentication.MyModelBackend')
            # login(request, user)
            res = JsonResponse({})
            basket_count = sync_session_basket(request)
            res = set_custom_signed_cookie(res, 'is_login', True)
            res = set_custom_signed_cookie(res, 'basket_count', basket_count)
            res.delete_cookie('token')
            return res
        except User.DoesNotExist:  # Signup
            user = User.objects.create_user(username=username)
            res = JsonResponse({"status": "guest_user"})
            return set_token(user, res)

    @staticmethod
    def check_password(user):
        return user.password[:6] == 'argon2'

    def check_code(self, request, code):
        # TODO: get csrf code
        try:
            client_token = get_custom_signed_cookie(request, 'token', False)
            user = User.objects.get(activation_code=code, token=client_token, is_ban=False,
                                    activation_expire__gte=timezone.now())
            user.activation_expire = timezone.now()
            user.is_active = True
            user.save()
            # login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            status = ''
            if Login.check_password(user) is False:
                status = 'set_password_required'
            if user.is_staff and not request.session.get('login_with_password', False):
                request.session['login_with_otp'] = True
                return JsonResponse({"status": "password_required"})
            login(request, user, backend='server.authentication.MyModelBackend')
            basket_count = sync_session_basket(request)
            res = JsonResponse({'status': status})
            res = set_custom_signed_cookie(res, 'basket_count', basket_count)
            res = set_custom_signed_cookie(res, 'is_login', True)
            res.delete_cookie('token')
            request.session['login_with_password'] = None
            request.session['login_with_otp'] = None
            return res

        except Exception:
            traceback.print_exc()
            return JsonResponse({'message': 'code not found'}, status=res_code['unauthorized'])


class SetPassword(View):
    def put(self, request):
        try:
            user = MyModelBackend.get_user_from_cookie(request)
            data = json.loads(request.body)
            user.set_password(data['password'])
            user.save()
            return JsonResponse({'user': UserSchema().dump(user)})
        except Exception:
            return JsonResponse({}, status=res_code['bad_request'])


class SendCode(View):
    def post(self, request):
        try:
            user = MyModelBackend.get_user_from_cookie(request)
            print(user)
            return self.send_activation(user, request)
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'message': 'token not found'}, status=res_code['bad_request'])

    def send_activation(self, user, request=None):
        resend_timeout = 1
        activation_expire = 2
        if timezone.now() < add_minutes((resend_timeout - activation_expire), time=user.activation_expire):
            return JsonResponse(
                {'resend_timeout': add_minutes(resend_timeout * -1, time=user.activation_expire).timestamp(),
                 'activation_expire': user.activation_expire.timestamp()})
        user.activation_code = random.randint(10000, 99999)
        user.activation_expire = add_minutes(activation_expire)
        user.save()
        ip = request.META.get('REMOTE_ADDR') or request.META.get('HTTP_X_FORWARDED_FOR')
        res = {'resend_timeout': add_minutes(resend_timeout).timestamp(),
               'activation_expire': add_minutes(activation_expire).timestamp(), 'code': user.activation_code}
        if not (DEBUG or (ip in SAFE_IP and user.username == TEST_USER)):
            send_sms(user.username, "verify", user.activation_code)
            res = {'resend_timeout': add_minutes(resend_timeout).timestamp(),
                   'activation_expire': user.activation_expire.timestamp()}
        return JsonResponse(res, status=res_code['updated'])


class LogoutView(View):
    def post(self, request):
        try:
            logout(request)
            res = JsonResponse({})
            res.delete_cookie('basket_count', domain=DEFAULT_COOKIE_DOMAIN)
            res = set_custom_signed_cookie(res, 'is_login', False)
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
