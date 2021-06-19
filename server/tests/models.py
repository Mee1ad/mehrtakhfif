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
    return {"fa": fake.name(), "en": ""}


def fake_settings():
    return {"ui": {}}


def fake_agent(is_mobile=False):
    device = type('Device', (), {'family': 'Samsung', })()
    if is_mobile:
        return type('UserAgent', (), {'is_mobile': True, 'device': device})()
    return type('UserAgent', (), {'is_mobile': False, 'device': device})()


def fake_ad(count=1, null=True, **kwargs):
    if null:
        obj = mixer.cycle(count).blend(Ad, **kwargs)
    else:
        obj = mixer.cycle(count).blend(Ad, title=fake_json(), url=fake.url(), media=fake_media(media_type=5),
                                       mobile_media=fake_media(media_type=6), storage=fake_storage(), **kwargs)
    return clean_return_data(obj, count)


def fake_address(count=1, null=True, user=None, **kwargs):
    state = fake_state()
    city = fake_city(state=state)
    if null:
        obj = mixer.cycle(count).blend(Address, city=city, state=state, **kwargs)
    else:
        obj = mixer.cycle(count).blend(Address, user=user, location=fake.location_on_land()[:2], city=city,
                                       state=state, **kwargs)
    return clean_return_data(obj, count)


def fake_box(count=1, null=True, **kwargs):
    if null:
        obj = mixer.cycle(count).blend(Box, name=fake_json(), settings=fake_settings(), disable=False, **kwargs)
    else:
        obj = mixer.cycle(count).blend(Box, name=fake_json(), settings=fake_settings(), disable=False,
                                       media=fake_media(7), **kwargs)
    return clean_return_data(obj, count)


def fake_basket(**kwargs):
    return mixer.blend(Basket, **kwargs)


def fake_brand(count=1, **kwargs):
    obj = mixer.cycle(count).blend(Brand, name=fake_json(), **kwargs)
    return clean_return_data(obj, count)


def fake_category(count=1, null=True, **kwargs):
    categories = []
    for permalink in [fake.password() for i in range(count)]:
        if null:
            categories.append(mixer.blend(Category, name=fake_json(), disable=False, **kwargs))
        else:
            categories.append(mixer.blend(Category, name=fake_json(), settings=fake_settings(), disable=False,
                                          parent=fake_category(), permalink=permalink, **kwargs))

    return clean_return_data(categories, count)


def fake_comment(count=1, comment_type='rate', comment=None, **kwargs):
    product = fake_product(null=False)
    if comment_type == 'q-a':
        obj = mixer.cycle(count).blend(Comment, text=fake.text(), approved=fake.boolean(), type=1,
                                       reply_to=comment, product=product, **kwargs)
        return clean_return_data(obj, count)
    obj = mixer.cycle(count).blend(Comment, text=fake.text(), approved=fake.boolean(), type=2,
                                   reply_to=comment, rate=fake.random_int(0, 10), product=product, **kwargs)
    return clean_return_data(obj, count)


def fake_client(count=1, **kwargs):
    obj = mixer.cycle(count).blend(Client, name=fake_json(), **kwargs)
    return clean_return_data(obj, count)


def fake_charity(count=1, **kwargs):
    obj = mixer.cycle(count).blend(Charity, name=fake_json(), deposit_id=1, **kwargs)
    return clean_return_data(obj, count)


def fake_city(count=1, state=None, **kwargs):
    obj = mixer.cycle(count).blend(City, name=fake.city(), state=state, **kwargs)
    return clean_return_data(obj, count)


def fake_discount_code(count=1, null=True, **kwargs):
    if null:
        obj = mixer.cycle(count).blend(DiscountCode, type=3, **kwargs)
    else:
        user = fake_user()
        invoice = fake_invoice()
        obj = mixer.cycle(count).blend(DiscountCode, user=user, storage=fake_storage(), invoice=invoice,
                                       invoice_storage=invoice.invoice_storages.all()[0].id,
                                       basket=fake_basket(user=user), type=3, **kwargs)  # post
    return clean_return_data(obj, count)


def fake_feature(count=1, **kwargs):
    obj = mixer.cycle(count).blend(Feature, **kwargs)
    return clean_return_data(obj, count)


def fake_feature_group(count=1, **kwargs):
    obj = mixer.cycle(count).blend(FeatureGroup, **kwargs)
    return clean_return_data(obj, count)


def fake_invoice(**kwargs):
    invoice = mixer.blend(Invoice, **kwargs)
    invoice.invoice_storages.set(fake_invoice_storage(5))
    return invoice


def fake_invoice_storage(count=1, **kwargs):
    return mixer.cycle(count).blend(InvoiceStorage, details=fake_json(), features=fake_json(), **kwargs)


def fake_media(media_type, count=1, null=True, **kwargs):
    file_name = next(item for item in Media.types if item[0] == media_type)[1]
    image_path = f"{MEDIA_ROOT}\\test\\{file_name}.jpg"
    image = SimpleUploadedFile(name='test_image.jpg', content=open(image_path, 'rb').read(),
                               content_type='image/jpeg')
    if null:
        obj = mixer.cycle(count).blend(Media, title=fake_json(), image=image, type=media_type, **kwargs)
    else:
        box = fake_box()
        obj = mixer.cycle(count).blend(Media, title=fake_json(), image=image, box=box, type=media_type, **kwargs)
    return clean_return_data(obj, count)


def fake_menu(count=1, **kwargs):
    return mixer.cycle(count).blend(Menu, **kwargs)


def fake_product(count=1, null=False, **kwargs):
    products = []
    if null:
        products = mixer.cycle(count).blend(Product, disable=False, **kwargs)
    else:
        review = {
            "chats": [{"id": 1, "text": "مشکل دارد", "user_id": 1, "question": True, "created_at": 1605884953},
                      {"id": 2, "text": "بشو رررررر", "user_id": 1, "question": False, "created_at": 1605967167},
                      {"id": 3, "text": "ایراد دارد", "user_id": 1, "question": True, "created_at": 1605967731},
                      {"id": 4, "text": "میگم نداره", "user_id": 1, "question": False, "created_at": 1605967777},
                      {"id": 5, "text": "وابدن", "user_id": 1, "question": False, "created_at": 1605967907}],
            "state": "reviewed"}
        thumbnail = fake_media(2)
        obj = None
        for storage in fake_storage(count):
            products.append(mixer.blend(Product, brand=fake_brand(), thumbnail=thumbnail,
                                        default_storage=storage, disable=False,
                                        location=fake.location_on_land()[:2], address=fake.address,
                                        properties=fake_json(),
                                        short_address=fake.address, details=fake_json(), settings=fake_settings(),
                                        review=review, **kwargs))
    return clean_return_data(products, count)


def fake_slider(count=1, **kwargs):
    return mixer.cycle(count).blend(Slider, title=fake_json(), product=fake_product(), media=fake_media(4),
                                    mobile_media=fake_media(8), type='home', url=fake.url, priority=0, **kwargs)


def fake_special_product(count=1, null=False, **kwargs):
    if null:
        obj = mixer.blend(SpecialProduct, storage=fake_storage(null=False)).__dict__
    else:
        obj = mixer.blend(SpecialProduct, storage=fake_storage(null=False), thumbnail=fake_media(2), box=fake_box(),
                          url=fake.url(), name=fake_json()).__dict__
    return clean_return_data(obj, count)


def fake_storage(count=1, null=True, **kwargs):
    if null:
        obj = mixer.cycle(count).blend(Storage, title=fake_json(), disable=False, **kwargs)
    else:
        supplier = fake_user(is_verify=True)
        obj = mixer.cycle(count).blend(Storage, title=fake_json(), disable=False, available_count=100,
                                       available_count_for_sale=100, start_price=1000, discount_price=2000,
                                       final_price=3000, shipping_cost=1000, max_count_for_sale=5, tax_type=1,
                                       deadline=None, supplier=supplier, media=fake_media(2),
                                       dimensions={'weight': 10, 'height': 10, 'width': 10, 'length': 10}, **kwargs)
    return clean_return_data(obj, count)


def fake_state(count=1, **kwargs):
    obj = mixer.cycle(count).blend(State, name=fake.state(), **kwargs)
    return clean_return_data(obj, count)


def fake_tag(count=1, **kwargs):
    obj = mixer.cycle(count).blend(Tag, **kwargs)
    return clean_return_data(obj, count)


def fake_tag_group(count=1, **kwargs):
    obj = mixer.cycle(count).blend(TagGroup, name=fake_json(), **kwargs)
    return clean_return_data(obj, count)


def fake_vip_type(count=1, **kwargs):
    obj = mixer.cycle(count).blend(VipType, **kwargs)
    return clean_return_data(obj, count)


def fake_user(count=1, null=True, **kwargs):
    if null:
        obj = mixer.cycle(count).blend(User, **kwargs)
    else:
        obj = mixer.cycle(count).blend(User, tg_id=fake.random_int(), tg_username=fake.name(),
                                       tg_first_name=fake.name()
                                       , avatar=fake.url(), first_name=fake.first_name(),
                                       last_name=fake.last_name(),
                                       default_address=fake_address(), **kwargs)
    return clean_return_data(obj, count)


def fake_wishlist(count=1, null=True, **kwargs):
    obj = mixer.cycle(count).blend(WishList, **kwargs)
    return clean_return_data(obj, count)
