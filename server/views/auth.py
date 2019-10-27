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
from django.contrib.auth.hashers import make_password
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
from django.contrib.auth.hashers import make_password
from secrets import token_hex


class Login(Validation):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        try: # Login
            # assert not request.user.is_authenticated
            username = data['username']
            password = data['password']
            user = User.objects.get(username=username)
            if user.is_ban:
                return JsonResponse({'message': 'user is banned'}, status=403)
            if not user.is_active: # incomplete signup
                user.delete()
                raise User.DoesNotExist
            if not password: # otp
                return JsonResponse(self.activate(request, user), status=202)
            assert user.check_password(password)
            login(request, user)
            return JsonResponse(UserSchema().dump(user))
        except User.DoesNotExist: # Signup
            activation_code = random.randint(10000, 99999)
            user = User.objects.create_user(username=username, activation_code=activation_code, password=password,
                                            activation_expire=add_minutes(5)).save()
            request.session['token'] = token_hex(125)
            self.send_sms(user.username, activation_code)
            return JsonResponse({'token': request.session['token'], 'code': activation_code}, status=201)
        except AssertionError: # invalid password
            return JsonResponse({}, status=401)

    def activate(self, request, user):
        user.activation_code = random.randint(10000, 99999)
        user.activation_expire = add_minutes(5)
        user.save()
        request.session['pass'] = False
        request.session['token'] = token_hex(125)
        self.send_sms(user.username, activation_code)
        return {'token': request.session['token'], 'code': user.activation_code}

    @staticmethod
    def send_sms(phone, code):
        pass # TODO: send sms


class ResendCode(View):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        try:
            assert request.session['token'] == data['token']
            user = User.objects.get(activation_code=token, is_ban=False)
            activation_code = random.randint(10000, 99999)
            user.activation_code = make_password(activation_code, 'activation_code')
            user.save()
            return JsonResponse({'code': activation_code, 'token': user.activation_code})
        except Exception:
            return JsonResponse({'message': 'token not found'}, status=406)


class Activate(View):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        # TODO: get csrf code
        try:
            assert request.session['token'] == data['token']
            code = data['code']
            user = User.objects.get(activation_code=code, is_ban=False, activation_expire__gte=timezone.now())
            user.activation_expire = timezone.now()
            user.is_active = True
            user.save()
            login(request, user)
            if user.password is not None:
                return JsonResponse(UserSchema().dump(user))
            return JsonResponse({'token': data['token']}, status=201)
        except Exception:
            return JsonResponse({'message': 'code not found'}, status=406)







class Test(View):
    permission_required = ''

    def get(self, request):
        qs = User.objects.get(pk=1)
        # print(user)
        # self.generate_token(request, user)
        # user = serialize.user(user)
        # cache.set('secret', 'test')
        # print(request.session.keys())
        # request.session['name'] = 'bilad'
        # a = request.session.get('name', 'nothing')
        return HttpResponse('ok')


class Signup(Validation):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        username = self.valid_phone(data['username'])
        password = data['password']
        activation_code = random.randint(10000, 99999)
        activation_expire = add_minutes(5)
        try:
            user = User.objects.get(username=username)
            if user.is_active:
                return JsonResponse({'message': 'already signed up'}, status=204)
            user.activation_code = activation_code
            user.activation_expire = activation_expire
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=password, email=None, activation_code=activation_code,
                                            activation_expire=activation_expire)
        user.refresh_token = token_hex(100)
        user.save()
        # todo send sms
        res = {'token': user.refresh_token, 'code': activation_code}
        # user.groups.add(1)
        return JsonResponse(res, status=201)



class Login_old(Validation):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        try:
            phone = self.valid_phone(data['username'], raise_error=False)
            email = self.valid_email(data['username'], raise_error=False)
            password = data['password']
            if phone:
                user = User.objects.get(phone=phone)
            if email:
                user = User.objects.get(email=email)
            # assert not request.user.is_authenticated
            valid_password = user.check_password(password)
            if user.is_ban:
                return JsonResponse({'message': 'user is banned'}, status=403)
            if not valid_password:
                return JsonResponse({'message': 'password is wrong'}, status=406)
            if not user.is_active:
                activation_code = random.randint(10000, 99999)
                activation_code_salted = make_password(activation_code, 'activation_code')
                user.activation_code = activation_code_salted
                activation_expire = add_minutes(5)
                user.activation_expire = activation_expire
                user.access_token = generate_token(user)
                user.save()
                login(request, user)
                res = {'token': user.activation_code, 'code': activation_code}
                # todo send sms
                return JsonResponse(res, status=201)
            token = generate_token(user)
            user.access_token = token['token']
            user.access_token_expire = token['expire']
            user.save()
            login(request, user)
            user = UserSchema().dump(User.objects.get(access_token=user.access_token))
            return JsonResponse(user)
        # except AssertionError:
        #     return JsonResponse({'message': 'user is  logged in'}, status=401)
        except Exception:
            return JsonResponse({'message': 'user does not exist'}, status=401)


class SetPassword(LoginRequired):
    @pysnooper.snoop()
    def post(self, request):
        request.user.set_password(request.data['new_password'])
        return JsonResponse({'message': 'ok'})


class ResetPasswordRequest(Validation):
    @pysnooper.snoop()
    def post(self, request):
        username = json.loads(request.body)['username']
        try:
            token = token_hex(10)
            user = User.objects.filter(username=username, is_active=True)
            user.update(token=token, token_expire=add_minutes(5))
            Login.send_sms(user.username, code)
            return JsonResponse({'token': token})
        except User.DoesNotExist:
            return JsonResponse({'message': 'user not found'}, status=404)


class ResetPassword(View):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        token = data['token']
        password = data['new_password']
        try:
            user = User.objects.get(reset_token=token, reset_token_expire__gt=timezone.now())
            user.set_password(password)
            user.reset_token_expire = timezone.now()
            user.access_token = self.generate_token(request, user)
            user.save()
            return JsonResponse(UserSchema().dump(user))
        except User.DoesNotExist:
            return JsonResponse({'message': 'user not found'}, status=404)



