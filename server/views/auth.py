from django.shortcuts import render
from django.views import View
from server.models import *
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core import serializers
import json
from .utils import *
from django.contrib import messages
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
from server import serializer as serialize


class Error(Tools):
    def get(self, request):
        return HttpResponse(status=413)


class Test(Tools):
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
    @try_except
    def post(self, request):
        data = json.loads(request.body)
        phone = self.valid_phone(data['phone'])
        password = data['password']
        activation_code = random.randint(10000, 99999)
        activation_code_salted = make_password(activation_code, 'activation_code')
        activation_expire = self.add_minutes(5)
        try:
            user = User.objects.get(phone=phone)
            if user.is_active:
                return JsonResponse({'message': 'already signed up'}, status=204)
            user.activation_code = activation_code_salted
            user.activation_expire = activation_expire
        except User.DoesNotExist:
            user = User.objects.create_user(phone=phone, username=phone, password=password, email=None,
                                            activation_code=activation_code_salted, activation_expire=activation_expire)

        user.save()
        # todo send sms
        res = {'token': user.activation_code, 'code': activation_code}
        # user.groups.add(1)
        return JsonResponse(res, status=201)


class Activate(Tools):
    @try_except
    def post(self, request):
        data = json.loads(request.body)
        # todo get csrf code
        code = data['code']
        try:
            print(make_password(code, 'activation_code'))
            user = User.objects.get(activation_code=make_password(code, 'activation_code'), is_ban=False,
                                    activation_expire__gte=timezone.now())
            user.activation_code = timezone.now()
            user.last_login = timezone.now()
            user.is_active = True
            user.access_token = self.generate_token(request, user)
            user.save()
            login(request, user)
            user = serialize.user(user)
            return JsonResponse(user)
        except User.DoesNotExist:
            return JsonResponse({'message': 'code not found'}, status=406)


class ResendCode(Tools):
    @try_except
    def post(self, request):
        data = json.loads(request.body)
        token = data['token']
        try:
            user = User.objects.get(activation_code=token, is_ban=False)
            activation_code = random.randint(10000, 99999)
            user.activation_code = make_password(activation_code, 'activation_code')
            user.save()
            return JsonResponse({'code': activation_code, 'token': user.activation_code})
        except User.DoesNotExist:
            return JsonResponse({'message': 'token not found'}, status=406)


class Login(Validation):
    @try_except
    def post(self, request):
        data = json.loads(request.body)
        phone = self.valid_phone(data['username'], raise_error=False)
        email = self.valid_email(data['username'], raise_error=False)
        password = data['password']
        time.sleep(3)
        try:
            if phone:
                user = User.objects.get(phone=phone)
            if email:
                user = User.objects.get(email=email)
            valid_password = user.check_password(password)
            if user.is_ban:
                return JsonResponse({'message': 'user is banned'}, status=403)
            if not valid_password:
                return JsonResponse({'message': 'password is wrong'}, status=406)
            if not user.is_active:
                activation_code = random.randint(10000, 99999)
                activation_code_salted = make_password(activation_code, 'activation_code')
                user.activation_code = activation_code_salted
                activation_expire = self.add_minutes(5)
                user.activation_expire = activation_expire
                user.save()
                res = {'token': user.activation_code, 'code': activation_code}
                # todo send sms
                return JsonResponse(res, status=201)
            login(request, user)
            request.session['counter'] = 1
            user = serialize.user(obj=user)
            res = JsonResponse({'user': user})
            return res
        except Exception:
            return JsonResponse({'message': 'user does not exist'}, status=401)


class ResetPasswordRequest(Validation):
    @try_except
    def post(self, request):
        data = json.loads(request.body)
        phone = self.valid_phone(data['username'], raise_error=False)
        email = self.valid_email(data['username'], raise_error=False)
        try:
            user = User.objects.get(Q(phone=phone) | Q(email=email), is_active=True)
            self.generate_token(request, user)
            # todo send email or sms
            return JsonResponse({'url': host + '/reset_password?token=' + user.access_token})
        except User.DoesNotExist:
            return JsonResponse({'message': 'user not found'}, status=404)


class ResetPassword(Tools):
    @try_except
    def post(self, request):
        data = json.loads(request.body)
        token = data['token']
        password = data['new_password']
        try:
            user = User.objects.get(access_token=token)
            user.set_password(password)
            self.generate_token(request, user)
            return JsonResponse({'message': 'password changed'})
        except User.DoesNotExist:
            return JsonResponse({'message': 'page not found'}, status=404)



