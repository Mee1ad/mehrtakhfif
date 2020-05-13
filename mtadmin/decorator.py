import functools
import traceback
import re

from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.core.exceptions import FieldDoesNotExist, ValidationError, PermissionDenied, FieldError
from django.db.utils import IntegrityError
from server.utils import res_code
import os
import sys


def error_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (FieldError, TypeError, KeyError):
            traceback.print_exc()
            return HttpResponseBadRequest()
        except ValidationError as e:
            print(str(e)[2:-2])
            # res = HttpResponseBadRequest()
            # res['error'] = str(e)[2:-2]
            return JsonResponse({'type': 'validation', 'error': str(e)[2:-2]}, status=res_code['bad_request'])
        except PermissionDenied:
            traceback.print_exc()
            return HttpResponseForbidden()
        except AssertionError:
            traceback.print_exc()
            return JsonResponse({}, status=res_code['token_issue'])
        except IntegrityError as e:
            pattern = r'(\((\w+)\))='
            try:
                field = re.search(pattern, str(e))[2]
                return JsonResponse({'type': 'duplicate', 'field': field}, status=res_code['integrity'])
            except (TypeError, IntegrityError):
                e = str(e).split('DETAIL', 1)[0][:-1]
                print(e)
                return JsonResponse({'error': str(e)}, status=res_code['integrity'])
        except FieldDoesNotExist:
            traceback.print_exc()
            return JsonResponse({'message': 'fields name is incorrect'}, status=res_code['bad_request'])
    return wrapper
