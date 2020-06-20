from py3dbp import Packer, Bin, Item
from server.models import BasketProduct, Basket
from math import ceil
import pysnooper
from django.db.models import F, Sum, Max, Avg
from django.contrib.postgres.fields.jsonb import KeyTextTransform


class CustomBin(Bin):
    def string(self):
        return [int(self.width), int(self.height), int(self.depth), int(self.max_weight), int(self.get_volume())]


class CustomItem(Item):
    def string(self):
        self.position = [int(position) for position in self.position]
        return [int(self.width), int(self.height), int(self.depth), int(self.weight), self.position, self.rotation_type
            , int(self.get_volume())]


class CustomPacker(Packer):
    def remove_item(self, item):
        self.items.pop(item)
        self.total_items = len(self.items) - 1


boxes = [CustomBin('box_1', 95, 100, 190, 100000), CustomBin('box_2', 100, 140, 200, 100000),
         CustomBin('box_3', 165, 205, 270, 100000),
         CustomBin('box_4', 195, 205, 305, 100000), CustomBin('box_5', 200, 260, 400, 100000),
         CustomBin('box_6', 250, 250, 500, 100000),
         CustomBin('box_7', 320, 350, 600, 100000), CustomBin('box_8', 320, 440, 600, 100000)]

guilan = 25  # state
tehran = 8  # state
guilan_neighbor = [3, 8, 14, 18, 27]  # states
tehran_neighbor = [5, 15, 19, 27, 32]  # states

# gram - toman
state_prices = [{'state': 'in', 'prices': [{'weight': 500, 'price': 5750}, {'weight': 1000, 'price': 7400},
                                           {'weight': 2000, 'price': 9800}]},
                {'state': 'neighbor', 'prices': [{'weight': 500, 'price': 7800}, {'weight': 1000, 'price': 10000},
                                                 {'weight': 2000, 'price': 12700}]},
                {'state': 'out', 'prices': [{'weight': 500, 'price': 8400}, {'weight': 1000, 'price': 11200},
                                            {'weight': 2000, 'price': 14000}]}]  # 2500 per every extar 2 kg


def get_state_position(destination, origin=25):
    if origin == destination:
        return 'in'
    if origin == 25:
        if destination in guilan_neighbor:
            return 'neighbor'
        return 'out'
    if origin == 8:
        if destination in guilan_neighbor:
            return 'neighbor'
        return 'out'


def get_transport_price(basket=None, basket_id=None):
    if basket is None:
        basket = Basket.objects.get(pk=basket_id)
    basket_products = BasketProduct.objects.filter(basket=basket)
    # print(basket_products.annotate(weight=KeyTextTransform('weight', 'storage__dimensions')).first().weight)
    # print(basket_products.aggregate(test=Sum(KeyTextTransform('weight', 'storage__dimensions'))))
    items = []
    weight = 0
    for basket_product in basket_products:
        storage = basket_product.storage
        sizes = list(storage.dimensions.values())
        items.append(CustomItem(storage.title[basket.user.language], *sizes))
        weight += storage.dimensions['weight'] * basket_product.count
    # packed_items = packing(items, boxes)
    # weight = sum(basket_products.values_list('storage__dimensions__weight', flat=True))
    print(weight)
    state = basket.user.default_address.state_id
    state_position = get_state_position(destination=state)
    for state_price in state_prices:
        if state_price['state'] == state_position:
            for item in state_price['prices']:
                if weight < item['weight']:
                    return item['price']
            else:
                return state_price['prices'][-1]['price'] + ceil((weight - 2000) / 2500) * 2500


def packing(items, boxes, required_bins=[]):
    packer = CustomPacker()
    for box in boxes:
        box.items = []
        box.unfitted_items = []
    [packer.add_bin(item) for item in boxes]
    [packer.add_item(item) for item in items]
    packer.pack()
    for b in packer.bins:
        if not b.unfitted_items:
            fitted_items_name = [item.name for item in b.items]
            required_bins.append({'name': b.name, 'items': fitted_items_name})
            return required_bins
        if b == boxes[-1]:
            fitted_items_name = [item.name for item in b.items]
            required_bins.append({'name': b.name, 'items': fitted_items_name})
            packing(b.unfitted_items, boxes)
