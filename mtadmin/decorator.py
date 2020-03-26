import functools
import traceback
import re

from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.core.exceptions import FieldDoesNotExist, ValidationError, PermissionDenied, FieldError
from django.db.utils import IntegrityError
from server.utils import res_code


def error_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FieldError:
            return HttpResponseBadRequest()
        except PermissionDenied:
            return HttpResponseForbidden()
        except AssertionError:
            traceback.print_exc()
            return JsonResponse({}, status=res_code['token_issue'])
        except IntegrityError as e:
            traceback.print_exc()
            pattern = r'(\((\w+)\))='
            field = re.search(pattern, str(e))[2]
            return JsonResponse({'type': 'duplicate', 'field': field}, status=res_code['integrity'])
        except (FieldDoesNotExist, ValidationError):
            traceback.print_exc()
            return JsonResponse({'message': 'fields name is incorrect'}, status=res_code['bad_request'])
    return wrapper
