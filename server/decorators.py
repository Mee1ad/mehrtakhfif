import functools
import json
import sys
import traceback

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponseServerError, HttpResponseForbidden, HttpResponseBadRequest
from django.core.exceptions import PermissionDenied

from server.models import *
from server.utils import res_code


def try_except(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PermissionDenied:
            return HttpResponseForbidden()
        except json.decoder.JSONDecodeError:
            traceback.print_exc()
            return HttpResponseServerError()
        except ValidationError as e:
            try:
                e = dict(e)
                first_key = next(iter(e))
                return JsonResponse({'type': 'validation', 'field': first_key, 'error': e[first_key][0]},
                                    status=res_code['bad_request'])
            except Exception:
                return HttpResponseBadRequest()
        except (AssertionError, ObjectDoesNotExist, StopIteration, AttributeError, KeyError):
            traceback.print_exc()
            return HttpResponseBadRequest()
        except Exception:
            traceback.print_exc()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_type = exc_type.__name__
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            trace = {'Type': error_type, 'Description': f'{exc_obj}', 'File': fname, 'Line': exc_tb.tb_lineno}
            # devices = FCMDevice.objects.filter(device_id='469f8ce1bfe86a95')
            # devices.send_message(title="oops, an error occurred", body=error_type + f', {exc_obj}', sound="cave")
            # return HttpResponse(f'{error_type}: {exc_obj} {fname}')
            return HttpResponseServerError

    return wrapper
