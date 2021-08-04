from django.core.files.uploadedfile import SimpleUploadedFile
from faker import Faker
from mixer.backend.django import Mixer

from server.models import *

fake = Faker('fa_IR')
mixer = Mixer(commit=True)


def clean_return_data(data, count):
    if data and count == 1:
        return data[0]
    return data


def fake_json():
    return {"fa": fake.name(), "en": "", "data": ""}


def fake_settings():
    return {"ui": {}}


def fake_mobile_agent():
    device = type('Device', (), {'family': 'Samsung', })()
    return type('UserAgent', (), {'is_mobile': True, 'device': device})()


def fake_desktop_agent():
    device = type('Device', (), {'family': 'Samsung', })()
    return type('UserAgent', (), {'is_mobile': False, 'device': device})()


def fake_phone_number():
    return fake.phone_number().replace(' ', '').replace('+98', '0')


def fake_ad(**kwargs):
    return mixer.blend(Ad, title=fake_json(), url=fake.url(), media=fake_media(media_type=5),
                       mobile_media=fake_media(media_type=6), storage=fake_storage(), **kwargs)


def fake_address(user=None, **kwargs):
    state = fake_state()
    city = fake_city(state=state)
    location = fake.location_on_land()[:2]
    return mixer.blend(Address, user=user, location={'lat': location[0], 'lng': location[1]}, city=city, state=state, **kwargs)


def fake_box(**kwargs):
    return mixer.blend(Box, name=fake_json(), settings=fake_settings(), disable=False, media=fake_media(7), **kwargs)


def fake_basket(**kwargs):
    return mixer.blend(Basket, **kwargs)


def fake_brand(**kwargs):
    return mixer.blend(Brand, name=fake_json(), **kwargs)


def fake_category(**kwargs):
    return mixer.blend(Category, name=fake_json(), disable=False, permalink=fake.password(), **kwargs)


def fake_comment(comment_type='rate', comment=None, **kwargs):
    product = fake_product(null=False)
    if comment_type == 'q-a':
        return mixer.blend(Comment, text=fake.text(), approved=fake.boolean(), type=1,
                           reply_to=comment, product=product, **kwargs)
    return mixer.blend(Comment, text=fake.text(), approved=fake.boolean(), type=2,
                       reply_to=comment, rate=fake.random_int(0, 10), product=product, **kwargs)


def fake_client(**kwargs):
    return mixer.blend(Client, name=fake_json(), **kwargs)


def fake_charity(**kwargs):
    return mixer.blend(Charity, name=fake_json(), deposit_id=1, **kwargs)


def fake_city(state=None, **kwargs):
    return mixer.blend(City, name=fake.city(), state=state, **kwargs)


def fake_discount_code(**kwargs):
    user = fake_user()
    invoice = fake_invoice()
    return mixer.blend(DiscountCode, created_by=user, storage=fake_storage(), invoice=invoice, type=3, **kwargs)  # post


def fake_feature(**kwargs):
    return mixer.blend(Feature, **kwargs)


def fake_feature_value(**kwargs):
    return mixer.blend(FeatureValue, **kwargs)


def fake_feature_group(**kwargs):
    return mixer.blend(FeatureGroup, **kwargs)


def fake_invoice(**kwargs):
    basket = fake_basket()
    sync_task = mixer.blend(PeriodicTask)
    invoice = mixer.blend(Invoice, basket=basket, sync_task=sync_task, **kwargs)
    invoice.invoice_storages.set(fake_invoice_storage(5, invoice=invoice))
    return invoice


def fake_invoice_storage(count=1, **kwargs):
    invoice_storages = []
    for i in range(count):
        product = fake_product()
        storage = fake_storage(product=product)
        invoice_storages.append(mixer.blend(InvoiceStorage, details=fake_json(), features=fake_json(),
                                            storage=storage, **kwargs))

    return invoice_storages


def fake_media(media_type, **kwargs):
    file_name = next(item for item in Media.types if item[0] == media_type)[1]
    image_path = f"{MEDIA_ROOT}\\test\\{file_name}.jpg"
    image = SimpleUploadedFile(name='test_image.jpg', content=open(image_path, 'rb').read(),
                               content_type='image/jpeg')
    return mixer.blend(Media, title=fake_json(), image=image, type=media_type, **kwargs)


def fake_menu(**kwargs):
    return mixer.blend(Menu, **kwargs)


def fake_product(**kwargs):
    review = {
        "chats": [{"id": 1, "text": "مشکل دارد", "user_id": 1, "question": True, "created_at": 1605884953},
                  {"id": 2, "text": "بشو رررررر", "user_id": 1, "question": False, "created_at": 1605967167},
                  {"id": 3, "text": "ایراد دارد", "user_id": 1, "question": True, "created_at": 1605967731},
                  {"id": 4, "text": "میگم نداره", "user_id": 1, "question": False, "created_at": 1605967777},
                  {"id": 5, "text": "وابدن", "user_id": 1, "question": False, "created_at": 1605967907}],
        "state": "reviewed"}
    thumbnail = fake_media(2)
    location = fake.location_on_land()[:2]
    return mixer.blend(Product, brand=fake_brand(), thumbnail=thumbnail, disable=False,
                       location={'lat': location[0], 'lng': location[1]}, address=fake.address,
                       properties=fake_json(), name=fake_json(), description=fake_json(),
                       short_address=fake.address, details=fake_json(), settings=fake_settings(),
                       review=review, **kwargs)


def fake_payment_history(**kwargs):
    return mixer.blend(PaymentHistory, **kwargs)


def fake_slider(**kwargs):
    return mixer.blend(Slider, title=fake_json(), product=fake_product(), media=fake_media(4),
                       mobile_media=fake_media(8), type='home', url=fake.url, priority=0, **kwargs)


def fake_special_product(**kwargs):
    return mixer.blend(SpecialProduct, storage=fake_storage(null=False), thumbnail=fake_media(2), box=fake_box(),
                       url=fake.url(), name=fake_json(), **kwargs)


def fake_storage(**kwargs):
    supplier = fake_user(is_verify=True)
    return mixer.blend(Storage, title=fake_json(), disable=False, available_count=100,
                       available_count_for_sale=100, start_price=1000, discount_price=2000,
                       final_price=3000, shipping_cost=1000, max_count_for_sale=5, tax_type=1,
                       deadline=None, supplier=supplier, media=fake_media(2),
                       dimensions={'weight': 10, 'height': 10, 'width': 10, 'length': 10}, **kwargs)


def fake_state(**kwargs):
    return mixer.blend(State, name=fake.state(), **kwargs)


def fake_tag(**kwargs):
    return mixer.blend(Tag, **kwargs)


def fake_tag_group(**kwargs):
    return mixer.blend(TagGroup, name=fake_json(), **kwargs)


def fake_vip_type(**kwargs):
    return mixer.blend(VipType, **kwargs)


def fake_user(**kwargs):
    return mixer.blend(User, tg_id=fake.random_int(), tg_username=fake.name(),
                       tg_first_name=fake.name()
                       , avatar=fake.url(), first_name=fake.first_name(),
                       last_name=fake.last_name(),
                       default_address=fake_address(), **kwargs)


def fake_wishlist(**kwargs):
    return mixer.blend(WishList, **kwargs)
