import json
import logging

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from .models import *

logger = logging.getLogger(__name__)


def fake_json():
    return {"fa": fake.name(), "en": ""}


def get(route):
    user = fake_user(is_superuser=False, is_active=False)
    factory = RequestFactory()

    request = factory.get(route)
    request = attach_request_default_attr(request, user)
    return request


def post(route, data=None):
    user = fake_user(is_superuser=False, is_active=False)
    factory = RequestFactory()

    request = factory.post(route, data, content_type='application/json')
    request = attach_request_default_attr(request, user)
    return request


def attach_request_default_attr(request, user, page=1, step=18):
    request.lang = 'fa'
    request.page = page
    request.step = step
    request.all = False
    request.user_agent = fake_desktop_agent()
    request.schema_params = {}
    request.user = user
    request.user.basket_count = 0
    if user is None:
        request.user = AnonymousUser()
    return request


def base_request(request, route, class_name, user, html, status_range, page=1, step=10, **kwargs):
    request.lang = 'fa'
    request.page = page
    request.step = step
    request.all = False
    request.user_agent = fake_desktop_agent()
    request.schema_params = {}
    request.user = user
    request.user.basket_count = 0
    if user is None:
        request.user = AnonymousUser()
    res = class_name.as_view()(request, **kwargs)
    print(route, res.content)
    assert status_range[0] <= res.status_code <= status_range[1], print(res.content)
    if html is False:
        res = json.loads(res.content)
    print(res)
    return res

# def get(route, class_name, user=mixer.blend(User), html=False, status_range=(200, 299), page=1, step=10, **kwargs):
#     factory = RequestFactory()
#     request = factory.get(f'/{route}')
#     return base_request(request, route, class_name, user, html, status_range, page, step, **kwargs)
#
#
# def post(route, data, class_name, user=mixer.blend(User), html=False, status_range=(200, 299), headers=None, **kwargs):
#     factory = RequestFactory()
#     if not headers:
#         headers = {}
#     print(headers)
#     print(kwargs)
#     print(data)
#     request = factory.post(f'/{route}', data, **headers)
#     return base_request(request, route, class_name, user, html, status_range, **kwargs)
#
#
# def patch(route, data, class_name, user=mixer.blend(User), html=False, status_range=(200, 299), headers=None, **kwargs):
#     factory = RequestFactory()
#     if not headers:
#         headers = {}
#     print(headers)
#     print(kwargs)
#     print(data)
#     request = factory.patch(f'/{route}', data, **headers)
#     return base_request(request, route, class_name, user, html, status_range, **kwargs)
