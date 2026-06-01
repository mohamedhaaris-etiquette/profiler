from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse

from .models import (
    Organization, BusinessCategory, SubCategory,
    VisitingCard, PaymentQR, WhatsAppConfig,
    SupplyChainLink, SupplyChainRole,
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
        qr = PaymentQR.objects.create(
            organization = org,
            label        = request.POST.get('label', 'Pay Now').strip(),
            method       = request.POST.get('method', 'upi'),
            upi_id       = request.POST.get('upi_id', '').strip(),
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
    Public discovery page — browse all verified organizations by category.
    Works like Justdial: search by name / city / category.
    """
    q      = request.GET.get('q', '').strip()
    city   = request.GET.get('city', '').strip()
    cat_id = request.GET.get('cat', '')

    from django.core.paginator import Paginator

    orgs = Organization.objects.filter(is_active=True, status='active').select_related(
        'category', 'sub_category', 'plan'
    )
    if q:
        from django.db.models import Q
        orgs = orgs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(tagline__icontains=q)
        )
    if city:
        orgs = orgs.filter(city__icontains=city)
    if cat_id:
        orgs = orgs.filter(category_id=cat_id)

    paginator = Paginator(orgs.order_by('-is_verified', '-created_at'), 20)
    page      = paginator.get_page(request.GET.get('page'))

    categories = BusinessCategory.objects.all()
    cities     = Organization.objects.filter(is_active=True).values_list('city', flat=True).distinct().order_by('city')

    return render(request, 'discovery_home.html', {
        'page_obj':   page,
        'categories': categories,
        'cities':     list(cities)[:50],
        'q': q, 'city': city, 'cat_id': cat_id,
        'total': orgs.count(),
    })


def discovery_category(request, cat_slug):
    """All organizations under a specific category."""
    cat  = get_object_or_404(BusinessCategory, slug=cat_slug)
    subcats = cat.sub_categories.filter(is_active=True)

    from django.core.paginator import Paginator
    from django.db.models import Q

    q    = request.GET.get('q', '').strip()
    city = request.GET.get('city', '').strip()
    sub  = request.GET.get('sub', '')

    orgs = Organization.objects.filter(
        category=cat, is_active=True, status='active'
    ).select_related('sub_category', 'plan')

    if q:
        orgs = orgs.filter(Q(name__icontains=q) | Q(tagline__icontains=q))
    if city:
        orgs = orgs.filter(city__icontains=city)
    if sub:
        orgs = orgs.filter(sub_category_id=sub)

    paginator = Paginator(orgs.order_by('-is_verified', '-created_at'), 20)
    page      = paginator.get_page(request.GET.get('page'))

    return render(request, 'discovery_category.html', {
        'cat':      cat,
        'subcats':  subcats,
        'page_obj': page,
        'q': q, 'city': city, 'sub': sub,
    })