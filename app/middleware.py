"""
middleware.py — Portal Platform
Subdomain routing middleware.

When a request comes in on johns-electricals.yourplatform.com,
this middleware detects the subdomain and sets request.subdomain_org
so views can render the correct org's landing page.

Setup:
1. Add 'portal.middleware.SubdomainMiddleware' to MIDDLEWARE (before CommonMiddleware)
2. Add a URL pattern: path('', views.subdomain_landing, name='subdomain_landing')
3. Set ROOT_DOMAIN in settings.py: ROOT_DOMAIN = 'yourplatform.com'
"""

from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.urls import resolve, reverse
from django.shortcuts import redirect


class SubdomainMiddleware:
    """
    Detects subdomain from the HTTP_HOST header.
    Sets request.subdomain (str) and request.subdomain_org (Organization or None).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.root_domain  = getattr(settings, 'ROOT_DOMAIN', 'yourplatform.com')

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()  # strip port

        request.subdomain     = ''
        request.subdomain_org = None

        # Check if this is a subdomain request
        if host.endswith('.' + self.root_domain):
            sub = host[: -len(self.root_domain) - 1]   # e.g. 'johns-electricals'
            if sub and sub != 'www':
                request.subdomain = sub
                # Lazy lookup — set on first use in subdomain_landing view
                request._subdomain_name = sub

        response = self.get_response(request)
        return response


class PlanEnforcementMiddleware:
    """
    Checks plan expiry on each dashboard request.
    """

    EXEMPT_PATHS = [
        '/login/', '/logout/', '/signup/', '/dashboard/settings/',
        '/django-admin/', '/static/', '/media/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.plan_expired = False

        if (
            request.user.is_authenticated
            and not request.user.is_super_admin
            and request.path.startswith('/dashboard/')
        ):
            org = getattr(request.user, 'organization', None)
            if org:
                if not org.is_plan_active:
                    request.plan_expired = True

        response = self.get_response(request)
        return response
        
class LoginRequiredMiddleware:
    """
    Redirects unauthenticated users to login page.
    Prevents accessing dashboard via browser back/forward after logout.
    """

    EXEMPT_PATHS = [
        '/login/',
        '/logout/',
        '/signup/',
        '/register-admin/',
        '/accounts/',
        '/onboard/',
        '/join/',
        '/discover/',
        '/ajax/',
        '/payment/',
        '/static/',
        '/media/',
        '/django-admin/',
    ]

    EXEMPT_URL_NAMES = [
        'login',
        'logout',
        'signup',
        'home',
        'register_super_admin',
        'password_reset',
        'password_reset_done',
        'password_reset_confirm',
        'password_reset_complete',
        'public_landing',
        'public_product_detail',
        'product_detail_json',
        'download_product_catalog',
        'public_content_json',
        'visiting_card',
        'download_vcard',
        'subdomain_landing',
        'signup_with_ref',
        'onboard_accept',
        'onboard_pending_review',
        'onboard_done',
        'discovery_home',
        'discovery_category',
        'load_sub_categories',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip if user is authenticated
        if request.user.is_authenticated:
            response = self.get_response(request)
            # Add no-cache headers for authenticated pages
            self._add_no_cache_headers(response)
            return response

        # Skip exempt paths
        if self._is_exempt(request):
            response = self.get_response(request)
            return response

        # Skip public org pages (/org/<slug>/)
        if request.path.startswith('/org/'):
            response = self.get_response(request)
            return response

        # Redirect to login
        return redirect(settings.LOGIN_URL)

    def _is_exempt(self, request):
        """Check if current path is exempt from login"""
        path = request.path

        # Check exact path match
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return True

        # Check URL name match
        try:
            url_name = resolve(path).url_name
            if url_name in self.EXEMPT_URL_NAMES:
                return True
        except:
            pass

        return False

    def _add_no_cache_headers(self, response):
        """Prevent browser caching for authenticated users"""
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

class AnalyticsMiddleware:
    """
    Auto-logs PageView for every public org landing page.
    Replaces manual log_page_view() calls in views.
    Set ANALYTICS_MIDDLEWARE_ENABLED = True in settings to activate.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'ANALYTICS_MIDDLEWARE_ENABLED', False)

    def __call__(self, request):
        response = self.get_response(request)

        if self.enabled and response.status_code == 200:
            # Only log public org pages
            if request.path.startswith('/org/') and not request.path.endswith('/json/'):
                try:
                    self._log_view(request)
                except Exception:
                    pass

        return response

    def _log_view(self, request):
        from .models import PageView, Organization
        import hashlib

        slug = request.path.split('/')[2] if len(request.path.split('/')) > 2 else ''
        if not slug:
            return

        org = Organization.objects.filter(slug=slug, is_active=True).first()
        if not org:
            return

        if not request.session.session_key:
            request.session.create()

        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR', '')
        )

        PageView.objects.create(
            organization = org,
            session_key  = request.session.session_key or '',
            ip_hash      = hashlib.sha256(ip.encode()).hexdigest()[:16] if ip else '',
            referrer     = request.META.get('HTTP_REFERER', '')[:500],
            user_agent   = request.META.get('HTTP_USER_AGENT', '')[:300],
        )
