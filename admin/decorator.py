import functools
import traceback
import re

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db.utils import IntegrityError
from server.views.utils import res_code
from server.error import *


def error_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
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
        except AuthError:
            traceback.print_exc()
            return JsonResponse({'message': 'authentication failed'}, status=res_code['forbidden'])
    return wrapper