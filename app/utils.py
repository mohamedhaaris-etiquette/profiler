import re

from django.utils.text import slugify


def normalize_indian_phone(value: str) -> str:
    """Return an Indian mobile number in WhatsApp's 91XXXXXXXXXX format."""
    digits = re.sub(r'\D', '', value or '')
    if digits.startswith('0') and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        digits = f'91{digits}'
    if len(digits) != 12 or not digits.startswith('91'):
        raise ValueError('Enter a valid 10-digit Indian mobile number.')
    return digits


def unique_organization_key(model, value: str, field: str = 'subdomain') -> str:
    """Build a collision-safe slug/subdomain key for an Organization model."""
    base = slugify(value)[:80] or 'business'
    candidate = base
    suffix = 2
    while model.objects.filter(**{field: candidate}).exists():
        tail = f'-{suffix}'
        candidate = f'{base[:100 - len(tail)]}{tail}'
        suffix += 1
    return candidate
