import functools
import re
import traceback

from django.core.exceptions import FieldDoesNotExist, PermissionDenied, FieldError
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest

from mtadmin.exception import *
from server.utils import res_code


def error_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (FieldError, TypeError, KeyError, ValueError, AttributeError):
            traceback.print_exc()
            return JsonResponse({'message': 'مشکلی پیش آمده', 'variant': 'error'}, status=res_code['bad_request'])
        except ActivationError as e:
            traceback.print_exc()
            return JsonResponse({'message': str(e), 'variant': 'warning'}, status=res_code['activation_warning'])
        except WarningMessage as e:
            traceback.print_exc()
            return JsonResponse({'message': str(e), 'variant': 'warning'}, status=res_code['updated'])
        except ObjectDoesNotExist:
            traceback.print_exc()
            return JsonResponse({'message': 'اینی که گفتی رو پیداش نکردم که 🤨', 'variant': 'error'},
                                status=res_code['object_does_not_exist'])
        except ValidationError as e:
            try:
                traceback.print_exc()
                # return JsonResponse({'message': e.message, 'variant': 'error'}, status=res_code['bad_request'])
                return JsonResponse({'message': str(e), 'variant': 'error'}, status=res_code['bad_request'])
            except Exception:
                traceback.print_exc()
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
                return JsonResponse(
                    {"message": f"مشکل داره {field}", "variant": "error"},
                    status=res_code['integrity'])
            except (TypeError, IntegrityError):
                e = str(e).split('DETAIL', 1)[0][:-1]
                print(e)
                return JsonResponse({'message': str(e)}, status=res_code['integrity'])
        except FieldDoesNotExist:
            traceback.print_exc()
            return JsonResponse({'message': 'fields name is incorrect'}, status=res_code['bad_request'])

    return wrapper
