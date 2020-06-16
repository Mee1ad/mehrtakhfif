from py3dbp import Packer, Bin, Item


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

guilan = 25
guilan_neighbor = [3, 8, 14, 18, 27]
tehran_neighbor = [5, 15, 19, 27, 32]


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
            print(required_bins)
            return required_bins
        if b == boxes[-1]:
            fitted_items_name = [item.name for item in b.items]
            required_bins.append({'name': b.name, 'items': fitted_items_name})
            packing(b.unfitted_items, boxes)
