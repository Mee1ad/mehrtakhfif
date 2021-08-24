import functools
import json
import sys
import traceback

from django.http import JsonResponse, HttpResponseServerError, HttpResponseForbidden, HttpResponseBadRequest
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from server.models import *
from server.utils import res_code
from django.core.exceptions import NON_FIELD_ERRORS
import pysnooper
from server.views.client.home import Init
from django.core.paginator import EmptyPage



def try_except(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (PermissionDenied, PermissionError):
            user = args[0].user
            return Init.set_login_cookie(user)
        except json.decoder.JSONDecodeError:
            traceback.print_exc()
            return HttpResponseServerError()
        except ValidationError as e:
            traceback.print_exc()
            # non_field_errors = e.message_dict[NON_FIELD_ERRORS][0]
            try:
                return JsonResponse({'message': e.messages[0], 'varaiant': 'error'}, status=res_code['bad_request'])
            except Exception:
                return HttpResponseBadRequest()
        except (AssertionError, StopIteration, AttributeError, KeyError, ValueError, TypeError,
                EmptyPage):
            traceback.print_exc()
            return HttpResponseBadRequest()
        except ObjectDoesNotExist:
            traceback.print_exc()
            return JsonResponse({}, status=404)
        # except Exception as e:  handled by sentry
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            # error_type = exc_type.__name__
            # fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            # trace = {'Type': error_type, 'Description': f'{exc_obj}', 'File': fname, 'Line': exc_tb.tb_lineno}
            # devices = FCMDevice.objects.filter(device_id='469f8ce1bfe86a95')
            # devices.send_message(title="oops, an error occurred", body=error_type + f', {exc_obj}', sound="cave")
            # return HttpResponse(f'{error_type}: {exc_obj} {fname}')
            # return HttpResponseServerError()

    return wrapper
