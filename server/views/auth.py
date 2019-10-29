from django.contrib.auth.backends import ModelBackend
from django.views import View
from server.models import *
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core import serializers
import json
from .utils import *
import random
from django.contrib.auth.hashers import (
    check_password, is_password_usable, make_password,
)
from server.decorators import try_except
from django.db.models import Q
import pysnooper
from mehr_takhfif.settings import HOST as host
import os
from django.contrib.sessions.models import Session
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.views.decorators.cache import cache_page
import time
from django.core.cache import cache
from mehr_takhfif.settings import CACHE_TTL
from secrets import token_hex
from django.contrib.auth import get_user_model

token_salt = 'nkU^&*()JH*757H*&^)_IJIO7JI874434%^&OHdfgdG457HIO44'


class Backend(ModelBackend):
    @staticmethod
    def get_user_from_cookie(request):
        try:
            client_token = request.get_signed_cookie('token', False, salt=token_salt)
            return User.objects.get(token=client_token, is_ban=False)
        except Exception:
            return None


class Login(Validation):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        cookie_age = 30 * 60
        try: # Login
            username = data['username']
            password = data['password']
            user = User.objects.get(username=username)
            if user.is_ban:
                return JsonResponse({'message': 'user is banned'}, status=403)
            if password is None: # otp
                if user.privacy_agreement: # 202 need activation code (login)
                    return self.set_token(user, self.send_activation(user))
                # res = JsonResponse({}, status=251) # please agree privacy policy (signup)
                # return self.set_token(user, res)
                raise User.DoesNotExist # redirect to signup
            if not user.is_active: # incomplete signup
                raise User.DoesNotExist # redirect to signup
            assert user.check_password(password)
            login(request, user)
            return JsonResponse(UserSchema().dump(user))
        except User.DoesNotExist: # Signup
            if 'user' in locals():
                user.delete()      
            user = User.objects.create_user(username=username, password=password)
            res = JsonResponse({}, status=251) # please agree privacy policy
            return self.set_token(user, res)
        except AssertionError: # invalid password
            return JsonResponse({}, status=401)
    
    @staticmethod
    @pysnooper.snoop()
    def send_activation(user):
        resend_timeout = 0.5
        activation_expire = 2
        user.activation_code = random.randint(10000, 99999)
        user.activation_expire = add_minutes(activation_expire)
        user.save()          
        Login.send_sms(user.username, user.activation_code)
        res = {'code': user.activation_code, 'resend_timeout': resend_timeout, 'timeout': activation_expire}
        return JsonResponse(res , status=202)

    @staticmethod
    def set_token(user, response):
        try:
            user.token = token_hex(100)
            user.save()
            response.set_signed_cookie('token', user.token, token_salt, max_age=7200, expires=7200)
            return response
        except Exception:
            return JsonResponse({}, status=401)

    @staticmethod
    def send_sms(phone, code):
        pass # TODO: send sms

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
            return Login.send_activation(user) # need activation code
        except Exception:
            return JsonResponse({}, status=401)

    @staticmethod
    def get_user(request):
        client_token = request.get_signed_cookie('token', False, salt=token_salt)
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
        resend_timeout = Login.resend_timeout
        activation_expire = Login.activation_expire
        try:
            user = Backend.get_user_from_cookie(request)
            user.activation_code = random.randint(10000, 99999)
            assert timezone.now() > add_minutes(resend_timeout-activation_expire, time=user.activation_expire)
            user.activation_expire = add_minutes(activation_expire)
            user.save()
            return JsonResponse({'code': user.activation_code, 'timeout': resend_timeout}, status=204)
        except Exception:
            return JsonResponse({'message': 'token not found'}, status=400)


class Activate(View):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        # TODO: get csrf code
        try:
            client_token = request.get_signed_cookie('token', False, salt=token_salt)
            code = data['code']
            user = User.objects.get(activation_code=code, token=client_token, is_ban=False, activation_expire__gte=timezone.now())
            user.activation_expire = timezone.now()
            user.is_active = True
            user.save()
            login(request, user)
            res = JsonResponse(UserSchema().dump(user), status=201) # signup without password
            if Login.check_password(user):
                res = JsonResponse(UserSchema().dump(user)) # successfull login
                res.delete_cookie('token')
            return res
        except Exception:
            return JsonResponse({'message': 'code not found'}, status=406)

    









