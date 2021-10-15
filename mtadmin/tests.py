import logging

from django.test import TestCase, RequestFactory, Client as TClient

from mehr_takhfif.settings import BASE_DIR
from mtadmin.views.tables import *
from server.tests.models import *
from mtadmin.views.views import *
from server.utils import res_code

#  todo add admin views
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# USE THIS

class PostModelTestCase(TestCase):
    def setUp(self):
        self.user = fake_user(is_superuser=True, is_active=True)
        self.factory = RequestFactory()
        self.headers = {"content_type": "application/json"}

    def make_request(self, route, data):
        request = self.factory.post(route, data, **self.headers)
        request.user = self.user
        return request

    def test_category(self):
        category = fake_category()
        media = fake_media(media_type=7)
        category = fake_category()
        data = {
            "parent_id": category.id,
            "name": fake_json(),
            "permalink": fake.uuid4(),
            "media_id": media.id
        }
        request = self.make_request('/admin/category', data)
        res = CategoryView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_brand(self):
        data = {
            "name": fake_json(),
            "permalink": fake.uuid4()
        }
        request = self.make_request('/admin/brand', data)
        res = BrandView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_menu(self):
        media = fake_media(media_type=4)
        category = fake_category()
        data = {
            "type": 1,
            "name": fake_json(),
            "media_id": media.id,
            "url": fake.url(),
            "parent_id": None,
            "category_id": category.id
        }
        request = self.make_request('/admin/menu', data)
        res = MenuView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_feature(self):
        feature_group = fake_feature_group()
        data = {
            "name": fake_json(),
            "groups": [
                feature_group.id
            ],
            "type": "text",
            "layout_type": "default",
            "values": [
                {
                    "value": fake_json(),
                    "settings": fake_json()
                },
                {
                    "value": fake_json(),
                    "settings": fake_json()
                },
                {
                    "value": fake_json(),
                    "settings": fake_json()
                }
            ]
        }
        request = self.make_request('/admin/feature', data)
        res = FeatureView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_feature_value(self):
        feature = fake_feature()
        data = {
            "value": fake_json(),
            "feature_id": feature.id
        }
        request = self.make_request('/admin/feature_value', data)
        res = FeatureValueView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_feature_group(self):
        category = fake_category()
        feature1 = fake_feature()
        feature2 = fake_feature()
        feature3 = fake_feature()
        data = {
            "name": fake_json(),
            "category_id": category.id,
            "settings": fake_settings(),
            "features": [
                feature1.id,
                feature2.id,
                feature3.id
            ]
        }
        request = self.make_request('/admin/feature_group', data)
        res = FeatureGroupView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_product(self):
        category = fake_category()
        brand = fake_brand()
        category1 = fake_category()
        category2 = fake_category()
        feature1 = fake_feature()
        feature2 = fake_feature()
        feature_value1 = mixer.blend(FeatureValue)
        feature_value2 = mixer.blend(FeatureValue)
        media1 = fake_media(media_type=3)
        media2 = fake_media(media_type=3)
        thumbnail = fake_media(media_type=2)
        tag1 = fake_tag()
        tag2 = fake_tag()
        tag_group1 = fake_tag_group()
        tag_group2 = fake_tag_group()

        data = {
            "category_id": category.id,
            "type": "service",
            "brand_id": brand.id,
            "categories": [
                category1.id,
                category2.id
            ],
            "features": [
                {
                    "feature_id": feature1.id,
                    "feature_value_id": feature_value1.id,
                    "settings": fake_settings()
                },
                {
                    "feature_id": feature2.id,
                    "feature_value_id": feature_value2.id,
                    "settings": fake_settings()
                }
            ],
            "review": {
                "chats": [],
                "state": "ready"
            },
            "description": fake_json(),
            "media": [
                media1.id,
                media2.id,
            ],
            "name": fake_json(),
            "permalink": fake.uuid4(),
            "settings": fake_settings(),
            "short_description": fake_json(),
            "tag_groups": [
                tag_group1.id,
                tag_group2.id
            ],
            "tags": [
                {
                    "tag_id": tag1.id,
                    "show": False
                },
                {
                    "tag_id": tag2.id,
                    "show": False
                }
            ],
            "thumbnail_id": thumbnail.id
        }
        request = self.make_request('/admin/product', data)
        res = ProductView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_tag(self):
        data = {
            "name": fake_json(),
        }
        request = self.make_request('/admin/tag', data)
        res = TagView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_discount_code(self):
        storage = fake_storage()
        data = {
            "storage_id": storage.id,
            "count": fake.random_int(1, 100),
            "len": fake.random_int(1, 10),
            "prefix": fake.name()
        }

        request = self.make_request('/amin/discount_code', data)
        res = DiscountCodeView.as_view()(request)
        self.assertEqual(res.status_code, 201, res)

    def test_storage(self):
        product = fake_product()
        product_feature = mixer.blend(ProductFeature, product=product)
        supplier = fake_user(is_supplier=True)
        vip_price1 = mixer.blend(VipPrice)
        vip_price2 = mixer.blend(VipPrice)
        accessory_product1 = fake_product()
        accessory_storage1 = fake_storage(product=accessory_product1)
        accessory_product2 = fake_product()
        accessory_storage2 = fake_storage(product=accessory_product2)
        package_item1 = fake_storage()
        package_item2 = fake_storage()
        data = {
            "available_count": 100,
            "available_count_for_sale": 100,
            "deadline": None,
            "dimensions": {
                "weight": 10,
                "height": 10,
                "length": 10,
                "width": 10
            },
            "start_price": 5000,
            "discount_price": 10000,
            "final_price": 20000,
            "features": [
                {
                    "product_feature_id": product_feature.id,
                    "extra_data": fake_settings()
                }
            ],
            "invoice_description": fake_json(),
            "invoice_title": fake_json(),
            "max_count_for_sale": 10,
            "min_count_alert": 3,
            "product_id": product.id,
            "shipping_cost": 0,
            'items': [
                {'package_item_id': package_item1.id, 'count': 5},
                {'package_item_id': package_item2.id, 'count': 10}
            ],
            "start_time": 1591004832,
            "supplier_id": supplier.id,
            "tax_type": "has_not",
            "title": fake_json(),
            "vip_prices": [
                {'vip_type_id': vip_price1.vip_type_id, 'discount_price': vip_price1.discount_price,
                 'max_count_for_sale': vip_price1.max_count_for_sale,
                 'available_count_for_sale': vip_price1.available_count_for_sale},
                {'vip_type_id': vip_price2.vip_type_id, 'discount_price': vip_price2.discount_price,
                 'max_count_for_sale': vip_price2.max_count_for_sale,
                 'available_count_for_sale': vip_price2.available_count_for_sale}
            ],
            "accessories": [
                {
                    "accessory_product_id": accessory_product1.id,
                    "accessory_storage_id": accessory_storage1.id,
                    "discount_price": 2000
                },
                {
                    "accessory_product_id": accessory_product2.id,
                    "accessory_storage_id": accessory_storage2.id,
                    "discount_price": 3000
                }
            ]
        }
        request = self.make_request('/admin/storage', data)
        res = StorageView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_package(self):
        pass
        # todo

    def test_vip_price(self):
        pass
        # todo

    def test_tag_group(self):
        category = fake_category()
        tag1 = fake_tag()
        tag2 = fake_tag()
        tag3 = fake_tag()
        data = {
            "name": fake_json(),
            "category_id": category.id,
            "tags": [
                tag1.id,
                tag2.id,
                tag3.id
            ]
        }
        request = self.make_request('/admin/tag_group', data)
        res = TagGroupView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_special_offer(self):
        pass
        # todo

    def test_special_product(self):
        pass
        # todo

    def test_media(self):
        category = fake_category()
        file = BASE_DIR + '/media/test/media.jpg'

        self.headers = {"content_type": "multipart/form-data"}
        c = TClient()
        with open(file) as fp:
            data = {
                "category_id": category.id,
                "type": 3,
                "titles": [fake_json(), fake_json()],
                "file": fp
            }
        # todo
        pass

    def test_ad(self):
        pass

        # todo

    def test_slider(self):
        pass
        # todo

    def test_supplier(self):
        data = {
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "username": fake.phone_number().replace(' ', '').replace('+98', '09')[:11],
            "shaba": "IR123456789",
            "meli_code": fake.ssn().replace('-', ''),
            "settings": fake_json()
        }
        request = self.make_request('/admin/supplier', data)
        res = SupplierView.as_view()(request)
        self.assertEqual(res.status_code, 201, f"can't create")

    def test_review_price(self):
        category = fake_category(settings={"share": 0.32})
        data = {
            "category_id": category.id,
            "tax_type": "has_not",
            "discount_price": 5000,
            "start_price": 0,
            "final_price": 10000,
            "shipping_cost": 1000
        }
        request = self.make_request('/admin/review_price', data)
        res = ReviewPrice.as_view()(request)
        self.assertEqual(res.status_code, 200, f"can't create")


class PutModelTestCase(TestCase):
    def setUp(self):
        self.user = fake_user(is_superuser=True, is_active=True)
        self.category = fake_category()
        self.factory = RequestFactory()
        self.headers = {"content_type": "application/json"}

    def make_request(self, route, data):
        request = self.factory.put(route, data, **self.headers)
        request.user = self.user
        return request

    def test_category(self):
        media = fake_media(media_type=7)
        category1 = fake_category()
        category2 = fake_category()
        data = {
            "id": category1.id,
            "parent_id": category2.id,
            "name": fake_json(),
            "permalink": fake.uuid4(),
            "media_id": media.id
        }
        request = self.make_request('/admin/category', data)
        res = CategoryView.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")

    def test_brand(self):
        brand = fake_brand()
        data = {
            "id": brand.id,
            "name": fake_json(),
            "permalink": fake.uuid4()
        }
        request = self.make_request('/admin/brand', data)
        res = BrandView.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")

    def test_menu(self):
        media = fake_media(media_type=4)
        menu = mixer.blend(Menu, category=self.category)
        data = {
            "id": menu.id,
            "type": 1,
            "name": fake_json(),
            "media_id": media.id,
            "url": fake.url(),
            "parent_id": None,
            "category_id": self.category.id
        }
        request = self.make_request('/admin/menu', data)
        res = MenuView.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")

    def test_feature(self):
        feature_group = fake_feature_group()
        feature = fake_feature()
        data = {
            "id": feature.id,
            "name": fake_json(),
            "groups": [
                feature_group.id
            ],
            "type": "text",
            "layout_type": "default",
            "values": [
                {
                    "value": fake_json(),
                    "settings": fake_json()
                },
                {
                    "value": fake_json(),
                    "settings": fake_json()
                },
                {
                    "value": fake_json(),
                    "settings": fake_json()
                }
            ]
        }
        request = self.make_request('/admin/feature', data)
        res = FeatureView.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")

    def test_feature_value(self):
        feature = fake_feature()
        feature_value = fake_feature_value()
        data = {
            "id": feature_value.id,
            "value": fake_json(),
            "feature_id": feature.id
        }
        request = self.make_request('/admin/feature_value', data)
        res = FeatureValueView.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")

    def test_feature_group(self):
        feature1 = fake_feature()
        feature2 = fake_feature()
        feature3 = fake_feature()
        feature_group = fake_feature_group()
        data = {
            "id": feature_group.id,
            "name": fake_json(),
            "category_id": self.category.id,
            "settings": fake_settings(),
            "features": [
                feature1.id,
                feature2.id,
                feature3.id
            ]
        }
        request = self.make_request('/admin/feature_group', data)
        res = FeatureGroupView.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")

    def test_product(self):
        # todo test activation warnings
        brand = fake_brand()
        category1 = fake_category()
        category2 = fake_category()
        feature1 = fake_feature()
        feature2 = fake_feature()
        feature_value1 = mixer.blend(FeatureValue)
        feature_value2 = mixer.blend(FeatureValue)
        media1 = fake_media(media_type=3)
        media2 = fake_media(media_type=3)
        thumbnail = fake_media(media_type=2)
        tag1 = fake_tag()
        tag2 = fake_tag()
        tag_group1 = fake_tag_group()
        tag_group2 = fake_tag_group()
        default_storage = fake_storage()
        product = default_storage.product
        data = {
            "id": product.id,
            "category_id": self.category.id,
            "type": "service",
            "brand_id": brand.id,
            "categories": [
                category1.id,
                category2.id
            ],
            "features": [
                {
                    "feature_id": feature1.id,
                    "feature_value_id": feature_value1.id,
                    "settings": fake_settings()
                },
                {
                    "feature_id": feature2.id,
                    "feature_value_id": feature_value2.id,
                    "settings": fake_settings()
                }
            ],
            "review": {
                "chats": [],
                "state": "ready"
            },
            "description": fake_json(),
            "media": [
                media1.id,
                media2.id,
            ],
            "name": fake_json(),
            "permalink": fake.uuid4(),
            "settings": fake_settings(),
            "short_description": fake_json(),
            "tag_groups": [
                tag_group1.id,
                tag_group2.id
            ],
            "tags": [
                {
                    "tag_id": tag1.id,
                    "show": False
                },
                {
                    "tag_id": tag2.id,
                    "show": False
                }
            ],
            "thumbnail_id": thumbnail.id
        }
        request = self.make_request('/admin/product', data)
        res = ProductView.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")
        print(json.loads(res.content))

    def test_tag(self):
        tag = fake_tag()
        data = {
            "id": tag.id,
            "name": fake_json(),
        }
        request = self.make_request('/admin/tag', data)
        res = TagView.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")

    def test_storage(self):
        product_feature = mixer.blend(ProductFeature)
        supplier = fake_user(is_supplier=True, is_verify=True)
        vip_price1 = mixer.blend(VipPrice)
        vip_price2 = mixer.blend(VipPrice)
        accessory_product1 = fake_product()
        accessory_storage1 = fake_storage(product=accessory_product1)
        accessory_product2 = fake_product()
        accessory_storage2 = fake_storage(product=accessory_product2)
        storage = fake_storage()
        product = storage.product
        data = {
            "id": storage.id,
            "available_count": 100,
            "available_count_for_sale": 100,
            "deadline": None,
            "dimensions": {
                "weight": 10,
                "height": 10,
                "length": 10,
                "width": 10
            },
            "start_price": 5000,
            "discount_price": 10000,
            "final_price": 20000,
            "features": [
                {
                    "product_feature_id": product_feature.id,
                    "extra_data": fake_settings()
                }
            ],
            "invoice_description": fake_json(),
            "invoice_title": fake_json(),
            "max_count_for_sale": 10,
            "min_count_alert": 3,
            "product_id": product.id,
            "shipping_cost": 0,
            'items': [
                {'package_item_id': 1, 'count': 5},
                {'package_item_id': 2, 'count': 10}
            ],
            "start_time": 1591004832,
            "supplier_id": supplier.id,
            "tax_type": "has_not",
            "title": fake_json(),
            "vip_prices": [
                {'vip_type_id': vip_price1.vip_type_id, 'discount_price': vip_price1.discount_price,
                 'max_count_for_sale': vip_price1.max_count_for_sale,
                 'available_count_for_sale': vip_price1.available_count_for_sale},
                {'vip_type_id': vip_price2.vip_type_id, 'discount_price': vip_price2.discount_price,
                 'max_count_for_sale': vip_price2.max_count_for_sale,
                 'available_count_for_sale': vip_price2.available_count_for_sale}
            ],
            "accessories": [
                {
                    "accessory_product_id": accessory_product1.id,
                    "accessory_storage_id": accessory_storage1.id,
                    "discount_price": 2000
                },
                {
                    "accessory_product_id": accessory_product2.id,
                    "accessory_storage_id": accessory_storage2.id,
                    "discount_price": 3000
                }
            ]
        }
        request = self.make_request('/admin/storage', data)
        res = StorageView.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")

    def test_package(self):
        pass
        # todo

    def test_vip_price(self):
        pass
        # todo

    def test_tag_group(self):
        tag1 = fake_tag()
        tag2 = fake_tag()
        tag3 = fake_tag()
        tag_group = fake_tag_group()
        data = {
            "id": tag_group.id,
            "name": fake_json(),
            "category_id": self.category.id,
            "tags": [
                tag1.id,
                tag2.id,
                tag3.id
            ]
        }
        request = self.make_request('/admin/tag_group', data)
        res = TagGroupView.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")

    def test_special_offer(self):
        pass
        # todo

    def test_special_product(self):
        pass
        # todo

    def test_ad(self):
        pass

        # todo

    def test_slider(self):
        pass
        # todo

    def test_promote_category(self):
        category1 = fake_category()
        category2 = fake_category()
        data = {
            "category_ids": [category1.id, category2.id]
        }
        request = self.make_request('/admin/promote_categories', data)
        res = PromoteCategory.as_view()(request)
        self.assertEqual(res.status_code, res_code['updated'], f"can't update")
