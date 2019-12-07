import functools
import json
import sys
import traceback

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse

from server.models import *


def try_except(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ObjectDoesNotExist:
            traceback.print_exc()
            print("Error: Can't find object")
            return JsonResponse({'message': 'Error: 1001'}, status=295)
        except ValidationError:
            return JsonResponse({}, status=400)
        except json.decoder.JSONDecodeError:
            print('Json Decode Error')
            traceback.print_exc()

        except Exception:
            traceback.print_exc()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_type = exc_type.__name__
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            trace = {'Type': error_type, 'Description': f'{exc_obj}', 'File': fname, 'Line': exc_tb.tb_lineno}
            # devices = FCMDevice.objects.filter(device_id='469f8ce1bfe86a95')
            # devices.send_message(title="oops, an error occurred", body=error_type + f', {exc_obj}', sound="cave")
            return HttpResponse(f'{error_type}: {exc_obj} {fname}')
            # return JsonResponse({'message': 'We have an unexpected error. sorry about that,'
            #                                 ' but we will handle it as soon as possible'}, status=500)

    return wrapper
