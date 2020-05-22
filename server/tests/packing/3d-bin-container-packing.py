from container_packing.shortcuts import pack_products_into_restrictions

boxes = [{
    'x': 10,
    'y': 20,
    'z': 30,
    'quantity': 15
}, {
    'x': 20,
    'y': 30,
    'z': 60,
    'quantity': 1
}]

conataner_max_sizes = (60, 60, 40)

container_x, container_y, container_z = pack_products_into_restrictions(
    boxes,
    conataner_max_sizes
)

print(container_x, container_y, container_z)