import random
from secrets import token_hex

import pysnooper
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.backends import ModelBackend
from django.http import JsonResponse

from mehr_takhfif.settings import TOKEN_SALT
from .utils import *
from server.serialize import UserSchema


class Backend(ModelBackend):
    @staticmethod
    def get_user_from_cookie(request):
        try:
            client_token = request.get_signed_cookie('token', False, salt=TOKEN_SALT)
            return User.objects.get(token=client_token, is_ban=False)
        except Exception:
            return None


class Login(Validation):
    def post(self, request):
        data = json.loads(request.body)
        cookie_age = 30 * 60
        username = data['username']
        password = data['password']
        try:  # Login
            user = User.objects.get(username=username)
            if user.is_ban:
                return JsonResponse({'message': 'user is banned'}, status=493)
            if password is None:  # otp
                if user.privacy_agreement:  # 202 need activation code (login)
                    return self.set_token(user, self.send_activation(user))
                # res = JsonResponse({}, status=251) # please agree privacy policy (signup)
                # return self.set_token(user, res)
                raise User.DoesNotExist  # redirect to signup
            if not user.is_active:  # incomplete signup
                raise User.DoesNotExist  # redirect to signup
            assert user.check_password(password)
            login(request, user)
            res = {'user': UserSchema().dump(user)}
            basket = Basket.objects.filter(user=user, active=True)
            if basket.exists():
                res['basket_count'] = basket.first().products.all().count()
            return JsonResponse(res)
        except User.DoesNotExist:  # Signup
            if 'user' in locals():
                # noinspection PyUnboundLocalVariable
                user.delete()
            user = User.objects.create_user(username=username, password=password)
            res = JsonResponse({}, status=251)  # please agree privacy policy
            return self.set_token(user, res)
        except AssertionError:  # invalid password
            return JsonResponse({}, status=450)

    @staticmethod
    @pysnooper.snoop()
    def send_activation(user):
        resend_timeout = 0.5
        activation_expire = 2
        assert timezone.now() > add_minutes(resend_timeout - activation_expire, time=user.activation_expire)
        user.activation_code = random.randint(10000, 99999)
        user.activation_expire = add_minutes(activation_expire)
        user.save()
        Login.send_sms(user.username, user.activation_code)
        res = {'code': user.activation_code, 'resend_timeout': resend_timeout, 'timeout': activation_expire}
        return JsonResponse(res, status=202)

    @staticmethod
    def set_token(user, response):
        try:
            user.token = token_hex(100)
            user.save()
            response.set_signed_cookie('token', user.token, TOKEN_SALT, max_age=7200, expires=7200)
            return response
        except Exception:
            return JsonResponse({}, status=401)

    @staticmethod
    def send_sms(phone, code):
        pass  # TODO: send sms

    @staticmethod
    def check_password(user):
        print(user.password[:6])
        return user.password[:6] == 'argon2'


class PrivacyPolicy(View):
    @pysnooper.snoop()
    def put(self, request):
        try:
            user = Backend.get_user_from_cookie(request)
            user.privacy_agreement = True
            user.save()
            return Login.send_activation(user)  # need activation code
        except Exception:
            return JsonResponse({}, status=401)

    @staticmethod
    def get_user(request):
        client_token = request.get_signed_cookie('token', False, salt=TOKEN_SALT)
        return User.objects.get(token=client_token)


class SetPassword(View):
    @pysnooper.snoop()
    def put(self, request):
        try:
            user = Backend.get_user_from_cookie(request)
            data = json.loads(request.body)
            user.set_password(data['new_password'])
            user.save()
            return JsonResponse(UserSchema().dump(user))
        except Exception:
            return JsonResponse({}, status=400)


class ResendCode(View):
    @pysnooper.snoop()
    def post(self, request):
        try:
            user = Backend.get_user_from_cookie(request)
            res = Login.send_activation(user)
            res.status_code = 204
            return res
        except Exception:
            return JsonResponse({'message': 'token not found'}, status=400)


class Activate(View):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        # TODO: get csrf code
        try:
            client_token = request.get_signed_cookie('token', False, salt=TOKEN_SALT)
            code = data['code']
            user = User.objects.get(activation_code=code, token=client_token, is_ban=False,
                                    activation_expire__gte=timezone.now())
            user.activation_expire = timezone.now()
            user.is_active = True
            user.save()
            login(request, user)
            res = JsonResponse(UserSchema().dump(user), status=201)  # signup without password
            if Login.check_password(user):
                res = JsonResponse(UserSchema().dump(user))  # successfull login
                res.delete_cookie('token')
            return res
        except Exception:
            return JsonResponse({'message': 'code not found'}, status=406)


class LogoutView(View):
    def post(self, request):
        try:
            logout(request)
            return JsonResponse({})
        except Exception:
            return JsonResponse({}, status=403)
