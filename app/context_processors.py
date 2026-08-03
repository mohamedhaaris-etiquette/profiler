"""
context_processors.py — Portal Platform
Injects global variables into every template automatically.
Add 'portal.context_processors.global_context' to TEMPLATES['OPTIONS']['context_processors']
"""

from .models import BusinessCategory, MemberInviteConfig
from django.core.cache import cache


def global_context(request):
    """
    Context available in every template:
        {{ categories }}        — all BusinessCategory objects (for nav/footer)
        {{ user_org }}          — shortcut for request.user.organization
        {{ plan_level }}        — current user's plan level string
        {{ unread_enquiries }}  — count of new enquiries for org_admin nav badge
        {{ invite_config }}     — MemberInviteConfig singleton
    """
    ctx = {
        'categories': cache.get_or_set(
            'global-business-categories',
            lambda: list(BusinessCategory.objects.all().order_by('name')),
            300,
        ),
        'user_org':   None,
        'plan_level': 'trial',
        'unread_enquiries': 0,
        'invite_config': None,
    }

    if request.user.is_authenticated:
        org = getattr(request.user, 'organization', None)
        ctx['user_org'] = org

        if org:
            ctx['plan_level'] = org.plan.level if org.plan else 'trial'
            try:
                ctx['unread_enquiries'] = org.enquiries.filter(status='new').count()
            except Exception:
                pass

        try:
            ctx['invite_config'] = MemberInviteConfig.get_config()
        except Exception:
            pass

    return ctx
