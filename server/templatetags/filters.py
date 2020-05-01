from django import template

register = template.Library()


@register.filter(name="to_rial")
def to_rial(price):
    price = int(f"{price}0")
    return f"{price:,}"


@register.filter(name="sub")
def sub(a, b):
    return f"{a - b:,}"


@register.filter(name="get_value_added")
def get_value_added(a, b):
    return f"{a - b:,}"


