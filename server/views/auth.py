import random

from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.backends import ModelBackend
from django.http import JsonResponse
from django.db.models import ProtectedError
from server.utils import *
from server.serialize import UserSchema
import pysnooper


class Backend(ModelBackend):
    @staticmethod
    def get_user_from_cookie(request):
        try:
            client_token = request.get_signed_cookie('token', False, salt=TOKEN_SALT)
            return User.objects.get(token=client_token, is_ban=False)
        except Exception:
            return None


class Login(View):
    @pysnooper.snoop()
    def post(self, request):
        data = load_data(request, check_token=False)
        cookie_age = 30 * 60
        username = data['username']
        password = data.get('password', None)
        try:  # Login
            user = User.objects.get(username=username)
            if user.is_ban:
                return JsonResponse({'message': 'user is banned'}, status=res_code['banned'])
            if password is None:  # otp
                if user.privacy_agreement:  # 202 need activation code (login)
                    return set_token(user, self.send_activation(user))
                # res = JsonResponse({}, status=251) # please agree privacy policy (signup)
                # return self.set_token(user, res)
                raise User.DoesNotExist  # redirect to signup
            if not user.is_active:  # incomplete signup
                raise User.DoesNotExist  # redirect to signup
            assert user.check_password(password)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            res = {'user': UserSchema().dump(user)}
            basket = Basket.objects.filter(user=user).order_by('-id')
            if basket.exists():
                res['basket_count'] = basket.first().products.all().count()
            return JsonResponse(res)
        except User.DoesNotExist:  # Signup
            try:
                user.delete()
            except (ProtectedError, UnboundLocalError):
                pass
            user = User.objects.create_user(username=username, password=password)
            res = JsonResponse({}, status=res_code['signup_with_pp'])  # please agree privacy policy
            return set_token(user, res)
        except AssertionError:  # invalid password
            return JsonResponse({}, status=res_code['invalid_password'])

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
        return JsonResponse(res, status=res_code['activate'])

    @staticmethod
    def send_sms(phone, code):
        pass  # TODO: send sms

    @staticmethod
    def check_password(user):
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
            return JsonResponse({}, status=res_code['unauthorized'])

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
            return JsonResponse({'user': UserSchema().dump(user)})
        except Exception:
            return JsonResponse({}, status=res_code['bad_request'])


class ResendCode(View):
    @pysnooper.snoop()
    def post(self, request):
        try:
            user = Backend.get_user_from_cookie(request)
            res = Login.send_activation(user)
            res.status_code = 204
            return res
        except Exception:
            return JsonResponse({'message': 'token not found'}, status=res_code['bad_request'])


class Activate(View):
    @pysnooper.snoop()
    def post(self, request):
        data = load_data(request)
        # TODO: get csrf code
        try:
            client_token = request.get_signed_cookie('token', False, salt=TOKEN_SALT)
            code = data['code']
            user = User.objects.get(activation_code=code, token=client_token, is_ban=False,
                                    activation_expire__gte=timezone.now())
            user.activation_expire = timezone.now()
            user.is_active = True
            user.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            res = {'user': UserSchema().dump(user)}  # signup without password
            basket = Basket.objects.filter(user=user).order_by('-id')
            if basket.exists():
                res['basket_count'] = basket.first().products.all().count()
            response = JsonResponse(res, status=res_code['signup_with_pass'])
            if Login.check_password(user):
                response = JsonResponse(res)  # successful login
                response.delete_cookie('token')
            return response
        except Exception:
            return JsonResponse({'message': 'code not found'}, status=res_code['integrity'])


class LogoutView(View):
    def post(self, request):
        try:
            logout(request)
            return JsonResponse({})
        except Exception:
            return JsonResponse({}, status=res_code['forbidden'])
