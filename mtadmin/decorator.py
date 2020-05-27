import functools
import traceback
import re

from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.core.exceptions import FieldDoesNotExist, ValidationError, PermissionDenied, FieldError
from django.db.utils import IntegrityError
from server.utils import res_code
from django.core.exceptions import NON_FIELD_ERRORS, ObjectDoesNotExist
from mtadmin.exception import *


def error_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (FieldError, TypeError, KeyError):
            traceback.print_exc()
            return HttpResponseBadRequest()
        except ActivationError as e:
            return JsonResponse({'message': str(e), 'variant': 'warning'}, status=res_code['activation_warning'])
        except WarningMessage as e:
            return JsonResponse({'message': str(e), 'variant': 'warning'}, status=res_code['updated'])
        except ObjectDoesNotExist:
            return JsonResponse({'message': 'اینی که گفتی رو پیداش نکردم که 🤨', 'variant': 'error'},
                                status=res_code['object_does_not_exist'])
        except ValidationError as e:
            try:
                non_field_errors = e.message_dict[NON_FIELD_ERRORS][0]
                return JsonResponse({'message': non_field_errors, 'variant': 'error'}, status=res_code['bad_request'])
            except Exception:
                return HttpResponseBadRequest()
        except PermissionDenied:
            traceback.print_exc()
            return HttpResponseForbidden()
        except AssertionError:
            traceback.print_exc()
            return JsonResponse({}, status=res_code['token_issue'])
        except IntegrityError as e:
            traceback.print_exc()
            pattern = r'(\((\w+)\))='
            try:
                field = re.search(pattern, str(e))[2]
                return JsonResponse({'type': 'duplicate', 'field': field}, status=res_code['integrity'])
            except (TypeError, IntegrityError):
                e = str(e).split('DETAIL', 1)[0][:-1]
                print(e)
                return JsonResponse({'message': str(e)}, status=res_code['integrity'])
        except FieldDoesNotExist:
            traceback.print_exc()
            return JsonResponse({'message': 'fields name is incorrect'}, status=res_code['bad_request'])
    return wrapper
