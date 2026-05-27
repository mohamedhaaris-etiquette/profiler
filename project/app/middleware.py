from django.shortcuts import redirect
from .models import Organization

class SubdomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0]  # remove port
        parts = host.split('.')

        # e.g. admin-electrical.yourportal.com → parts = ['admin-electrical', 'yourportal', 'com']
        # e.g. localhost → parts = ['localhost']  ← skip

        if len(parts) >= 3:
            subdomain = parts[0]

            # skip www and admin
            if subdomain not in ('www', 'admin', ''):
                try:
                    org = Organization.objects.get(subdomain=subdomain, is_active=True)
                    # redirect to the public landing page
                    return redirect('public_landing', slug=org.slug)
                except Organization.DoesNotExist:
                    pass

        return self.get_response(request)