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


@register.filter(name='strip')
def strip(value):
    """Trim whitespace from the start and end of a string."""
    if value is None:
        return ''
    try:
        return str(value).strip()
    except Exception:
        return value



@register.filter
def currency(value):
    """Format a number as Indian Rupee currency. {{ product.price|currency }}"""
    try:
        return f'₹{float(value):,.2f}'
    except (TypeError, ValueError):
        return '₹0.00'
 
 
@register.filter
def currency_short(value):
    """Short currency: ₹1.2K, ₹4.5L etc."""
    try:
        v = float(value)
        if v >= 100000:
            return f'₹{v/100000:.1f}L'
        if v >= 1000:
            return f'₹{v/1000:.1f}K'
        return f'₹{v:,.0f}'
    except (TypeError, ValueError):
        return '₹0'
 
 
@register.filter
def intcomma(value):
    """Add comma separators to integers."""
    try:
        return f'{int(value):,}'
    except (TypeError, ValueError):
        return value
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  PHONE / TEXT FILTERS
# ══════════════════════════════════════════════════════════════════════════════
 
@register.filter
def phone_format(value):
    """Format phone number for display: +91 98765 43210"""
    if not value:
        return ''
    digits = str(value).replace('+', '').replace(' ', '').replace('-', '')
    if digits.startswith('91') and len(digits) == 12:
        return f'+91 {digits[2:7]} {digits[7:]}'
    if len(digits) == 10:
        return f'{digits[:5]} {digits[5:]}'
    return value
 
 
@register.filter
def truncate_smart(value, length=100):
    """Truncate text at word boundary."""
    if not value:
        return ''
    if len(value) <= length:
        return value
    truncated = value[:length].rsplit(' ', 1)[0]
    return truncated + '…'
 
 
@register.filter
def initials(value):
    """Get initials from a name: 'John Doe' → 'JD'"""
    if not value:
        return ''
    words = str(value).split()
    return ''.join(w[0].upper() for w in words[:2])
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  PLAN / BADGE FILTERS
# ══════════════════════════════════════════════════════════════════════════════
 
PLAN_COLORS = {
    'trial':    '#6b7280',
    'silver':   '#64748b',
    'gold':     '#d97706',
    'platinum': '#7c3aed',
}
 
PLAN_ICONS = {
    'trial':    'bi-hourglass-split',
    'silver':   'bi-award',
    'gold':     'bi-trophy-fill',
    'platinum': 'bi-gem',
}
 
 
@register.filter
def plan_badge(org):
    """
    Render an HTML plan badge for an org.
    {{ org|plan_badge }}
    """
    if not org or not org.plan:
        return mark_safe(
            '<span class="badge" style="background:#6b7280;font-size:0.7rem;">No Plan</span>'
        )
    level  = org.plan.level
    color  = PLAN_COLORS.get(level, '#6b7280')
    icon   = PLAN_ICONS.get(level, 'bi-circle')
    name   = org.plan.name
    return mark_safe(
        f'<span class="badge" style="background:{color};font-size:0.7rem;">'
        f'<i class="bi {icon} me-1"></i>{name}</span>'
    )
 
 
@register.filter
def plan_color(plan_level):
    """Return hex color for a plan level string."""
    return PLAN_COLORS.get(plan_level, '#6b7280')
 
 
@register.filter
def plan_icon(plan_level):
    """Return Bootstrap icon class for a plan level string."""
    return PLAN_ICONS.get(plan_level, 'bi-circle')
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  STATUS BADGE FILTER
# ══════════════════════════════════════════════════════════════════════════════
 
STATUS_COLORS = {
    'active':     ('#22c55e', '#dcfce7'),
    'inactive':   ('#6b7280', '#f3f4f6'),
    'suspended':  ('#ef4444', '#fee2e2'),
    'pending':    ('#f59e0b', '#fef3c7'),
    'new':        ('#3b82f6', '#dbeafe'),
    'contacted':  ('#8b5cf6', '#ede9fe'),
    'in_progress':('#f59e0b', '#fef3c7'),
    'resolved':   ('#22c55e', '#dcfce7'),
    'closed':     ('#6b7280', '#f3f4f6'),
}
 
 
@register.filter
def status_badge(status):
    """Render colored status badge. {{ enquiry.status|status_badge }}"""
    colors = STATUS_COLORS.get(status, ('#6b7280', '#f3f4f6'))
    label  = status.replace('_', ' ').title()
    return mark_safe(
        f'<span class="badge" style="background:{colors[1]};color:{colors[0]};'
        f'font-size:0.72rem;font-weight:600;">{label}</span>'
    )
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  DATE / TIME FILTERS
# ══════════════════════════════════════════════════════════════════════════════
 
@register.filter
def days_until(date_value):
    """Returns number of days until a date. Negative = past."""
    if not date_value:
        return None
    today = timezone.now().date()
    delta = date_value - today
    return delta.days
 
 
@register.filter
def time_ago(dt):
    """Human-readable time ago: '2 hours ago', '3 days ago'"""
    if not dt:
        return ''
    now   = timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    delta = now - dt
    secs  = int(delta.total_seconds())
 
    if secs < 60:
        return 'just now'
    if secs < 3600:
        m = secs // 60
        return f'{m} min{"s" if m > 1 else ""} ago'
    if secs < 86400:
        h = secs // 3600
        return f'{h} hour{"s" if h > 1 else ""} ago'
    if secs < 604800:
        d = secs // 86400
        return f'{d} day{"s" if d > 1 else ""} ago'
    if secs < 2592000:
        w = secs // 604800
        return f'{w} week{"s" if w > 1 else ""} ago'
    m = secs // 2592000
    return f'{m} month{"s" if m > 1 else ""} ago'
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  STAR RATING FILTER
# ══════════════════════════════════════════════════════════════════════════════
 
@register.filter
def star_rating(rating):
    """Render filled/empty star icons for a rating (1-5)."""
    try:
        r = int(rating)
    except (TypeError, ValueError):
        r = 0
    r = max(0, min(5, r))
    stars = ''
    for i in range(1, 6):
        if i <= r:
            stars += '<i class="bi bi-star-fill" style="color:#f59e0b;font-size:0.85rem;"></i>'
        else:
            stars += '<i class="bi bi-star" style="color:#d1d5db;font-size:0.85rem;"></i>'
    return mark_safe(stars)
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  MATH / MISC FILTERS
# ══════════════════════════════════════════════════════════════════════════════
 
@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (TypeError, ValueError):
        return 0
 
 
@register.filter
def percentage(value, total):
    """{{ count|percentage:total }} → '45.2'"""
    try:
        return round((float(value) / float(total)) * 100, 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0
 
 
@register.filter
def dict_get(d, key):
    """Get a value from a dict in templates: {{ my_dict|dict_get:key }}"""
    try:
        return d.get(key, '')
    except AttributeError:
        return ''
 
 
@register.filter
def index(lst, i):
    """Get list item by index: {{ my_list|index:0 }}"""
    try:
        return lst[int(i)]
    except (IndexError, TypeError, ValueError):
        return ''
 
 
@register.filter
def split(value, delimiter=','):
    """Split a string: {{ 'a,b,c'|split:',' }} → ['a','b','c']"""
    if not value:
        return []
    return str(value).split(delimiter)
 
 
@register.filter
def compact_number(value):
    """1234 → 1.2K, 1234567 → 1.2M"""
    try:
        v = int(value)
        if v >= 1_000_000:
            return f'{v/1_000_000:.1f}M'
        if v >= 1_000:
            return f'{v/1_000:.1f}K'
        return str(v)
    except (TypeError, ValueError):
        return value
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  INCLUSION TAGS
# ══════════════════════════════════════════════════════════════════════════════
 
@register.simple_tag
def active_class(request, url_name):
    """
    Returns 'active' if the current URL matches url_name.
    {% active_class request 'dashboard' %}
    """
    from django.urls import reverse, NoReverseMatch
    try:
        url = reverse(url_name)
        if request.path == url or request.path.startswith(url):
            return 'active'
    except NoReverseMatch:
        pass
    return ''
 
 
@register.simple_tag
def query_string(request, **kwargs):
    """
    Build a query string preserving existing params and overriding with kwargs.
    {% query_string request page=2 status='new' %}
    """
    params = request.GET.copy()
    for k, v in kwargs.items():
        params[k] = v
    return params.urlencode()