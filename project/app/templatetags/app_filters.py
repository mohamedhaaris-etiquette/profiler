from django import template

register = template.Library()


@register.filter(name='split')
def split(value, sep=None):
    """Split a string by `sep` and return a list. Trims whitespace from items.

    Usage: {{ "a,b,c"|split:"," }}
    """
    if value is None:
        return []
    try:
        if sep is None:
            return [s.strip() for s in str(value).split()]
        return [s.strip() for s in str(value).split(sep)]
    except Exception:
        return []
