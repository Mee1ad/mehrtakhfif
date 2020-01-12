from marshmallow import Schema, fields
from mehr_takhfif.settings import HOST, MEDIA_URL
import pysnooper
from secrets import token_hex
from datetime import date
from django.utils import timezone
from server.models import BasketProduct, FeatureStorage, CostumeHousePrice, Book
import time

lst = []


def list_view(obj_list):
    for obj in obj_list:
        if type(obj) == list:
            lst.append([list_view(obj)])
        else:
            try:
                lst.append(obj.name)
            except AttributeError:
                lst.append(obj.title)


def related_objects(objects):
    res = []
    for item in objects:
        if type(item) == list:
            related_objects(item)
            continue
        item = {'model': item.__class__.__name__, 'data': item}
        res.append(item)
    return res
