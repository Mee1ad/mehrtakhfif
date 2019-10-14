from django.http import JsonResponse
from mehrpeyk.models import *
from django.views import View
import json
from django.contrib.auth.hashers import make_password
import random
from .serialize import *
import jwt
from mehr_takhfif.settings import TOKEN_SECRET, SALT
from secrets import token_hex
import pysnooper
from server.views.utils import Validation
from django.db import IntegrityError


class VersionInfo(View):
    def get(self, request):
        try:
            mission = Mission.objects.get(peyk_id=request.peyk_id, status=0)
            device_id = request.headers['device-id']
            return JsonResponse({"version": "1", 'mission': MissionSchema().dump(mission)})
        except (AttributeError, Mission.DoesNotExist):
            return JsonResponse({"version": "1"})
        except KeyError:
            return JsonResponse({}, status=403)


class Signup(Validation):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        phone = self.valid_phone(data['phone'])
        password = data['password']
        vehicle = data['vehicle']
        activation_code = random.randint(1000, 9999)
        activation_code_salted = make_password(activation_code, f'{activation_code}' + SALT)
        activation_expire = self.add_minutes(5)
        try:
            user = Peyk.objects.get(phone=phone, verified=False)
            user.password = make_password(password, password + SALT)
            user.activation_code = activation_code_salted
            user.activation_expire = activation_expire
            user.device_id = request.headers['device-id']
            user.vehicle = vehicle
            user.save()
            #todo send sms
            return JsonResponse({'message': activation_code})
        except Peyk.DoesNotExist:
            return JsonResponse({'message': 'Unauthorized'}, status=401)


class ResendActivate(Validation):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        phone = self.valid_phone(data['phone'])
        device_id = request.headers['device-id']
        activation_code = random.randint(1000, 9999)
        activation_code_salted = make_password(activation_code, f'{activation_code}' + SALT)
        activation_expire = self.add_minutes(5)
        try:
            user = Peyk.objects.get(phone=phone, device_id=device_id)
            assert timezone.now() < user.activation_expire
            user.activation_code = activation_code_salted
            user.activation_expire = activation_expire
            user.save()
            # todo send sms
            return JsonResponse({'message': activation_code})
        except Peyk.DoesNotExist:
            return JsonResponse({'message': 'Unauthorized'}, status=401)
        except AssertionError:
            return JsonResponse({'message': 'دسترسی غیر مجاز'}, status=403)


class Activate(View):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        # todo get csrf code
        code = data['code']
        try:
            user = Peyk.objects.get(activation_code=make_password(code, f'{code}' + SALT),
                                    activation_expire__gte=timezone.now())
            user.activation_code = timezone.now()
            user.activation_expire = timezone.now()
            user.verified = True
            user.access_token = self.generate_token(request, user)
            user.save()
            return JsonResponse({'message': 'ok', 'access_token': user.access_token})
        except Peyk.DoesNotExist:
            return JsonResponse({'message': 'code not found'}, status=406)

    @pysnooper.snoop()
    def generate_token(self, request, user):
        data = {'user': PeykSchema().dump(user)}
        first_encrypt = jwt.encode(data, TOKEN_SECRET, algorithm='HS256')
        secret = token_hex(10)
        second_encrypt = jwt.encode({'data': first_encrypt.decode()}, secret, algorithm='HS256')
        access_token = f'{second_encrypt.decode()}{secret}'
        request.session['counter'] = 0
        return 'Bearer ' + access_token


class Login(Validation):
    def post(self, request):
        data = json.loads(request.body)
        password = data['password']
        activation_code = random.randint(1000, 9999)
        activation_code_salted = make_password(activation_code, f'{activation_code}' + SALT)
        activation_expire = self.add_minutes(5)
        try:
            peyk = Peyk.objects.get(phone=data['phone'], password=make_password(password, password + SALT),
                                    verified=True)
            peyk.activation_code = activation_code_salted
            peyk.activation_expire = activation_expire
            peyk.device_id = request.headers['device-id']
            peyk.save()
            # todo send sms
            return JsonResponse({'message': activation_code})
        except Peyk.DoesNotExist:
            return JsonResponse({'message': 'Unauthorized'}, status=401)


class AddMission(View):
    def post(self, request):
        data = json.loads(request.body)
        customer = 'علی بابایی'
        customer_number = '09015518585'
        customer_address = 'رشت'
        try:
            assert not Mission.objects.filter(peyk_id=request.peyk_id, status=0)
            Mission(customer=customer, phone=customer_number, address=customer_address,
                    peyk_id=request.peyk_id, factor_number=data['number']).save()
        except IntegrityError:
            return JsonResponse({'message': 'duplicate factor number'}, status=403)
        except AssertionError:
            return JsonResponse({'message': 'شما یک ماموریت فعل دارید'}, status=400)
        missions = Mission.objects.filter(peyk=request.peyk_id)
        return JsonResponse({'missions': MissionSchema().dump(missions, many=True)})


class GetMission(View):
    def get(self, request):
        missions = Mission.objects.filter(peyk_id=request.peyk_id)
        return JsonResponse({'missions': MissionSchema().dump(missions, many=True)})


class StartMission(View):
    @pysnooper.snoop()
    def post(self, request):
        data = json.loads(request.body)
        mission_id = data['id']
        try:
            peyk = Peyk.objects.get(pk=request.peyk_id)
            assert not peyk.active
            mission = Mission.objects.get(pk=mission_id, peyk=peyk, status=1)
            mission.status = 0
            mission.save()
            peyk.active = True
            peyk.save()
            return JsonResponse({"message": "ماموریت شروع شد"})
        except AssertionError:
            return JsonResponse({'message': 'شما یک ماموریت فعال دارید'}, status=403)
        except Mission.DoesNotExist:
            try:
                assert not Mission.objects.get(pk=mission_id, status=1)
                return JsonResponse({"message": "ماموریت پیدا نشد"}, status=404)
            except AssertionError:
                return JsonResponse({"message": "ماموریت فعال است"}, status=404)
            except Exception:
                return JsonResponse({"message": "ماموریت در دسترس نیست"}, status=404)
        except Exception:
            return JsonResponse({"message": "مشکلی رخ داده"}, status=401)


class UpdateLocation(View):
    def post(self, request):
        data = json.loads(request.body)
        mission_id = data['id']
        longitude = data['longitude']
        latitude = data['latitude']
        try:
            assert Mission.objects.filter(pk=mission_id, status=0, peyk_id=request.peyk_id).exists()
            Location(mission_id=mission_id, point=[longitude, latitude]).save()
            return JsonResponse({"message": "Location updated"})
        except AssertionError:
            return JsonResponse({"message": "mission finished"}, status=403)
        except Exception as e:
            print(e)
            return JsonResponse({"message": "can not update location"}, status=406)


class EndMission(View):
    def post(self, request):
        data = json.loads(request.body)
        mission_id = data['id']
        try:
            peyk = Peyk.objects.get(pk=request.peyk_id)
            mission = Mission.objects.get(pk=mission_id, peyk_id=request.peyk_id, status=0)
            mission.status = 2
            mission.save()
            peyk.active = False
            peyk.save()
            return JsonResponse({"message": "ماموریت پایان یافت"})
        except Mission.DoesNotExist:
            return JsonResponse({"message": "ماموریت پیدا نشد"}, status=404)


class GetLocation(View):
    def get(self, request, factor):
        try:
            mission = Mission.objects.get(factor_number=factor)
            assert mission.status == 2
            location = Location.objects.filter(mission=mission).order_by('created_at').last()
            return JsonResponse({'lang': location.point[0], 'lat': location.point[1]})
        except Location.DoesNotExist:
            return JsonResponse({'message': 'no location'}, status=204)
        except AssertionError:
            return JsonResponse({'message': 'mission ended'}, status=202)
        except Exception:
            return JsonResponse({}, status=400)


class GetActiveLocations(View):
    def get(self, request):
        try:
            mission = Mission.objects.filter(status=0)
            location = Location.objects.filter(mission__in=mission).select_related('mission').distinct('mission')
            # return JsonResponse({'lang': location.point[0], 'lat': location.point[1]})
            return JsonResponse({'locations': LocationSchema().dump(location, many=True)})
        except Exception:
            return JsonResponse({}, status=400)
