from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse
from decimal import Decimal, InvalidOperation

from .models import (
    Organization, BusinessCategory, SubCategory,
    VisitingCard, PaymentQR, WhatsAppConfig,
    SupplyChainLink, SupplyChainRole, Service,
)


# ─────────────────────────────────────────────────────────────────────────────
#  DIGITAL VISITING CARD
# ─────────────────────────────────────────────────────────────────────────────

def visiting_card(request, slug):
    """Public digital visiting card page — mobile-optimised, shareable link."""
    org  = get_object_or_404(Organization, slug=slug, is_active=True)
    card, _ = VisitingCard.objects.get_or_create(organization=org)

    # Track view
    VisitingCard.objects.filter(pk=card.pk).update(total_views=card.total_views + 1)

    wa_config = getattr(org, 'whatsapp_config', None)
    return render(request, 'visiting_card.html', {
        'org':       org,
        'card':      card,
        'wa_config': wa_config,
        'payment_qrs': org.payment_qrs.filter(is_active=True)[:3],
    })


def download_vcard(request, slug):
    """Download a .vcf vCard for the organization's visiting card."""
    org  = get_object_or_404(Organization, slug=slug, is_active=True)
    card, _ = VisitingCard.objects.get_or_create(organization=org)

    # Track save
    VisitingCard.objects.filter(pk=card.pk).update(total_saves=card.total_saves + 1)

    vcf_text = card.get_vcard_text()
    response = HttpResponse(vcf_text, content_type='text/vcard')
    safe_name = org.name.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{safe_name}.vcf"'
    return response


@login_required
def edit_visiting_card(request):
    org  = request.user.organization
    if not org:
        return redirect('dashboard')
    card, _ = VisitingCard.objects.get_or_create(organization=org)

    if request.method == 'POST':
        card.contact_name    = request.POST.get('contact_name', '').strip()
        card.designation     = request.POST.get('designation', '').strip()
        card.tagline         = request.POST.get('tagline', '').strip()
        card.theme           = request.POST.get('theme', 'modern')
        card.direct_phone    = request.POST.get('direct_phone', '').strip()
        card.direct_whatsapp = request.POST.get('direct_whatsapp', '').strip()
        card.direct_email    = request.POST.get('direct_email', '').strip()
        card.linkedin_url    = request.POST.get('linkedin_url', '').strip()
        card.instagram_url   = request.POST.get('instagram_url', '').strip()
        card.twitter_url     = request.POST.get('twitter_url', '').strip()
        card.youtube_url     = request.POST.get('youtube_url', '').strip()
        if request.FILES.get('profile_photo'):
            card.profile_photo = request.FILES['profile_photo']
        card.save()
        messages.success(request, 'Visiting card updated.')
        return redirect('edit_visiting_card')

    return render(request, 'edit_visiting_card.html', {
        'org': org, 'card': card,
        'card_url': request.build_absolute_uri(f'/card/{org.slug}/'),
    })


# ─────────────────────────────────────────────────────────────────────────────
#  PAYMENT QR
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def manage_payment_qr(request):
    org = request.user.organization
    return render(request, 'manage_payment_qr.html', {
        'org': org,
        'payment_qrs': org.payment_qrs.all(),
    })


@login_required
def add_payment_qr(request):
    org = request.user.organization
    if request.method == 'POST':
        label = request.POST.get('label', '').strip()
        if not label:
            messages.error(request, 'Payment label is required.')
            return redirect('manage_payment_qr')

        amount = None
        amount_raw = request.POST.get('amount', '').strip()
        if amount_raw:
            try:
                amount = Decimal(amount_raw)
                if amount <= 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                messages.error(request, 'Enter a valid payment amount greater than zero.')
                return redirect('manage_payment_qr')

        qr = PaymentQR.objects.create(
            organization = org,
            label        = label,
            method       = request.POST.get('method', 'upi'),
            upi_id       = request.POST.get('upi_id', '').strip(),
            amount       = amount,
            is_primary   = request.POST.get('is_primary') == 'on',
        )
        if request.FILES.get('qr_image'):
            qr.qr_image = request.FILES['qr_image']
            qr.save()
        messages.success(request, 'Payment QR added.')
    return redirect('manage_payment_qr')


@login_required
def delete_payment_qr(request, pk):
    org = request.user.organization
    qr  = get_object_or_404(PaymentQR, pk=pk, organization=org)
    qr.delete()
    messages.success(request, 'Payment QR removed.')
    return redirect('manage_payment_qr')


# ─────────────────────────────────────────────────────────────────────────────
#  WHATSAPP CONFIG
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def edit_whatsapp_config(request):
    org = request.user.organization
    if not org:
        messages.error(request, 'Organization not found. Please contact support.')
        return redirect('dashboard')

    cfg, _ = WhatsAppConfig.objects.get_or_create(
        organization=org,
        defaults={'whatsapp_number': org.whatsapp or org.phone or ''},
    )
    if request.method == 'POST':
        cfg.whatsapp_number      = request.POST.get('whatsapp_number', '').replace('+', '').replace(' ', '')
        cfg.greeting_message     = request.POST.get('greeting_message', cfg.greeting_message)
        cfg.show_float_button    = request.POST.get('show_float_button') == 'on'
        cfg.show_in_enquiry_form = request.POST.get('show_in_enquiry_form') == 'on'
        cfg.business_hours_only  = request.POST.get('business_hours_only') == 'on'
        cfg.is_active            = request.POST.get('is_active') == 'on'
        cfg.save()
        messages.success(request, 'WhatsApp settings saved.')
        return redirect('edit_whatsapp_config')
    return render(request, 'edit_whatsapp_config.html', {'org': org, 'cfg': cfg})


# ─────────────────────────────────────────────────────────────────────────────
#  SUPPLY CHAIN
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def supply_chain_view(request):
    org = request.user.organization
    parents  = SupplyChainLink.objects.filter(child=org).select_related('parent', 'parent__supply_chain_role')
    children = SupplyChainLink.objects.filter(parent=org).select_related('child', 'child__supply_chain_role')
    roles    = SupplyChainRole.objects.filter(is_active=True)
    other_orgs = Organization.objects.filter(is_active=True).exclude(pk=org.pk)
    return render(request, 'supply_chain.html', {
        'org': org, 'parents': parents, 'children': children, 'roles': roles,
        'other_orgs': other_orgs,
    })


@login_required
def link_supply_chain(request):
    """Request a supply-chain connection to another organisation."""
    org = request.user.organization
    if request.method == 'POST':
        target_pk  = request.POST.get('target_org')
        direction  = request.POST.get('direction', 'child')  # 'parent' or 'child'
        note       = request.POST.get('note', '').strip()

        target = get_object_or_404(Organization, pk=target_pk, is_active=True)

        if direction == 'child':
            parent, child = org, target
        else:
            parent, child = target, org

        link, created = SupplyChainLink.objects.get_or_create(
            parent=parent, child=child,
            defaults={'note': note, 'status': 'pending'},
        )
        if created:
            messages.success(request, f'Connection request sent to {target.name}.')
        else:
            messages.info(request, f'A connection with {target.name} already exists.')
    return redirect('supply_chain')


@login_required
def update_chain_link(request, pk):
    """Approve / reject a pending supply-chain link."""
    org  = request.user.organization
    link = get_object_or_404(SupplyChainLink, pk=pk)

    # Only the parent or child can update
    if org not in (link.parent, link.child):
        messages.error(request, 'Permission denied.')
        return redirect('supply_chain')

    new_status = request.POST.get('status', '')
    if new_status in ('active', 'rejected', 'inactive'):
        from django.utils import timezone
        link.status = new_status
        if new_status == 'active':
            link.approved_at = timezone.now()
        link.save()
        messages.success(request, f'Connection {new_status}.')
    return redirect('supply_chain')


# ─────────────────────────────────────────────────────────────────────────────
#  DISCOVERY HOME (Justdial / OLX-style)
# ─────────────────────────────────────────────────────────────────────────────

def discovery_home(request):
    """
    Public business marketplace.

    Only active, super-admin-approved organizations are discoverable. The
    endpoint returns the complete page normally and the results fragment for
    AJAX requests, so search stays fast without losing its no-JavaScript
    fallback.
    """
    q = request.GET.get('q', '').strip()[:120]
    city = request.GET.get('city', '').strip()[:100]
    cat_id = request.GET.get('cat', '').strip()
    verified = request.GET.get('verified', '') == '1'
    sort = request.GET.get('sort', 'recommended')

    if cat_id and not cat_id.isdigit():
        cat_id = ''

    approved_orgs = Organization.objects.filter(
        is_active=True,
        status='active',
    )
    orgs = approved_orgs.select_related(
        'category',
        'sub_category',
        'plan',
    ).prefetch_related(
        Prefetch(
            'services',
            queryset=Service.objects.filter(is_active=True).order_by('order', 'name'),
            to_attr='discovery_services',
        ),
    )

    if q:
        orgs = orgs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(tagline__icontains=q) |
            Q(category__name__icontains=q) |
            Q(sub_category__name__icontains=q) |
            Q(services__name__icontains=q) |
            Q(products__name__icontains=q)
        ).distinct()
    if city:
        orgs = orgs.filter(city__icontains=city)
    if cat_id:
        orgs = orgs.filter(category_id=cat_id)
    if verified:
        orgs = orgs.filter(is_verified=True)

    ordering = {
        'recommended': ('-is_verified', '-created_at'),
        'newest': ('-created_at',),
        'name': ('name',),
    }
    if sort not in ordering:
        sort = 'recommended'

    filtered_total = orgs.count()
    paginator = Paginator(orgs.order_by(*ordering[sort]), 12)
    page = paginator.get_page(request.GET.get('page'))

    categories = BusinessCategory.objects.annotate(
        active_business_count=Count(
            'organization',
            filter=Q(
                organization__is_active=True,
                organization__status='active',
            ),
            distinct=True,
        ),
    ).order_by('-active_business_count', 'name')

    city_rows = list(
        approved_orgs.exclude(city='')
        .values('city')
        .annotate(business_count=Count('id'))
        .order_by('-business_count', 'city')[:12]
    )
    popular_searches = [
        category.name
        for category in categories
        if category.active_business_count
    ][:6]
    if not popular_searches:
        popular_searches = [
            'Electrician', 'Plumber', 'Mechanic',
            'Home Service', 'Repair', 'Restaurant',
        ]

    why_features = [
        {
            'icon': 'bi-shop-window',
            'title': 'Professional business page',
            'desc': 'Show services, products, offers and contact details in one place.',
        },
        {
            'icon': 'bi-whatsapp',
            'title': 'Direct customer enquiries',
            'desc': 'Turn profile visits into WhatsApp, call and quotation enquiries.',
        },
        {
            'icon': 'bi-patch-check',
            'title': 'Verified visibility',
            'desc': 'Build trust after the super admin approves your business.',
        },
        {
            'icon': 'bi-graph-up-arrow',
            'title': 'Track business growth',
            'desc': 'Understand profile views and customer actions from your dashboard.',
        },
    ]

    context = {
        'page_obj': page,
        'categories': categories,
        'city_rows': city_rows,
        'popular_searches': popular_searches,
        'why_features': why_features,
        'q': q,
        'city': city,
        'cat_id': cat_id,
        'verified': verified,
        'sort': sort,
        'total': filtered_total,
        'platform_total': approved_orgs.count(),
        'verified_total': approved_orgs.filter(is_verified=True).count(),
        'city_total': approved_orgs.exclude(city='').values('city').distinct().count(),
    }

    if (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.GET.get('partial') == '1'
    ):
        return render(request, 'includes/discovery_results.html', context)

    return render(request, 'discovery_home.html', context)


def discovery_category(request, cat_slug):
    """All organizations under a specific category."""
    cat  = get_object_or_404(BusinessCategory, slug=cat_slug)
    subcats = cat.sub_categories.filter(is_active=True)

    q    = request.GET.get('q', '').strip()
    city = request.GET.get('city', '').strip()
    sub  = request.GET.get('sub', '')

    orgs = Organization.objects.filter(
        category=cat, is_active=True, status='active'
    ).select_related('sub_category', 'plan').prefetch_related(
        Prefetch(
            'services',
            queryset=Service.objects.filter(is_active=True).order_by('order', 'name'),
            to_attr='discovery_services',
        ),
    )

    if q:
        orgs = orgs.filter(
            Q(name__icontains=q) |
            Q(tagline__icontains=q) |
            Q(services__name__icontains=q) |
            Q(products__name__icontains=q)
        ).distinct()
    if city:
        orgs = orgs.filter(city__icontains=city)
    if sub and sub.isdigit():
        orgs = orgs.filter(sub_category_id=sub)

    paginator = Paginator(orgs.order_by('-is_verified', '-created_at'), 20)
    page      = paginator.get_page(request.GET.get('page'))

    return render(request, 'discovery_category.html', {
        'cat':      cat,
        'subcats':  subcats,
        'page_obj': page,
        'q': q, 'city': city, 'sub': sub,
    })
