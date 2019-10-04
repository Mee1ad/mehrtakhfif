from django.contrib.auth import authenticate, login
from server.models import *
import pysnooper
from django.apps import apps
import jwt
import json
from django.http import JsonResponse, HttpResponse, HttpRequest
from mehr_takhfif.settings import TOKEN_SECRET
from server.views.utils import Tools
from django.urls import resolve


class AuthMiddleware:
    def __init__(self, get_response):
        super().__init__()
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        try:
            request.lang = request.headers['language']
        except Exception:
            request.lang = 'persian'
        try:
            request.params = Tools.filter_params(request)
        except Exception:
            request.params = {}
        try:
            app_name = resolve(request.path_info).app_name
            if app_name == 'mehrpeyk':
                import time
                time.sleep(.6)
                s = ['mehrpeyk/splash', 'mehrpeyk/login', 'mehrpeyk/sign_up']
                if resolve(request.path_info).route not in s:
                    try:
                        token = request.headers['Authorization']
                        first_decrypt = jwt.decode(token[7:-20], token[-20:], algorithms=['HS256'])
                        second_decrypt = jwt.decode(first_decrypt['data'].encode(), TOKEN_SECRET, algorithms=['HS256'])
                        request.peyk_id = second_decrypt['user']['id']
                    except Exception as e:
                        print(e)
                        return JsonResponse({'message': f'{e}'}, status=401)
            request.user = User.objects.get(pk=1)
            delay = request.GET.get('delay', None)
            if delay:
                import time
                print(delay)
                time.sleep(float(delay))
            error = request.GET.get('error', None)
            if error:
                status_code = request.GET.get('status_code', 501)
                return JsonResponse({}, status=status_code)

            # print(request.headers)
            # print(json.loads(request.body))
            # token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRhIjoiZXlKMGVYQWlPaUpLVjFRaUxDSmhiR2NpT2lKSVV6STFOaUo5LmV5SjFjMlZ5SWpwN0ltWnBjbk4wWDI1aGJXVWlPbTUxYkd3c0lteGhjM1JmYm1GdFpTSTZiblZzYkN3aWJHRnVaM1ZoWjJVaU9pSm1ZU0lzSW1WdFlXbHNJam9pSWl3aWNHaHZibVVpT2lJaUxDSjNZV3hzWlhSZmJXOXVaWGtpT201MWJHd3NJblpwY0NJNlptRnNjMlVzSW1GalkyVnpjMTkwYjJ0bGJpSTZJbk5zYTIxbWJHdHpaV3B1Wm05bGFYTm9iMlpwYUdWemIybG1hbVYzYjJsbWFuQnZkMlU3YW1admQyVm1ORGMxZDJWbU5qVjNaU3M1Tm1ZMUszZGxPVFkxWnpRNE9UWjNjalZuS3prMmNuZGxOR2M1T0RaeWR6VTJPR2M1TlhKbEt6azJaelZ5WlNzNVp6VmxjalZuT1hKbE5pSjlmUS5GR3BTQlU2VTdncU9kUDJnUFYxNS1SRE9JY2FFWUw1OExtaXFMenkyNXlJIn0.pAzbUs9iB5XPQ_TMVkNqpD9SD4YWM7iCoAfliXWQpXs4696f0769f6e850968ffe9aad83d756a6765e62a4b0e7b6766c0"
            # first_decrypt = jwt.decode(token[:-52], token[-52:-32], algorithms=['HS256'])
            # second_decrypt = jwt.decode(first_decrypt['data'].encode(), TOKEN_SECRET, algorithms=['HS256'])
        except KeyError:
            pass
        except json.decoder.JSONDecodeError:
            pass
        response = self.get_response(request)
        # sleep(.5)
        # Code to be executed for each request/response after
        # the view is called.
        return response
