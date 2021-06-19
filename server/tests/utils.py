import json
import logging

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, Client as TestClient

from .models import *

logger = logging.getLogger(__name__)


def fake_json():
    return {"fa": fake.name(), "en": ""}


def base_request(request, route, class_name, user, html, status_range, page=1, step=10, **kwargs):
    request.lang = 'fa'
    request.page = page
    request.step = step
    request.all = False
    request.user_agent = fake_agent()
    request.schema_params = {}
    request.user = user
    if user is None:
        request.user = AnonymousUser()
    res = class_name.as_view()(request, **kwargs)
    assert status_range[0] <= res.status_code <= status_range[1], (print(res), f"{class_name} has issue in /{route}")
    if html is False:
        res = json.loads(res.content)
    print(res)
    return res


def get(route, class_name, user=mixer.blend(User), html=False, status_range=(200, 299), page=1, step=10, **kwargs):
    factory = RequestFactory()
    request = factory.get(f'/{route}')
    return base_request(request, route, class_name, user, html, status_range, page, step, **kwargs)


def post(route, data, class_name, user=mixer.blend(User), html=False, status_range=(200, 299), headers=None, **kwargs):
    factory = RequestFactory()
    if not headers:
        headers = {}
    print(headers)
    print(kwargs)
    print(data)
    request = factory.post(f'/{route}', data, **headers)
    return base_request(request, route, class_name, user, html, status_range, **kwargs)
