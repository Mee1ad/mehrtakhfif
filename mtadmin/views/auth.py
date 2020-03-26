from django.http import JsonResponse
from django.db.models import Q
from server.views.auth import Login
from django.contrib.auth import login

from server.utils import *
from mtadmin.serializer import *
from mtadmin.utils import AdminView


class AdminLogin(AdminView):
    def post(self, request):
        data = load_data(request)
        meli_code = data['meli_code']
        password = data['password']
        user = User.objects.get(Q(meli_code=meli_code), (Q(is_staff=True) | Q(is_superuser=True)))
        if user.is_ban:
            return JsonResponse({'message': 'user is banned'}, status=493)
        assert user.check_password(password)
        return set_token(user, Login.send_activation(user))


class AdminActivate(AdminView):
    def post(self, request):
        data = load_data(request)
        try:
            client_token = get_signed_cookie(request, 'token', False)
            code = data['code']
            user = User.objects.get(Q(activation_code=code, token=client_token, is_ban=False,
                                      activation_expire__gte=timezone.now()), (Q(is_staff=True) | Q(is_superuser=True)))
            user.activation_expire = timezone.now()
            user.is_active = True
            user.save()
            login(request, user)
            res = JsonResponse(UserSchema().dump(user), status=201)  # signup without password
            if Login.check_password(user):
                res = JsonResponse(UserSchema().dump(user))  # successful login
                res.delete_cookie('token')
            return res
        except Exception:
            return JsonResponse({'message': 'code not found'}, status=406)
