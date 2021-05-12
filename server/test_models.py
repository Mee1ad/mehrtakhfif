from django.core.files.uploadedfile import SimpleUploadedFile
from faker import Faker
from mixer.backend.django import Mixer

from server.models import *

fake = Faker('fa_IR')
mixer = Mixer(commit=True)


def clean_return_data(data, count):
    if count == 1:
        return data[0]
    return data


def fake_json():
    return {"fa": fake.name(), "en": ""}


def fake_settings():
    return {"ui": {}}


def fake_box(count=1, null=True):
    if null:
        obj = mixer.cycle(count).blend(Box, name=fake_json(), settings=fake_settings(), disable=False)
    else:
        obj = mixer.cycle(count).blend(Box, name=fake_json(), settings=fake_settings(), disable=False,
                                       media=fake_media())
    return clean_return_data(obj, count)


def fake_brand(count=1):
    obj = mixer.cycle(count).blend(Brand, name=fake_json())
    return clean_return_data(obj, count)


def fake_media(count=1, null=True):
    image_path = f"{MEDIA_ROOT}\\icon.png"
    image = SimpleUploadedFile(name='test_image.jpg', content=open(image_path, 'rb').read(), content_type='image/jpeg')
    if null:
        obj = mixer.cycle(count).blend(Media, title=fake_json(), image=image)
    else:
        box = fake_box()
        obj = mixer.cycle(count).blend(Media, title=fake_json(), image=image, box=box)
    return clean_return_data(obj, count)


def fake_product(count=1, null=False):
    if null:
        obj = mixer.cycle(count).blend(Product, disable=False)
    else:
        review = {"chats": [{"id": 1, "text": "مشکل دارد", "user_id": 1, "question": True, "created_at": 1605884953},
                            {"id": 2, "text": "بشو رررررر", "user_id": 1, "question": False, "created_at": 1605967167},
                            {"id": 3, "text": "ایراد دارد", "user_id": 1, "question": True, "created_at": 1605967731},
                            {"id": 4, "text": "میگم نداره", "user_id": 1, "question": False, "created_at": 1605967777},
                            {"id": 5, "text": "وابدن", "user_id": 1, "question": False, "created_at": 1605967907}],
                  "state": "reviewed"}
        thumbnail = fake_media()
        obj = mixer.cycle(count).blend(Product, brand=fake_brand(), thumbnail=thumbnail,
                                       default_storage=default_storage,
                                       location=fake.location_on_land()[:2], address=fake.address,
                                       properties=fake_json(),
                                       short_address=fake.address, details=fake_json(), settings=fake_settings(),
                                       review=review)
    return clean_return_data(obj, count)


def fake_slider():
    return mixer.cycle(5).blend(Slider, title=fake_json(), product=product, media=media, mobile_media=mobile_media,
                                type='home', url=fake.url, priority=0)


def fake_storage(count=1, null=True):
    if null:
        obj = mixer.cycle(count).blend(Storage, title=fake_json(), disable=False)
    else:
        obj = mixer.cycle(count).blend(Storage, title=fake_json(), disable=False, available_count=100,
                                       available_count_for_sale=100, start_price=1000, discount_price=2000,
                                       final_price=3000, shipping_cost=1000, max_count_for_sale=5, tax_type=1,
                                       deadline=fake.date_time())
    return clean_return_data(obj, count)
