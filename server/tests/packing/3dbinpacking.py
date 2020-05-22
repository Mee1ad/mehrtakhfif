from py3dbp import Packer, Bin, Item


class CustomBin(Bin):
    def string(self):
        return [int(self.width), int(self.height), int(self.depth), int(self.max_weight), int(self.get_volume())]


class CustomItem(Item):
    def string(self):
        self.position = [int(position) for position in self.position]
        return [int(self.width), int(self.height), int(self.depth), int(self.weight), self.position, self.rotation_type
            , int(self.get_volume())]


packer = Packer()
#  طول - عرض - ارتفاع
box_1 = CustomBin('box_1', 95, 100, 190, 100000)
box_2 = CustomBin('box_2', 100, 140, 200, 100000)
box_3 = CustomBin('box_3', 165, 205, 270, 100000)
box_4 = CustomBin('box_4', 195, 205, 305, 100000)
box_5 = CustomBin('box_5', 200, 260, 400, 100000)
box_6 = CustomBin('box_6', 250, 250, 500, 100000)
box_7 = CustomBin('box_7', 320, 350, 600, 100000)
box_8 = CustomBin('box_8', 320, 440, 600, 100000)

item_1 = CustomItem('item1', 20, 50, 30, 250)
item_2 = CustomItem('item2', 20, 50, 30, 250)
item_3 = CustomItem('item3', 60, 60, 180, 250)
item_4 = CustomItem('item4', 50, 10, 10, 250)

packer.add_bin(box_1)
packer.add_bin(box_2)
packer.add_bin(box_3)
packer.add_bin(box_4)
packer.add_bin(box_5)
packer.add_bin(box_6)
packer.add_bin(box_7)
packer.add_bin(box_8)

packer.add_item(item_1)
packer.add_item(item_2)
packer.add_item(item_3)
packer.add_item(item_4)
packer.add_item(item_4)


packer.pack()

for b in packer.bins:
    print(f"trying {b.name}", b.string())

    print("FITTED ITEMS:")
    for item in b.items:
        print(f"====> {item.name}", item.string())

    print("UNFITTED ITEMS:")
    for item in b.unfitted_items:
        print(f"====> {item.name}", item.string())

    print("---------------------------------------------------")

    if not b.unfitted_items:
        print(f'Recomended box is: {b.name}')
        break
    print([item.name for item in b.unfitted_items])

else:
    print(f'Can not fit to any of boxes')

