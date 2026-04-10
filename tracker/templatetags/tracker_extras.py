from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    if d is None:
        return None
    return d.get(key)

@register.filter
def category_class(category):
    """
    Deterministically map a Category (or name) to a CSS class.
    No DB changes needed.
    """
    if not category:
        return "cat-none"

    name = getattr(category, "name", str(category))
    # stable-ish mapping: sum of character codes
    score = sum(ord(c) for c in name)
    classes = ["cat-lake", "cat-wildflower", "cat-berry", "cat-gold", "cat-earth", "cat-forest"]
    return classes[score % len(classes)]