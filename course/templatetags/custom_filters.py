from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Truy xuất giá trị từ dictionary bằng key"""
    return dictionary.get(key)
