from py3dbp import Packer, Bin, Item
import pysnooper


# Todo make multiple box
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
        self.total_items = len(self.items) - 1
        self.items.pop(item)


#  طول - عرض - ارتفاع


def test():
    boxes = [CustomBin('box_1', 95, 100, 190, 100000), CustomBin('box_2', 100, 140, 200, 100000),
             CustomBin('box_3', 165, 205, 270, 100000),
             CustomBin('box_4', 195, 205, 305, 100000), CustomBin('box_5', 200, 260, 400, 100000),
             CustomBin('box_6', 250, 250, 500, 100000),
             CustomBin('box_7', 320, 350, 600, 100000), CustomBin('box_8', 320, 440, 600, 100000)]

    # items = [CustomItem('item1', 20, 50, 30, 250), CustomItem('item2', 20, 50, 30, 250),
    #          CustomItem('item3', 60, 60, 180, 250),
    #          CustomItem('item6', 60, 60, 180, 250), CustomItem('item7', 180, 80, 180, 250),
    #          CustomItem('item8', 180, 80, 180, 250),
    #          CustomItem('item9', 180, 80, 180, 250), CustomItem('item10', 180, 80, 180, 250),
    #          CustomItem('item11', 180, 80, 180, 250),
    #          CustomItem('item12', 180, 80, 180, 250), CustomItem('item13', 180, 80, 180, 250),
    #          CustomItem('item14', 180, 80, 180, 250),
    #          CustomItem('item15', 180, 150, 180, 250), CustomItem('item16', 100, 230, 190, 250),
    #          CustomItem('item17', 120, 250, 190, 250),
    #          CustomItem('item18', 300, 300, 300, 250), CustomItem('item4', 50, 10, 10, 250),
    #          CustomItem('item5', 50, 50, 10, 250)]

    items = [CustomItem('item1', 185, 210, 300, 250)]

    item_remained = True
    required_bins = []
    while item_remained:
        print('items:', [item.name for item in items])
        packer = CustomPacker()
        [packer.add_bin(item) for item in boxes]
        # [packer.remove_item(item) for item in items]
        packer.items.clear()
        [packer.add_item(item) for item in items]
        print('after_items:', [item.name for item in items])
        print('after_packer_items:', [item.name for item in packer.items])
        packer.pack()
        print('after_packing_items:', [item.name for item in items])
        print('after_packing_packer_items:', [item.name for item in packer.items])

        for b in packer.bins:
            # print(f"trying {b.name}", b.string())
            #
            # print("FITTED ITEMS:")
            # for item in b.items:
            #     print(f"====> {item.name}", item.string())
            #
            # print("UNFITTED ITEMS:")
            # for item in b.unfitted_items:
            #     print(f"====> {item.name}", item.string())
            #
            # print("---------------------------------------------------")

            if not b.unfitted_items:
                # print(f'Recomended box is: {b.name}')
                required_bins.append(b.name)
                item_remained = False
                break
            if b == boxes[-1]:
                items = b.unfitted_items
                items_name = [item.name for item in b.unfitted_items]
                # print('cant fit:', items_name)
                print(f'but some items fits in {b.name}, looking for another bin')
                required_bins.append(b.name)

    print("remaining_items:", [item.name for item in b.unfitted_items])
    print("required_bins:", required_bins)


test()
