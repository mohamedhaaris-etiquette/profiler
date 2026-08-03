
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import *
from .forms import (
    OrganizationSignupForm, CustomLoginForm, EnquiryForm,
    ServiceForm, OrganizationUpdateForm, ProductForm ,SuperAdminRegisterForm
)
from .utils import normalize_indian_phone




def home(request):
    subdomain = getattr(request, '_subdomain_name', '')
    if subdomain:
        org = Organization.objects.filter(
            subdomain=subdomain,
            status='active',
            is_active=True,
        ).first()
        if org:
            return public_landing(request, org.slug)

    if request.user.is_authenticated:
        return redirect('dashboard')

    categories = BusinessCategory.objects.all()
    steps = [
        ('Register your business', 'Sign up, choose a category, and create your business profile in minutes.'),
        ('Get discovered locally', 'Appear in search results when customers look for services nearby.'),
        ('Manage enquiries', 'Receive customer leads and reply directly from your dashboard.'),
        ('Grow online', 'Update services, add photos, and build trust with better listings.'),
    ]
    default_cats = [
        ('Electrician', 'lightning-charge-fill'),
        ('Plumber', 'droplet-fill'),
        ('Mechanic', 'gear-fill'),
        ('Carpenter', 'hammer'),
    ]

    return render(request, 'home.html', {
        'categories': categories,
        'steps': steps,
        'default_cats': default_cats,
    })


def _create_pending_signup(request, form, referrer_org=None, referral_code=None):
    """Create an inactive business application for super-admin review."""
    from .models import InvitationToken, Plan, Referral, ReferralProgram
    from .utils import normalize_indian_phone

    with transaction.atomic():
        org = form.save(commit=False)
        org.status = 'pending_approval'
        org.is_active = False
        org.plan = Plan.objects.filter(level='trial', is_active=True).first()
        if org.plan:
            org.plan_start_date = timezone.now().date()
            org.plan_end_date = (
                timezone.now().date()
                + timezone.timedelta(days=org.plan.duration_days)
            )
        org.save()

        user = CustomUser.objects.create_user(
            username=form.cleaned_data['username'],
            email=form.cleaned_data['user_email'],
            password=form.cleaned_data['password1'],
            first_name=form.cleaned_data['first_name'],
            last_name=form.cleaned_data['last_name'],
            phone=form.cleaned_data['user_phone'],
            organization=org,
            role='org_admin',
            is_active=False,
        )

        if org.category:
            Service.objects.bulk_create([
                Service(
                    organization=org,
                    name=service_name,
                    icon=org.category.icon,
                    order=index,
                    is_featured=index < 3,
                )
                for index, service_name in enumerate(org.category.default_services)
            ])

        try:
            phone = normalize_indian_phone(form.cleaned_data['user_phone'])
        except ValueError:
            phone = ''.join(ch for ch in form.cleaned_data['user_phone'] if ch.isdigit())

        program = ReferralProgram.objects.filter(is_active=True).first()
        bonus_points = program.points_per_referral if program else 100
        invite = InvitationToken.objects.create(
            invited_by=None,
            email=form.cleaned_data['user_email'].lower(),
            phone=phone,
            delivery_channel='whatsapp' if referrer_org else 'direct',
            invite_type='member' if referrer_org else 'direct',
            referred_by_org=referrer_org,
            referral_code=referral_code,
            invite_bonus_points=bonus_points if referrer_org else 0,
            plan=org.plan,
            main_category=org.category,
            sub_category=org.sub_category,
            site_title=org.name,
            status='accepted',
            accepted_at=timezone.now(),
            organization=org,
            approval_status='pending_review',
        )
        if referrer_org:
            Referral.objects.create(
                referrer=referrer_org,
                referred=org,
                code=referral_code,
                status='pending',
            )

        _notify_admins_of_new_submission(invite, org, request)
        return org, user, invite


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    categories = BusinessCategory.objects.all()
    form = OrganizationSignupForm()

    if request.method == 'POST':
        form = OrganizationSignupForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                org, user, invite = _create_pending_signup(request, form)
                messages.success(
                    request,
                    f'{org.name} was submitted successfully. '
                    'You can log in after the super admin approves it.',
                )
                return redirect('onboard_pending_review', token=invite.token)
            except Exception as e:
                messages.error(request, 'Registration failed. Please review the details and try again.')
        else:
            messages.error(request, 'Please fix the errors below.')

    return render(request, 'signup.html', {'form': form, 'categories': categories})

def login_view(request):
    if request.user.is_authenticated and request.session.get('_auth_user_id'):
        return redirect('dashboard')

    form = CustomLoginForm()
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect(request.GET.get('next', 'dashboard'))
        else:
            messages.error(request, 'Invalid username or password.')

    response = render(request, 'login.html', {'form': form})
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response

@login_required
def logout_view(request):
    request.session.flush()
    logout(request)

    messages.info(request, 'You have been logged out.')

    # Build response with no-cache headers
    response = redirect('login')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response

@login_required
def dashboard(request):
    user = request.user
    # Super admin dashboard
    if user.is_super_admin:
        from .models import AdminNotification

        orgs = Organization.objects.all().order_by('-created_at')
        total_enquiries = Enquiry.objects.count()
        new_enquiries = Enquiry.objects.filter(status='new').count()
        total_products = Product.objects.count()

        admin_notifications = AdminNotification.recent_unread(limit=20)
        admin_notification_count = AdminNotification.unread_count()

        response = render(request, 'super_admin_dashboard.html', {
            'orgs': orgs,
            'total_enquiries': total_enquiries,
            'new_enquiries': new_enquiries,
            'total_products': total_products,
            'admin_notifications': admin_notifications,
            'admin_notification_count': admin_notification_count,
        })

        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'

        return response

    # Org admin dashboard
    org = user.organization

    if not org:
        messages.warning(request, 'You are not linked to any organization.')
        return redirect('login')

    services = org.get_services()
    products = org.products.filter(is_active=True)
    enquiries = org.enquiries.all()[:10]
    new_enquiries = org.enquiries.filter(status='new').count()
    testimonials = org.testimonials.filter(is_active=True)[:5]

    response = render(request, 'dashboard.html', {
        'org': org,
        'services': services,
        'products': products,
        'enquiries': enquiries,
        'new_enquiries': new_enquiries,
        'testimonials': testimonials,
        'total_enquiries': org.enquiries.count(),
        'total_products': products.count(),
    })

    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
def public_landing(request, slug):
    """Public-facing landing page for an organization (with notifications)."""
    from django.shortcuts import render, redirect, get_object_or_404
    from django.contrib import messages as dj_messages
    from django.db.models import Avg, Q
    from django.utils import timezone
    from .models import (
        AdminNotification, LandingPageConfig, Organization, Plan,
    )
    from .forms import EnquiryForm
    from .notifications import notify_admin_whatsapp, notify_nearest_staff

    org = get_object_or_404(
        Organization.objects.select_related('category', 'sub_category', 'plan'),
        slug=slug,
        is_active=True,
        status='active',
    )

    services          = org.get_services()
    featured_services = services.filter(is_featured=True)
    products          = org.products.filter(is_active=True)
    featured_products = products.filter(is_featured=True)
    gallery           = org.gallery.all()[:8]
    testimonials      = org.testimonials.filter(is_active=True)
    payment_qrs       = org.payment_qrs.filter(is_active=True)
    hero_slides       = org.hero_slides.filter(is_active=True)[:10]
    now               = timezone.now()
    promo_banners     = org.promo_banners.filter(is_active=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gte=now),
    )[:20]
    landing_features  = org.landing_features.filter(is_active=True)[:12]
    maximise_steps    = org.maximise_steps.filter(is_active=True)[:12]
    faq_items         = org.faq_items.filter(is_active=True)[:20]
    success_stories   = org.success_stories.filter(is_active=True)[:12]
    dealer_locations  = org.dealer_locations.filter(is_active=True)[:24]
    public_plans      = Plan.objects.filter(is_active=True).order_by('order', 'level')[:6]
    service_count = services.count()
    product_count = products.count()
    review_summary = testimonials.aggregate(average=Avg('rating'))
    average_rating = review_summary['average']
    review_count = testimonials.count()
    landing_stats = []
    if average_rating is not None:
        landing_stats.append({
            'icon': 'star-fill',
            'value': f'{average_rating:.1f}',
            'label': f'{review_count} review{"s" if review_count != 1 else ""}',
        })
    if service_count:
        landing_stats.append({
            'icon': 'briefcase-fill',
            'value': str(service_count),
            'label': 'Services',
        })
    if product_count:
        landing_stats.append({
            'icon': 'box-seam-fill',
            'value': str(product_count),
            'label': 'Products',
        })
    if org.established_year:
        landing_stats.append({
            'icon': 'calendar-check-fill',
            'value': org.established_year,
            'label': 'Established',
        })
    if org.home_service_available:
        landing_stats.append({
            'icon': 'house-fill',
            'value': 'Available',
            'label': 'Home service',
        })
    if org.is_open_sunday:
        landing_stats.append({
            'icon': 'sun-fill',
            'value': 'Open',
            'label': 'Sunday',
        })
    if org.accepts_online_payment:
        landing_stats.append({
            'icon': 'credit-card-fill',
            'value': 'Available',
            'label': 'Online payment',
        })
    show_about_content = bool(
        org.description
        or org.established_year
        or org.is_verified
        or org.home_service_available
        or org.is_open_sunday
        or org.accepts_online_payment
        or org.phone
        or org.whatsapp
        or org.email
    )
    page_config = LandingPageConfig.objects.filter(organization=org).first()
    if page_config is None:
        page_config = LandingPageConfig(organization=org)
    has_location = bool(
        page_config.google_maps_embed_url
        or org.address_line1
        or org.city
    )
    can_customize = bool(
        request.user.is_authenticated
        and getattr(request.user, 'is_org_admin', False)
        and request.user.organization_id == org.id
    )
    customize_mode = can_customize and request.GET.get('customize') == '1'

    wa_admin_url = ''

    if request.method == 'POST':
        enquiry_form = EnquiryForm(organization=org, data=request.POST)
        if enquiry_form.is_valid():
            enquiry              = enquiry_form.save(commit=False)
            enquiry.organization = org
            enquiry.save()

            # ── Notify admin (WhatsApp) ───────────────────────────────────
            wa_admin_url = notify_admin_whatsapp(enquiry)

            # ── Auto-notify backup staff if any is unavailable ────────────
            notify_nearest_staff(enquiry)

            # ── Create AdminNotification for dashboard bell ───────────────
            AdminNotification.objects.create(
                notification_type = 'enquiry_submit',
                title             = f'New Enquiry — {org.name}',
                message           = (
                    f'Name    : {enquiry.name}\n'
                    f'Phone   : {enquiry.phone}\n'
                    f'Email   : {enquiry.email}\n'
                    f'Subject : {enquiry.subject}\n'
                    f'Message : {enquiry.message}'
                ),
                organization = org,
                is_read      = False,
            )

            dj_messages.success(
                request,
                'Your enquiry has been submitted successfully.'
            )
            request.session['wa_admin_url'] = wa_admin_url
            return redirect('public_landing', slug=slug)
    else:
        enquiry_form = EnquiryForm(organization=org)
        wa_admin_url = request.session.pop('wa_admin_url', '')

    return render(request, 'landing.html', {
        'org':               org,
        'services':          services,
        'featured_services': featured_services,
        'products':          products,
        'featured_products': featured_products,
        'gallery':           gallery,
        'testimonials':      testimonials,
        'enquiry_form':      enquiry_form,
        'wa_admin_url':      wa_admin_url,
        'payment_qrs':       payment_qrs,
        'hero_slides':       hero_slides,
        'promo_banners':     promo_banners,
        'landing_features':  landing_features,
        'maximise_steps':    maximise_steps,
        'faq_items':         faq_items,
        'success_stories':   success_stories,
        'dealer_locations':  dealer_locations,
        'public_plans':      public_plans,
        'landing_stats':     landing_stats,
        'average_rating':    average_rating,
        'review_count':      review_count,
        'show_about_content': show_about_content,
        'has_location':      has_location,
        'page_config':       page_config,
        'can_customize':     can_customize,
        'customize_mode':    customize_mode,
    })


def product_detail(request, slug, pk):
    """Public-facing product detail page."""
    org = get_object_or_404(Organization, slug=slug, is_active=True)
    product = get_object_or_404(Product, pk=pk, organization=org, is_active=True)
    gallery = [img for img in [product.image, product.image2, product.image3] if img]
    return render(request, 'product_detail.html', {
        'org': org,
        'product': product,
        'gallery': gallery,
        'related_products': org.products.filter(is_active=True).exclude(pk=product.pk)[:8],
    })


def product_detail_json(request, slug, pk):
    """Return product details as JSON for the modal."""
    from django.shortcuts import get_object_or_404
    from django.http import JsonResponse
    from .models import Organization, Product
 
    org     = get_object_or_404(Organization, slug=slug, is_active=True)
    product = get_object_or_404(Product, pk=pk, organization=org, is_active=True)
 
    images = []
    for img_field in [product.image, product.image2, product.image3]:
        if img_field:
            images.append(img_field.url)
 
    data = {
        'id':             product.pk,
        'name':           product.name,
        'brand':          product.brand,
        'description':    product.description,
        'price':          str(product.price),
        'discount_price': str(product.discount_price) if product.discount_price else None,
        'discount_percent': product.discount_percent,
        'unit':           product.unit,
        'condition':      product.get_condition_display(),
        'in_stock':       product.in_stock,
        'sku':            product.sku,
        'category':       product.category,
        'images':         images,
        'youtube_url':    getattr(product, 'youtube_url', ''),
        'instagram_url':  getattr(product, 'instagram_url', ''),
        'pdf_catalog':    product.pdf_catalog.url if getattr(product, 'pdf_catalog', None) else '',
        'specs':          getattr(product, 'specs_json', {}),
        'org_whatsapp':   org.whatsapp or org.phone,
        'org_name':       org.name,
    }
    return JsonResponse(data)

def download_product_catalog(request, slug, pk):
    """Serve the product's uploaded PDF catalog."""
    from django.shortcuts import get_object_or_404
    from django.http import FileResponse, Http404
    from .models import Organization, Product
    import os
 
    org     = get_object_or_404(Organization, slug=slug, is_active=True)
    product = get_object_or_404(Product, pk=pk, organization=org, is_active=True)
 
    pdf = getattr(product, 'pdf_catalog', None)
    if not pdf:
        raise Http404("No catalog available for this product.")
 
    file_path = pdf.path
    if not os.path.exists(file_path):
        raise Http404("Catalog file not found.")
 
    filename = f"{product.name.replace(' ', '_')}_catalog.pdf"
    response = FileResponse(open(file_path, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def toggle_staff_availability(request, user_pk):
    """Quick toggle for a staff member's availability status."""
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib.auth.decorators import login_required
    from django.contrib import messages as dj_messages
    from .models import CustomUser, StaffAvailability
 
    if not request.user.is_authenticated:
        return redirect('login')
 
    target_user = get_object_or_404(
        CustomUser, pk=user_pk, organization=request.user.organization
    )
    avail, _ = StaffAvailability.objects.get_or_create(staff=target_user)
    avail.status = 'available' if avail.status != 'available' else 'busy'
    avail.save()
 
    dj_messages.success(
        request,
        f"{target_user.get_full_name()}: {avail.get_status_display()}"
    )
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def manage_services(request):
    org = request.user.organization
    if not org:
        return redirect('dashboard')
    services = org.services.all()
    return render(request, 'manage_services.html', {'org': org, 'services': services})


@login_required
def add_service(request):
    org = request.user.organization
    if not org:
        messages.error(request, 'Your account is not attached to a business profile.')
        return redirect('dashboard')
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            svc = form.save(commit=False)
            svc.organization = org
            svc.save()
            messages.success(request, 'Service added successfully.')
            return redirect('manage_services')
        messages.error(request, 'The service was not saved. Correct the highlighted fields below.')
    else:
        form = ServiceForm()
    return render(request, 'service_form.html', {'form': form, 'org': org, 'action': 'Add'})


@login_required
def edit_service(request, pk):
    org = request.user.organization
    if not org:
        messages.error(request, 'Your account is not attached to a business profile.')
        return redirect('dashboard')
    svc = get_object_or_404(Service, pk=pk, organization=org)
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=svc)
        if form.is_valid():
            svc = form.save()
            cleared_fields = []
            for field_name in ('image', 'image2', 'banner_image', 'before_image', 'after_image'):
                if request.POST.get(f'clear_{field_name}') == '1':
                    setattr(svc, field_name, None)
                    cleared_fields.append(field_name)
            if cleared_fields:
                svc.save(update_fields=cleared_fields)
            messages.success(request, 'Service updated.')
            return redirect('manage_services')
        messages.error(request, 'The service was not saved. Correct the highlighted fields below.')
    else:
        form = ServiceForm(instance=svc)
    return render(request, 'service_form.html', {'form': form, 'org': org, 'action': 'Edit'})


@login_required
def delete_service(request, pk):
    org = request.user.organization
    svc = get_object_or_404(Service, pk=pk, organization=org)
    svc.delete()
    messages.success(request, 'Service deleted.')
    return redirect('manage_services')


@login_required
def enquiries_list(request):
    user = request.user
    status_filter = request.GET.get('status', '')

    if user.is_super_admin:
        enquiries = Enquiry.objects.select_related('organization').all()
        org = None
        page_org_name = 'All organizations'
    else:
        org = user.organization
        enquiries = org.enquiries.select_related('service').all() if org else Enquiry.objects.none()
        page_org_name = org.name if org else ''

    if status_filter:
        enquiries = enquiries.filter(status=status_filter)

    return render(request, 'enquiries.html', {
        'enquiries': enquiries,
        'org': org,
        'org_name': page_org_name,
        'status_filter': status_filter,
        'enquiry_statuses': Enquiry.STATUS_CHOICES,
        'show_org_column': user.is_super_admin,
    })

from django.http import JsonResponse
import logging
logger = logging.getLogger(__name__)

@login_required
def update_enquiry_status(request, pk):
    logger.error(f"HIT update_enquiry_status pk={pk} method={request.method} POST={request.POST}")
    print(f"HIT update_enquiry_status pk={pk} method={request.method} POST={request.POST}")
    user = request.user
    if user.is_super_admin:
        enq = get_object_or_404(Enquiry, pk=pk)
    else:
        org = user.organization
        enq = get_object_or_404(Enquiry, pk=pk, organization=org)

    if request.method == 'POST':
        enq.status = request.POST.get('status', enq.status)
        enq.notes = request.POST.get('notes', enq.notes)
        enq.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True})
        messages.success(request, 'Enquiry updated.')
    return redirect('enquiries')

# ── PRODUCTS ──────────────────────────────────────────────────────────────────

@login_required
def manage_products(request):
    org = request.user.organization
    if not org:
        return redirect('dashboard')
    q = request.GET.get('q', '')
    cat = request.GET.get('cat', '')
    products = org.products.all()
    if q:
        products = products.filter(name__icontains=q)
    if cat:
        products = products.filter(category__icontains=cat)
    categories = org.products.values_list('category', flat=True).distinct().exclude(category='')
    paginator = Paginator(products, 12)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'manage_products.html', {
        'org': org,
        'page_obj': page,
        'categories': categories,
        'q': q,
        'cat': cat,
        'total': org.products.count(),
        'in_stock': org.products.filter(in_stock=True).count(),
    })


@login_required
def add_product(request):
    org = request.user.organization
    if not org:
        messages.error(request, 'Your account is not attached to a business profile.')
        return redirect('dashboard')
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.organization = org
            product.save()
            messages.success(request, f'Product "{product.name}" added successfully.')
            return redirect('manage_products')
        messages.error(request, 'The product was not saved. Correct the highlighted fields below.')
    else:
        form = ProductForm()
    return render(request, 'product_form.html', {
        'form': form, 'org': org, 'action': 'Add New'
    })


@login_required
def edit_product(request, pk):
    org = request.user.organization
    if not org:
        messages.error(request, 'Your account is not attached to a business profile.')
        return redirect('dashboard')
    product = get_object_or_404(Product, pk=pk, organization=org)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated.')
            return redirect('manage_products')
        messages.error(request, 'The product was not saved. Correct the highlighted fields below.')
    else:
        form = ProductForm(instance=product)
    return render(request, 'product_form.html', {
        'form': form, 'org': org, 'action': 'Edit', 'product': product
    })


@login_required
def delete_product(request, pk):
    org = request.user.organization
    product = get_object_or_404(Product, pk=pk, organization=org)
    name = product.name
    product.delete()
    messages.success(request, f'Product "{name}" deleted.')
    return redirect('manage_products')


@login_required
def toggle_product_stock(request, pk):
    """Quick toggle in/out of stock via AJAX or form post"""
    org = request.user.organization
    product = get_object_or_404(Product, pk=pk, organization=org)
    product.in_stock = not product.in_stock
    product.save()
    status = 'In Stock' if product.in_stock else 'Out of Stock'
    messages.success(request, f'{product.name} marked as {status}.')
    return redirect('manage_products')

@login_required
def org_settings(request):
    org_id = getattr(request.user, 'organization_id', None)

    if not org_id:
        messages.error(request, 'Organization account not found.')
        return redirect('dashboard')

    org = get_object_or_404(Organization, pk=org_id)

    if request.method == 'POST':
        form = OrganizationUpdateForm(
            request.POST,
            request.FILES,
            instance=org,
        )

        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Organization settings updated successfully.'
            )
            return redirect('org_settings')

        messages.error(
            request,
            'Settings were not saved. Please correct the errors below.'
        )
    else:
        form = OrganizationUpdateForm(instance=org)

    return render(request, 'org_settings.html', {
        'form': form,
        'org': org,
    })


# ══════════════════════════════════════════════════════════════
#  REFERRAL SYSTEM
# ══════════════════════════════════════════════════════════════
from .models import ReferralCode, Referral, ReferralBonus, ReferralProgram
from django.utils import timezone


def _get_or_create_referral_code(org):
    """Get or lazily create a referral code for an org."""
    try:
        return org.referral_code
    except ReferralCode.DoesNotExist:
        code = ReferralCode.generate_code()
        while ReferralCode.objects.filter(code=code).exists():
            code = ReferralCode.generate_code()
        return ReferralCode.objects.create(organization=org, code=code)


def signup_with_ref(request, ref_code):
    """Legacy referral URL routed through the same approval-safe workflow."""
    from django.db.models import F

    ref = ReferralCode.objects.select_related('organization').filter(code=ref_code).first()
    if ref and request.method == 'GET':
        ReferralCode.objects.filter(pk=ref.pk).update(total_clicks=F('total_clicks') + 1)

    if request.user.is_authenticated:
        return redirect('dashboard')

    categories = BusinessCategory.objects.all()
    form = OrganizationSignupForm()

    if request.method == 'POST':
        form = OrganizationSignupForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                org, user, invite = _create_pending_signup(
                    request,
                    form,
                )
                messages.success(
                    request,
                    f'{org.name} was submitted for approval. '
                    'Rewards are available only through phone-bound WhatsApp invitations.',
                )
                return redirect('onboard_pending_review', token=invite.token)
            except Exception as e:
                messages.error(request, 'Registration failed. Please review the details and try again.')
        else:
            messages.error(request, 'Please fix the errors below.')

    return render(request, 'signup.html', {
        'form': form,
        'categories': categories,
        'ref_code': ref_code,
        'referrer_org': ref.organization if ref else None,
    })


@login_required
def referral_dashboard(request):
    """Keep old bookmarks working while enforcing WhatsApp-only invitations."""
    return redirect('member_send_invite')


# ════════════════════════════════════════════════════════════════
#  ADD TO views.py  — Admin "Add Member" two-step flow
#  Place this block after the existing imports / views
# ════════════════════════════════════════════════════════════════

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from .forms import AddMemberStep1Form, AddMemberStep2Form
from .models import (
    Organization, CustomUser, BusinessCategory,
    SubCategory, Plan, Service
)


# ── AJAX: load sub-categories for a given main category ──────────────────────
def load_sub_categories(request):
    """
    Called by the Step-1 form via AJAX when user changes Main Category.
    Returns JSON list of sub-categories.

    URL: /ajax/subcategories/?category_id=<id>
    """
    cat_id = request.GET.get('category_id')
    subs = SubCategory.objects.filter(
        main_category_id=cat_id, is_active=True
    ).values('id', 'name').order_by('order', 'name')
    return JsonResponse({'sub_categories': list(subs)})


# ── Main two-step Add Member view ─────────────────────────────────────────────
@login_required
def add_member(request):
    """
    Two-step wizard for Admin Staff to create a new member (Organisation + User).

    Step 1: Site URL (subdomain), Site Title, Main Category, Sub Category, Plan
    Step 2: Full contact/account details

    Session keys used:
        add_member_step1  — cleaned Step-1 data (dict)
    """
    if not request.user.is_super_admin:
        messages.error(request, 'Access denied. Super Admin only.')
        return redirect('dashboard')

    # ── Step determination ────────────────────────────────────────
    step = request.POST.get('step') or request.GET.get('step', '1')

    # ── Step 1 POST ───────────────────────────────────────────────
    if request.method == 'POST' and step == '1':
        form1 = AddMemberStep1Form(request.POST)
        form2 = AddMemberStep2Form()
        if form1.is_valid():
            request.session['add_member_step1'] = {
                'site_url':      form1.cleaned_data['site_url'],
                'site_title':    form1.cleaned_data['site_title'],
                'main_category': form1.cleaned_data['main_category'].pk,
                'sub_category':  (
                    form1.cleaned_data['sub_category'].pk
                    if form1.cleaned_data.get('sub_category') else None
                ),
                'plan': form1.cleaned_data['plan'].pk,
            }
            return render(request, 'add_member.html', {
                'form1': form1,
                'form2': form2,
                'current_step': 2,
                'step1_data': form1.cleaned_data,
            })
        else:
            return render(request, 'add_member.html', {
                'form1': form1,
                'form2': AddMemberStep2Form(),
                'current_step': 1,
            })

    # ── Step 2 POST (final submit) ────────────────────────────────
    elif request.method == 'POST' and step == '2':
        step1_session = request.session.get('add_member_step1')
        if not step1_session:
            messages.warning(request, 'Session expired. Please start again.')
            return redirect('add_member')

        form2 = AddMemberStep2Form(request.POST, request.FILES)
        form1 = AddMemberStep1Form()

        if form2.is_valid():
            try:
                with transaction.atomic():
                    cd = form2.cleaned_data
                    s1 = step1_session

                    # ── Resolve FK objects ────────────────────────
                    main_cat = BusinessCategory.objects.get(pk=s1['main_category'])
                    sub_cat  = (
                        SubCategory.objects.get(pk=s1['sub_category'])
                        if s1.get('sub_category') else None
                    )
                    plan_obj = Plan.objects.get(pk=s1['plan'])

                    # ── Create Organisation ───────────────────────
                    org = Organization.objects.create(
                        name          = cd['company_name'],
                        subdomain     = s1['site_url'],
                        category      = main_cat,
                        sub_category  = sub_cat,
                        plan          = plan_obj,
                        plan_start_date = cd.get('plan_start_date'),
                        plan_end_date   = cd.get('plan_end_date'),
                        email         = cd['email'],
                        phone         = cd['mobile'],
                        whatsapp      = cd.get('whatsapp', ''),
                        landline      = cd.get('landline', ''),
                        website       = cd.get('website', ''),
                        address_line1 = cd['address'],
                        city          = cd['city'],
                        district      = cd.get('district', ''),
                        state         = cd['state'],
                        pincode       = cd['pincode'],
                        status        = cd.get('status', 'active'),
                        file_attachment = cd.get('file_attachment'),
                        is_active     = (cd.get('status', 'active') == 'active'),
                    )

                    # ── Auto-generate username if blank ───────────
                    username = cd.get('username') or \
                               cd['email'].split('@')[0].replace('.', '_').replace('+', '_')
                    base_uname = username
                    counter = 1
                    while CustomUser.objects.filter(username=username).exists():
                        username = f"{base_uname}{counter}"
                        counter += 1

                    # ── Parse first / last name ───────────────────
                    name_parts = cd['contact_name'].strip().split(' ', 1)
                    first_name = name_parts[0]
                    last_name  = name_parts[1] if len(name_parts) > 1 else ''

                    # ── Create User ───────────────────────────────
                    user = CustomUser.objects.create_user(
                        username     = username,
                        email        = cd['email'],
                        password     = cd['password'],
                        first_name   = first_name,
                        last_name    = last_name,
                        phone        = cd['mobile'],
                        landline     = cd.get('landline', ''),
                        gender       = cd.get('gender', 'male'),
                        date_of_birth = cd.get('date_of_birth'),
                        organization = org,
                        role         = cd.get('user_role', 'org_admin'),
                    )
                    if cd.get('profile_picture'):
                        user.profile_pic = cd['profile_picture']
                        user.save()

                    # ── Pre-fill services from category template ──
                    for i, svc_name in enumerate(main_cat.default_services):
                        Service.objects.create(
                            organization = org,
                            name         = svc_name,
                            icon         = main_cat.icon,
                            order        = i,
                            is_featured  = (i < 3),
                        )

                    # ── Clear session ─────────────────────────────
                    if 'add_member_step1' in request.session:
                        del request.session['add_member_step1']

                    messages.success(
                        request,
                        f'Member "{org.name}" created successfully! '
                        f'Login: {username} | Plan: {plan_obj.name}'
                    )
                    return redirect('member_list')   # or 'dashboard'

            except Exception as e:
                messages.error(request, f'Member creation failed: {str(e)}')
        else:
            # Re-render Step 2 with errors
            step1_data = {}
            if step1_session:
                try:
                    step1_data['main_category'] = BusinessCategory.objects.get(pk=step1_session['main_category'])
                    step1_data['sub_category']  = (
                        SubCategory.objects.get(pk=step1_session['sub_category'])
                        if step1_session.get('sub_category') else None
                    )
                    step1_data['plan']       = Plan.objects.get(pk=step1_session['plan'])
                    step1_data['site_url']   = step1_session['site_url']
                    step1_data['site_title'] = step1_session['site_title']
                except Exception:
                    pass

        return render(request, 'add_member.html', {
            'form1': form1,
            'form2': form2,
            'current_step': 2,
            'step1_data': step1_data,
        })

    # ── GET: show Step 1 ──────────────────────────────────────────
    else:
        # Clear any stale session
        if 'add_member_step1' in request.session:
            del request.session['add_member_step1']
        return render(request, 'add_member.html', {
            'form1': AddMemberStep1Form(),
            'form2': AddMemberStep2Form(),
            'current_step': 1,
        })


# ── Member List (Super Admin) ─────────────────────────────────────────────────
@login_required
def member_list(request):
    """Super admin view of all member organisations."""
    if not request.user.is_super_admin:
        return redirect('dashboard')

    from django.core.paginator import Paginator

    q      = request.GET.get('q', '')
    plan   = request.GET.get('plan', '')
    status = request.GET.get('status', '')

    orgs = Organization.objects.select_related(
        'category', 'sub_category', 'plan'
    ).order_by('-created_at')

    if q:
        orgs = orgs.filter(name__icontains=q)
    if plan:
        orgs = orgs.filter(plan__level=plan)
    if status:
        orgs = orgs.filter(status=status)

    paginator = Paginator(orgs, 15)
    page      = paginator.get_page(request.GET.get('page'))

    return render(request, 'member_list.html', {
        'page_obj':       page,
        'plans':          Plan.objects.filter(is_active=True),
        'status_choices': Organization.STATUS_CHOICES,
        'q': q, 'plan': plan, 'status': status,
        'total': orgs.count(),
    })


# ── Edit Member ───────────────────────────────────────────────────────────────
@login_required
def edit_member(request, pk):
    """Super admin edit for an existing organisation/member."""
    if not request.user.is_super_admin:
        return redirect('dashboard')

    from .forms import OrganizationUpdateForm
    org = get_object_or_404(Organization, pk=pk)

    if request.method == 'POST':
        form = OrganizationUpdateForm(request.POST, request.FILES, instance=org)
        if form.is_valid():
            form.save()
            messages.success(request, f'Member "{org.name}" updated.')
            return redirect('member_list')
    else:
        form = OrganizationUpdateForm(instance=org)

    return render(request, 'edit_member.html', {'form': form, 'org': org})


def register_super_admin(request):
    active_super_admins = CustomUser.objects.filter(is_active=True).filter(
        Q(role='super_admin') | Q(is_superuser=True)
    )
    already_exists = active_super_admins.exists()
    current_user_can_create = (
        request.user.is_authenticated and request.user.is_super_admin
    )

    if already_exists and not current_user_can_create:
        return render(
            request,
            'superadmin_setup_locked.html',
            {'signed_in_as_other_role': request.user.is_authenticated},
            status=403,
        )

    form = SuperAdminRegisterForm()

    if request.method == 'POST':
        form = SuperAdminRegisterForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = CustomUser.objects.create_user(
                username   = cd['username'],
                email      = cd['email'],
                password   = cd['password1'],
                first_name = cd['first_name'],
                last_name  = cd.get('last_name', ''),
                phone      = cd.get('phone', ''),
                role       = 'super_admin',
                is_staff   = True,
            )
            messages.success(request, f'Super Admin "{user.username}" created successfully!')
            if not request.user.is_authenticated:
                login(request, user)
                return redirect('dashboard')
            return redirect('member_list')

    return render(request, 'register_superadmin.html', {
        'form': form,
        'already_exists': already_exists,
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
 
from .models import (
    InvitationToken, Organization, CustomUser,
    BusinessCategory, SubCategory, Plan, Service,
    VisitingCard, WhatsAppConfig,
)

# Import feature-specific views (payment QR, visiting card, supply chain, etc.)
from .views_features import (
    visiting_card, download_vcard, edit_visiting_card,
    manage_payment_qr, add_payment_qr, delete_payment_qr,
    edit_whatsapp_config, supply_chain_view, link_supply_chain, update_chain_link,
    discovery_home, discovery_category,
)

from .views_member_invite import (
    member_send_invite, member_invite_list,
    member_resend_invite, member_revoke_invite,
    _award_member_invite_bonus,
)
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  STEP 1 — Super Admin sends invitation
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def invite_member(request):
    """Super Admin fills email + pre-assigns plan/category → invitation email sent."""
    if not request.user.is_super_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        email      = request.POST.get('email', '').strip().lower()
        plan_id    = request.POST.get('plan', '').strip()
        cat_id     = request.POST.get('main_category', '').strip()
        subcat_id  = request.POST.get('sub_category', '').strip() or None
        subdomain  = request.POST.get('subdomain', '').strip() or None
        site_title = request.POST.get('site_title', '').strip()

        # ── Validation — only email is required, everything else is optional ──
        errors = []
        if not email:
            errors.append('Email is required.')
        if email and InvitationToken.objects.filter(email=email, status='pending').exists():
            errors.append(f'A pending invitation already exists for {email}.')
        if email and Organization.objects.filter(email=email).exists():
            errors.append(f'{email} is already a registered member.')
        if subdomain and Organization.objects.filter(subdomain=subdomain).exists():
            errors.append(f'Subdomain "{subdomain}" is already taken.')

        if errors:
            for e in errors:
                messages.error(request, e)
            # Re-render with submitted values preserved
            context = {
                'plans':      Plan.objects.filter(is_active=True).order_by('order'),
                'categories': BusinessCategory.objects.all(),
                'form_data':  request.POST,
            }
            return render(request, 'invite_member.html', context)

        # ── Safe lookups — empty string → None, never passed to pk filter ────
        plan   = Plan.objects.filter(pk=plan_id).first()            if plan_id   else None
        cat    = BusinessCategory.objects.filter(pk=cat_id).first() if cat_id    else None
        subcat = SubCategory.objects.filter(pk=subcat_id).first()   if subcat_id else None

        invite = InvitationToken.objects.create(
            invited_by    = request.user,
            email         = email,
            plan          = plan,
            main_category = cat,
            sub_category  = subcat,
            subdomain     = subdomain,
            site_title    = site_title,
        )
        _send_invitation_email(invite, request)
        messages.success(request, f'Invitation sent to {email} ✓')
        return redirect('invitation_list')

    context = {
        'plans':      Plan.objects.filter(is_active=True).order_by('order'),
        'categories': BusinessCategory.objects.all(),
    }
    return render(request, 'invite_member.html', context) 


def _send_invitation_email(invite: InvitationToken, request):
    """Send the magic-link email to the invited person."""
    onboard_url = invite.get_onboard_url(request)
    subject = f"You're invited to join Portal — Complete your profile"
 
    # Plain-text body (also send HTML version below)
    body = (
        f"Hello,\n\n"
        f"You have been invited to join Portal by {invite.invited_by.get_full_name() or invite.invited_by.username}.\n\n"
        f"Click the link below to complete your profile and set your password:\n\n"
        f"{onboard_url}\n\n"
        f"This link expires in 7 days.\n\n"
        f"If you did not expect this invitation, you can ignore this email.\n\n"
        f"— Portal Team"
    )
 
    # Try HTML template first; fall back to plain text
    try:
        html_body = render_to_string('emails/invitation.html', {
            'invite':      invite,
            'onboard_url': onboard_url,
        })
    except Exception:
        html_body = None
 
    send_mail(
        subject      = subject,
        message      = body,
        from_email   = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@Portal.com'),
        recipient_list = [invite.email],
        html_message = html_body,
        fail_silently = False,
    )
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2 — Invited person accepts & fills in details
# ─────────────────────────────────────────────────────────────────────────────
 
def onboard_accept(request, token):
    """
    Public view — the magic link from the email.
    The user completes their org profile and sets a password.
    """
    invite = get_object_or_404(InvitationToken, token=token)
 
    # Guard: token must be valid
    if not invite.is_valid:
        return render(request, 'onboard_invalid.html', {
            'reason': 'expired' if invite.status == 'pending' else invite.status
        })
 
    if request.method == 'POST':
        errors = _validate_onboard_form(request.POST)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            try:
                with transaction.atomic():
                    org, user = _create_org_and_user_from_onboard(request.POST, request.FILES, invite)
 
                    # Mark invitation accepted
                    invite.status       = 'accepted'
                    invite.accepted_at  = timezone.now()
                    invite.organization = org
                    invite.save()
                    _award_member_invite_bonus(invite)   # ← award bonus if member invite
 
                    from django.contrib.auth import login as auth_login
                    auth_login(request, user)
                    messages.success(
                        request,
                        f'Welcome to Portal, {org.name}! Your account is ready.'
                    )
                    return redirect('onboard_done', token=token)
 
            except Exception as exc:
                messages.error(request, 'Setup failed. Please review the details and try again.')
 
    context = {
        'invite':  invite,
        'plan':    invite.plan,
        'cat':     invite.main_category,
        'subcat':  invite.sub_category,
    }
    return render(request, 'onboard_accept.html', context)
 
 
def onboard_done(request, token):
    """Success page after onboarding."""
    invite = get_object_or_404(InvitationToken, token=token)
    return render(request, 'onboard_done.html', {'invite': invite, 'org': invite.organization})
 
 
def _validate_onboard_form(data: dict, invite=None) -> list:
    errors = []
    required = [
        ('company_name', 'Company / Business name'),
        ('contact_name', 'Your full name'),
        ('mobile',       'Mobile number'),
        ('address',      'Address'),
        ('city',         'City'),
        ('state',        'State'),
        ('pincode',      'Pincode'),
        ('password',     'Password'),
        ('password2',    'Confirm password'),
    ]
    for field, label in required:
        if not data.get(field, '').strip():
            errors.append(f'{label} is required.')

    account_email = (getattr(invite, 'email', '') or data.get('email', '')).strip().lower()
    if not account_email:
        errors.append('Email address is required.')
    elif CustomUser.objects.filter(email__iexact=account_email).exists():
        errors.append('An account with this email already exists.')

    if invite and invite.phone and data.get('mobile'):
        try:
            if normalize_indian_phone(data['mobile']) != invite.phone:
                errors.append(
                    'Use the same mobile number that received the WhatsApp invitation.'
                )
        except ValueError as exc:
            errors.append(str(exc))
 
    if data.get('password') and data.get('password2'):
        if data['password'] != data['password2']:
            errors.append('Passwords do not match.')
        if len(data['password']) < 8:
            errors.append('Password must be at least 8 characters.')
 
    if data.get('pincode') and not data['pincode'].strip().isdigit():
        errors.append('Pincode must be numeric.')
 
    return errors
 
 
def _create_org_and_user_from_onboard(data, files, invite: InvitationToken):
    """Create Organization + CustomUser from the onboarding form POST data."""
    from django.utils.text import slugify
 
    # ── Organisation ─────────────────────────────────────
    org = Organization.objects.create(
        name          = data['company_name'].strip(),
        subdomain     = invite.subdomain or slugify(data['company_name']),
        category      = invite.main_category,
        sub_category  = invite.sub_category,
        plan          = invite.plan,
        plan_start_date = timezone.now().date(),
        plan_end_date   = (
            timezone.now().date() + timezone.timedelta(days=invite.plan.duration_days)
            if invite.plan else None
        ),
        email         = invite.email,
        phone         = data.get('mobile', '').strip(),
        whatsapp      = data.get('whatsapp', '').strip(),
        landline      = data.get('landline', '').strip(),
        website       = data.get('website', '').strip(),
        tagline       = data.get('tagline', '').strip(),
        description   = data.get('description', '').strip(),
        address_line1 = data.get('address', '').strip(),
        address_line2 = data.get('address2', '').strip(),
        city          = data.get('city', '').strip(),
        district      = data.get('district', '').strip(),
        state         = data.get('state', '').strip(),
        pincode       = data.get('pincode', '').strip(),
        status        = 'active',
        is_active     = True,
    )
 
    # Upload logo if provided
    if files.get('logo'):
        org.logo = files['logo']
        org.save(update_fields=['logo'])
 
    # ── Default services from category template ───────────
    if invite.main_category:
        for i, svc_name in enumerate(invite.main_category.default_services):
            Service.objects.create(
                organization = org,
                name         = svc_name,
                icon         = invite.main_category.icon,
                order        = i,
                is_featured  = (i < 3),
            )
 
    # ── Auto-create visiting card & WhatsApp config ───────
    VisitingCard.objects.create(
        organization = org,
        contact_name = data.get('contact_name', '').strip(),
        designation  = data.get('designation', '').strip(),
    )
    whatsapp_number = data.get('whatsapp', '') or data.get('mobile', '')
    if whatsapp_number:
        WhatsAppConfig.objects.create(
            organization    = org,
            whatsapp_number = whatsapp_number.strip().replace('+', '').replace(' ', ''),
        )
 
    # ── User account ──────────────────────────────────────
    email_local = invite.email.split('@')[0].replace('.', '_').replace('+', '_')
    username = email_local
    counter  = 1
    while CustomUser.objects.filter(username=username).exists():
        username = f"{email_local}{counter}"
        counter += 1
 
    name_parts = data.get('contact_name', '').strip().split(' ', 1)
    user = CustomUser.objects.create_user(
        username     = username,
        email        = invite.email,
        password     = data['password'],
        first_name   = name_parts[0],
        last_name    = name_parts[1] if len(name_parts) > 1 else '',
        phone        = data.get('mobile', '').strip(),
        landline     = data.get('landline', '').strip(),
        gender       = data.get('gender', 'male'),
        organization = org,
        role         = 'org_admin',
    )
 
    if files.get('profile_photo'):
        user.profile_pic = files['profile_photo']
        user.save(update_fields=['profile_pic'])
 
    return org, user
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  INVITATION MANAGEMENT (Super Admin)
# ─────────────────────────────────────────────────────────────────────────────
 
@login_required
def invitation_list(request):
    if not request.user.is_super_admin:
        return redirect('dashboard')
 
    from django.core.paginator import Paginator
    invites = InvitationToken.objects.select_related(
        'invited_by', 'plan', 'main_category', 'organization'
    ).order_by('-created_at')
 
    status_filter = request.GET.get('status', '')
    if status_filter:
        invites = invites.filter(status=status_filter)
 
    paginator = Paginator(invites, 20)
    page = paginator.get_page(request.GET.get('page'))
 
    return render(request, 'invitation_list.html', {
        'page_obj': page,
        'status_filter': status_filter,
        'status_choices': InvitationToken.STATUS_CHOICES,
    })
 


@login_required
def delete_invitation(request, pk):
    if not request.user.is_super_admin:
        return redirect('dashboard')

    invite = get_object_or_404(InvitationToken, pk=pk)

    if request.method == 'POST':
        invite.delete()
        messages.success(request, f"Invitation to {invite.email} has been deleted.")
        return redirect('invitation_list')

    # GET → show confirmation page
    return render(request, 'invitation_confirm_delete.html', {'invite': invite})
 
@login_required
def resend_invitation(request, pk):
    if not request.user.is_super_admin:
        return redirect('dashboard')
    invite = get_object_or_404(InvitationToken, pk=pk)
    if invite.status == 'pending':
        invite.expires_at = timezone.now() + timezone.timedelta(days=7)
        invite.save(update_fields=['expires_at'])
        _send_invitation_email(invite, request)
        messages.success(request, f'Invitation resent to {invite.email}.')
    else:
        messages.warning(request, 'Only pending invitations can be resent.')
    return redirect('invitation_list')
 
 
@login_required
def revoke_invitation(request, pk):
    if not request.user.is_super_admin:
        return redirect('dashboard')
    invite = get_object_or_404(InvitationToken, pk=pk)
    invite.status = 'revoked'
    invite.save(update_fields=['status'])
    messages.success(request, f'Invitation for {invite.email} revoked.')
    return redirect('invitation_list')


# Visiting card edit (dashboard)
@login_required
def edit_visiting_card(request):
    """Edit or create the organization's visiting card (handles POST updates).

    For GET requests this redirects to the organization settings page to avoid
    introducing a new template during the quick fix.
    """
    org = getattr(request.user, 'organization', None)
    if not org:
        return redirect('dashboard')

    card, _ = VisitingCard.objects.get_or_create(organization=org)

    if request.method == 'POST':
        # Accept common card fields from the form
        fields = [
            'contact_name', 'designation', 'tagline',
            'direct_phone', 'direct_whatsapp', 'direct_email',
            'linkedin_url', 'instagram_url', 'twitter_url', 'youtube_url',
            'theme',
        ]
        for f in fields:
            if f in request.POST:
                setattr(card, f, request.POST.get(f) or '')

        if request.FILES.get('profile_photo'):
            card.profile_photo = request.FILES.get('profile_photo')

        # Toggle active if provided
        if 'is_active' in request.POST:
            card.is_active = request.POST.get('is_active') in ['1', 'true', 'True', 'on']

        card.save()
        messages.success(request, 'Visiting card updated.')
        return redirect('org_settings')

    return redirect('org_settings')



from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
 
from .models import Organization, Product, Service, Cart, CartItem, Enquiry
 
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def _ensure_session_key(request):
    """Make sure the session has a key (creates one if needed)."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key
 
 
def _get_or_create_cart(request, org: Organization) -> Cart:
    """
    Get the active cart for this session + org, or create one.
    If the session has an active cart for a DIFFERENT org, abandon it first.
    """
    sk = _ensure_session_key(request)
 
    # Try to reuse existing active cart for this org + session
    cart = Cart.objects.filter(
        session_key=sk, organization=org, status='active'
    ).first()
 
    if not cart:
        # Abandon any stale cart for a different org in this session
        Cart.objects.filter(session_key=sk, status='active').update(status='abandoned')
        cart = Cart.objects.create(session_key=sk, organization=org)
 
    return cart
 
 
def _get_cart(request, org: Organization):
    """Return existing active cart or None."""
    sk = _ensure_session_key(request)
    return Cart.objects.filter(
        session_key=sk, organization=org, status='active'
    ).prefetch_related('items__product', 'items__service').first()
 
 
def _cart_to_dict(cart) -> dict:
    """Serialise cart to a dict for JSON responses."""
    if not cart:
        return {'item_count': 0, 'total': '0.00', 'items': []}
 
    items = []
    for item in cart.items.select_related('product', 'service'):
        img_url = ''
        if item.display_image:
            try:
                img_url = item.display_image.url
            except Exception:
                pass
        items.append({
            'id':          item.pk,
            'name':        item.display_name,
            'type':        item.item_type,
            'quantity':    item.quantity,
            'unit_price':  str(item.unit_price or 0),
            'line_total':  str(item.line_total),
            'image':       img_url,
            'note':        item.note,
        })
 
    return {
        'item_count': cart.item_count,
        'total':      str(cart.total),
        'items':      items,
    }
 
 
# ── VIEWS ─────────────────────────────────────────────────────────────────────
 
@require_POST
def cart_add(request, slug):
    """
    Add a product or service to the cart.
    Accepts POST with:
      product_id  OR  service_id
      quantity    (default 1)
      note        (optional customer note)
    Returns JSON for AJAX calls; redirects for plain form posts.
    """
    org     = get_object_or_404(Organization, slug=slug, is_active=True)
    cart    = _get_or_create_cart(request, org)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.content_type == 'application/json'
 
    product_id  = request.POST.get('product_id')
    service_id  = request.POST.get('service_id')
    quantity    = max(1, int(request.POST.get('quantity', 1)))
    note        = request.POST.get('note', '').strip()
 
    added_name = ''
 
    if product_id:
        product = get_object_or_404(Product, pk=product_id, organization=org, is_active=True)
 
        # Update quantity if already in cart, else create
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': quantity, 'note': note}
        )
        if not created:
            item.quantity = min(item.quantity + quantity, 99)
            if note:
                item.note = note
            item.save()
 
        added_name = product.name
 
    elif service_id:
        service = get_object_or_404(Service, pk=service_id, organization=org, is_active=True)
 
        item, created = CartItem.objects.get_or_create(
            cart=cart, service=service,
            defaults={'quantity': quantity, 'note': note}
        )
        if not created:
            item.quantity = min(item.quantity + quantity, 99)
            if note:
                item.note = note
            item.save()
 
        added_name = service.name
 
    else:
        if is_ajax:
            return JsonResponse({'ok': False, 'error': 'No item specified'}, status=400)
        return redirect('public_landing', slug=slug)
 
    # Refresh cart from DB
    cart.refresh_from_db()
 
    if is_ajax:
        return JsonResponse({
            'ok':        True,
            'message':   f'"{added_name}" added to cart.',
            'cart':      _cart_to_dict(cart),
        })
 
    return redirect('public_landing', slug=slug)
 
 
@require_POST
def cart_update(request, slug, item_pk):
    """Update quantity of a cart item. qty=0 removes it."""
    org  = get_object_or_404(Organization, slug=slug, is_active=True)
    cart = _get_cart(request, org)
 
    if not cart:
        return JsonResponse({'ok': False, 'error': 'No cart'}, status=404)
 
    item = get_object_or_404(CartItem, pk=item_pk, cart=cart)
    qty  = int(request.POST.get('quantity', 1))
 
    if qty <= 0:
        item.delete()
    else:
        item.quantity = min(qty, 99)
        item.note     = request.POST.get('note', item.note).strip()
        item.save()
 
    cart.refresh_from_db()
    return JsonResponse({'ok': True, 'cart': _cart_to_dict(cart)})
 
 
@require_POST
def cart_remove(request, slug, item_pk):
    """Remove a single item from the cart."""
    org  = get_object_or_404(Organization, slug=slug, is_active=True)
    cart = _get_cart(request, org)
 
    if not cart:
        return JsonResponse({'ok': False, 'error': 'No cart'}, status=404)
 
    item = get_object_or_404(CartItem, pk=item_pk, cart=cart)
    item.delete()
 
    cart.refresh_from_db()
    return JsonResponse({'ok': True, 'cart': _cart_to_dict(cart)})
 
 
@require_POST
def cart_clear(request, slug):
    """Empty the cart entirely."""
    org  = get_object_or_404(Organization, slug=slug, is_active=True)
    cart = _get_cart(request, org)
    if cart:
        cart.items.all().delete()
    return JsonResponse({'ok': True, 'cart': {'item_count': 0, 'total': '0.00', 'items': []}})
 
 
def cart_json(request, slug):
    """Return the current cart state as JSON (for page-load hydration)."""
    org  = get_object_or_404(Organization, slug=slug, is_active=True)
    cart = _get_cart(request, org)
    return JsonResponse({'cart': _cart_to_dict(cart)})
 
 
@require_POST
def cart_checkout(request, slug):
    """
    Convert the cart into an Enquiry and (optionally) open WhatsApp.
    POST fields:
      name, email, phone  — required for the enquiry
      checkout_type       — 'enquiry' (default) | 'whatsapp'
    """
    org  = get_object_or_404(Organization, slug=slug, is_active=True)
    cart = _get_cart(request, org)
 
    if not cart or cart.item_count == 0:
        return JsonResponse({'ok': False, 'error': 'Cart is empty'}, status=400)
 
    name  = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
 
    if not all([name, phone]):
        return JsonResponse({'ok': False, 'error': 'Name and phone are required.'}, status=400)
 
    # Build subject and message from cart items
    items_text = "\n".join(
        f"- {item.display_name} × {item.quantity} @ ₹{item.unit_price or 0}"
        for item in cart.items.all()
    )
    subject = f"Cart Order — {cart.item_count} item(s) — ₹{cart.total}"
    message = f"Order details:\n{items_text}\n\nTotal: ₹{cart.total}"
 
    enquiry = Enquiry.objects.create(
        organization = org,
        name         = name,
        email        = email or 'noemail@provided.com',
        phone        = phone,
        subject      = subject,
        message      = message,
        status       = 'new',
    )
 
    # Link enquiry to cart and close cart
    cart.enquiry = enquiry
    cart.status  = 'checkout'
    cart.save(update_fields=['enquiry', 'status'])
 
    # Build WhatsApp URL
    wa_number = org.whatsapp or org.phone
    wa_url = ''
    if wa_number:
        wa_url = f"https://wa.me/91{wa_number.replace(' ','').replace('+','')}?text={cart.get_whatsapp_summary(org.name)}"
 
    return JsonResponse({
        'ok':          True,
        'enquiry_id':  enquiry.pk,
        'wa_url':      wa_url,
        'message':     'Your enquiry has been submitted!',
    })
 
 
def cart_view(request, slug):
    """Full cart page (fallback for non-JS)."""
    org  = get_object_or_404(Organization, slug=slug, is_active=True)
    cart = _get_cart(request, org)
    return render(request, 'cart.html', {'org': org, 'cart': cart})



@login_required
def member_delete_invite(request, pk):
    """Hard-delete a member-sent InvitationToken belonging to this org."""
    org = request.user.organization
    if not org:
        return redirect('dashboard')

    # Only allow deletion of invites THIS org sent (invite_type='member')
    invite = get_object_or_404(
        InvitationToken,
        pk=pk,
        referred_by_org=org,
        invite_type='member'
    )

    if request.method == 'POST':
        recipient = invite.email or f'+{invite.phone}'
        invite.delete()
        messages.success(request, f'Invitation for {recipient} has been deleted.')

    return redirect('member_invite_list')


@login_required
@require_POST
def org_soft_delete(request, pk):
    """
    Soft-delete: sets status='inactive' and is_active=False.
    Hard data (enquiries, products, etc.) is preserved.
    Triggered by a modal confirm form — POST only.
    """
    if not request.user.is_super_admin:
        return JsonResponse({'ok': False, 'error': 'Access denied.'}, status=403)
 
    org = get_object_or_404(Organization, pk=pk)
 
    # Prevent deleting the org the current super admin belongs to (safety guard)
    if request.user.organization and request.user.organization.pk == pk:
        messages.error(request, 'You cannot deactivate your own organisation.')
        return redirect('member_list')
 
    org.status    = 'inactive'
    org.is_active = False
    org.save(update_fields=['status', 'is_active'])
 
    messages.success(request, f'"{org.name}" has been deactivated.')
    return redirect('member_list')
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  2. ENQUIRY — delete
# ══════════════════════════════════════════════════════════════════════════════
 
@login_required
@require_POST
def delete_enquiry(request, pk):
    """
    Hard-delete an enquiry. Only the owning org_admin or super admin can do this.
    Modal confirm → POST.
    """
    user = request.user
    if user.is_super_admin:
        enq = get_object_or_404(Enquiry, pk=pk)
    else:
        org = user.organization
        if not org:
            return redirect('dashboard')
        enq = get_object_or_404(Enquiry, pk=pk, organization=org)
 
    enq.delete()
    messages.success(request, 'Enquiry deleted.')
 
    # AJAX support (called from inline table row)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('enquiries')
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  3. SUPPLY CHAIN LINK — delete
# ══════════════════════════════════════════════════════════════════════════════
 
@login_required
@require_POST
def delete_chain_link(request, pk):
    """
    Hard-delete a supply-chain link.
    Only the parent or child organisation can remove it.
    """
    org  = request.user.organization
    link = get_object_or_404(SupplyChainLink, pk=pk)
 
    if org not in (link.parent, link.child):
        messages.error(request, 'Permission denied.')
        return redirect('supply_chain')
 
    other = link.child if link.parent == org else link.parent
    link.delete()
    messages.success(request, f'Connection with "{other.name}" removed.')
    return redirect('supply_chain')
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  4. INVITATION TOKEN (admin-sent) — delete
# ══════════════════════════════════════════════════════════════════════════════
 
@login_required
@require_POST
def admin_delete_invite(request, pk):
    """
    Hard-delete an admin-sent InvitationToken (invite_type='admin').
    Super admin only.
    """
    if not request.user.is_super_admin:
        return redirect('dashboard')
 
    invite = get_object_or_404(InvitationToken, pk=pk, invite_type='admin')
    email  = invite.email
    invite.delete()
    messages.success(request, f'Invitation for {email} has been deleted.')
    return redirect('invitation_list')
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  5. STAFF — list / edit / toggle-active / delete
# ══════════════════════════════════════════════════════════════════════════════
 
@login_required
def staff_list(request):
    """
    List all staff members belonging to the current organisation.
    Super admins see all staff across all orgs (filtered by ?org=pk).
    """
    user = request.user
 
    if user.is_super_admin:
        org_pk = request.GET.get('org')
        members = CustomUser.objects.select_related('organization').exclude(role='super_admin')
        if org_pk:
            members = members.filter(organization_id=org_pk)
        org = None
    else:
        org = user.organization
        if not org:
            return redirect('dashboard')
        members = org.members.all()
 
    return render(request, 'staff_list.html', {
        'members': members,
        'org':     org,
    })
 
 
@login_required
def edit_staff(request, pk):
    """
    Edit a staff member's details.
    Org admins can only edit staff in their own org.
    Super admins can edit anyone.
    """
    user = request.user
 
    if user.is_super_admin:
        member = get_object_or_404(CustomUser, pk=pk)
    else:
        org    = user.organization
        member = get_object_or_404(CustomUser, pk=pk, organization=org)
 
    if request.method == 'POST':
        member.first_name     = request.POST.get('first_name', member.first_name).strip()
        member.last_name      = request.POST.get('last_name',  member.last_name).strip()
        member.phone          = request.POST.get('phone',      member.phone).strip()
        member.landline       = request.POST.get('landline',   member.landline).strip()
        member.gender         = request.POST.get('gender',     member.gender)
        requested_role = request.POST.get('role', member.role)
        if user.is_super_admin and requested_role in dict(CustomUser.ROLE_CHOICES):
            member.role = requested_role
        elif requested_role == 'staff':
            member.role = 'staff'

        team_role_id = request.POST.get('team_role', '').strip()
        member.team_role = (
            TeamRole.objects.filter(
                pk=team_role_id,
                organization=member.organization,
                is_active=True,
            ).first()
            if team_role_id else None
        )
 
        dob = request.POST.get('date_of_birth', '')
        if dob:
            from datetime import date
            try:
                member.date_of_birth = date.fromisoformat(dob)
            except ValueError:
                messages.error(request, 'Invalid date of birth format.')
                return redirect('edit_staff', pk=pk)
 
        if request.FILES.get('profile_pic'):
            member.profile_pic = request.FILES['profile_pic']
 
        # Password change (optional — only if both fields supplied)
        new_password  = request.POST.get('new_password', '').strip()
        confirm_pass  = request.POST.get('confirm_password', '').strip()
        if new_password:
            if new_password != confirm_pass:
                messages.error(request, 'Passwords do not match.')
                return redirect('edit_staff', pk=pk)
            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
                return redirect('edit_staff', pk=pk)
            member.set_password(new_password)
 
        member.save()
        messages.success(request, f'{member.get_full_name() or member.username} updated.')
        return redirect('staff_list')
 
    return render(request, 'staff_edit.html', {
        'member': member,
        'role_choices': CustomUser.ROLE_CHOICES,
        'gender_choices': CustomUser.GENDER_CHOICES,
        'team_roles': TeamRole.objects.filter(
            organization=member.organization,
            is_active=True,
        ),
    })
 
 
@login_required
@require_POST
def toggle_staff_active(request, pk):
    """
    Toggle a staff member's is_active flag (enable / disable login).
    """
    user = request.user
 
    if user.is_super_admin:
        member = get_object_or_404(CustomUser, pk=pk)
    else:
        org    = user.organization
        member = get_object_or_404(CustomUser, pk=pk, organization=org)
 
    # Prevent self-deactivation
    if member.pk == user.pk:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('staff_list')
 
    member.is_active = not member.is_active
    member.save(update_fields=['is_active'])
 
    status = 'activated' if member.is_active else 'deactivated'
    messages.success(request, f'{member.get_full_name() or member.username} {status}.')
 
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'is_active': member.is_active})
    return redirect('staff_list')
 
 
@login_required
@require_POST
def delete_staff(request, pk):
    """
    Hard-delete a staff member.
    Org admins can only delete staff in their own org.
    Cannot delete super admins.
    """
    user = request.user
 
    if user.is_super_admin:
        member = get_object_or_404(CustomUser, pk=pk)
    else:
        org    = user.organization
        member = get_object_or_404(CustomUser, pk=pk, organization=org)
 
    if member.pk == user.pk:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('staff_list')
 
    if member.role == 'super_admin':
        messages.error(request, 'Super admin accounts cannot be deleted here.')
        return redirect('staff_list')
 
    name = member.get_full_name() or member.username
    member.delete()
    messages.success(request, f'Staff member "{name}" deleted.')
    return redirect('staff_list')
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  6. GALLERY IMAGE — list / add (single + bulk) / delete
# ══════════════════════════════════════════════════════════════════════════════
 
@login_required
def manage_gallery(request):
    """List all gallery images for the current org."""
    org = request.user.organization
    if not org:
        return redirect('dashboard')
 
    images = org.gallery.all()
    return render(request, 'manage_gallery.html', {
        'org':    org,
        'images': images,
        'total':  images.count(),
    })
 
 
@login_required
def add_gallery_images(request):
    """
    Upload one or multiple gallery images in a single POST.
    The template should use:
      <input type="file" name="images" multiple accept="image/*">
    """
    org = request.user.organization
    if not org:
        return redirect('dashboard')
 
    if request.method == 'POST':
        files   = request.FILES.getlist('images')
        caption = request.POST.get('caption', '').strip()
 
        if not files:
            messages.error(request, 'Please select at least one image.')
            return redirect('manage_gallery')
 
        # Determine next order value
        last_order = org.gallery.order_by('-order').values_list('order', flat=True).first() or 0
 
        created = 0
        for idx, img_file in enumerate(files):
            # Basic image validation
            if not img_file.content_type.startswith('image/'):
                messages.warning(request, f'"{img_file.name}" is not an image — skipped.')
                continue
            if img_file.size > 10 * 1024 * 1024:   # 10 MB guard
                messages.warning(request, f'"{img_file.name}" exceeds 10 MB — skipped.')
                continue
 
            GalleryImage.objects.create(
                organization = org,
                image        = img_file,
                caption      = caption,
                order        = last_order + idx + 1,
            )
            created += 1
 
        if created:
            messages.success(request, f'{created} image(s) uploaded successfully.')
        return redirect('manage_gallery')
 
    # GET — just redirect; upload UI lives on manage_gallery
    return redirect('manage_gallery')
 
 
@login_required
@require_POST
def delete_gallery_image(request, pk):
    """Delete a single gallery image."""
    org   = request.user.organization
    image = get_object_or_404(GalleryImage, pk=pk, organization=org)
 
    # Remove the file from storage too
    if image.image:
        try:
            image.image.delete(save=False)
        except Exception:
            pass   # storage error shouldn't block the DB delete
 
    image.delete()
    messages.success(request, 'Image removed.')
 
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('manage_gallery')
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  7. TESTIMONIAL — list / add / edit / delete
# ══════════════════════════════════════════════════════════════════════════════
 
@login_required
def manage_testimonials(request):
    """List all testimonials for the current org."""
    org = request.user.organization
    if not org:
        return redirect('dashboard')
 
    testimonials = org.testimonials.all()
    return render(request, 'manage_testimonials.html', {
        'org':          org,
        'testimonials': testimonials,
        'total':        testimonials.count(),
        'active':       testimonials.filter(is_active=True).count(),
    })
 
 
@login_required
def add_testimonial(request):
    """Add a new testimonial."""
    org = request.user.organization
    if not org:
        return redirect('dashboard')
 
    if request.method == 'POST':
        client_name = request.POST.get('client_name', '').strip()
        if not client_name:
            messages.error(request, 'Client name is required.')
            return redirect('manage_testimonials')
 
        rating = _safe_int(request.POST.get('rating'), default=5, min_val=1, max_val=5)
 
        org.testimonials.create(
            client_name = client_name,
            client_role = request.POST.get('client_role', '').strip(),
            message     = request.POST.get('message', '').strip(),
            rating      = rating,
            is_active   = request.POST.get('is_active') == 'on',
        )
        messages.success(request, f'Testimonial from "{client_name}" added.')
        return redirect('manage_testimonials')
 
    return redirect('manage_testimonials')
 
 
@login_required
def edit_testimonial(request, pk):
    """Edit an existing testimonial."""
    org         = request.user.organization
    testimonial = get_object_or_404(Testimonial, pk=pk, organization=org)
 
    if request.method == 'POST':
        client_name = request.POST.get('client_name', '').strip()
        if not client_name:
            messages.error(request, 'Client name is required.')
            return redirect('manage_testimonials')
 
        testimonial.client_name = client_name
        testimonial.client_role = request.POST.get('client_role', '').strip()
        testimonial.message     = request.POST.get('message', '').strip()
        testimonial.rating      = _safe_int(request.POST.get('rating'), default=5, min_val=1, max_val=5)
        testimonial.is_active   = request.POST.get('is_active') == 'on'
        testimonial.save()
 
        messages.success(request, 'Testimonial updated.')
        return redirect('manage_testimonials')
 
    # GET — render inline edit form
    return render(request, 'testimonial_edit.html', {
        'org':         org,
        'testimonial': testimonial,
    })
 
 
@login_required
@require_POST
def delete_testimonial(request, pk):
    """Delete a testimonial."""
    org         = request.user.organization
    testimonial = get_object_or_404(Testimonial, pk=pk, organization=org)
 
    client_name = testimonial.client_name
    testimonial.delete()
    messages.success(request, f'Testimonial from "{client_name}" deleted.')
 
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True})
    return redirect('manage_testimonials')
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  8. PAYMENT QR — edit
# ══════════════════════════════════════════════════════════════════════════════
 
@login_required
def edit_payment_qr(request, pk):
    """Edit an existing PaymentQR entry."""
    org = request.user.organization
    if not org:
        return redirect('dashboard')
 
    qr = get_object_or_404(PaymentQR, pk=pk, organization=org)
 
    if request.method == 'POST':
        qr.label      = request.POST.get('label', qr.label).strip()
        qr.method     = request.POST.get('method', qr.method)
        qr.upi_id     = request.POST.get('upi_id', qr.upi_id).strip()
        qr.is_primary = request.POST.get('is_primary') == 'on'
        qr.is_active  = request.POST.get('is_active') == 'on'

        amount_raw = request.POST.get('amount', '').strip()
        if amount_raw:
            from decimal import Decimal, InvalidOperation
            try:
                qr.amount = Decimal(amount_raw)
                if qr.amount <= 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                messages.error(request, 'Enter a valid payment amount greater than zero.')
                return render(request, 'payment_qr_edit.html', {
                    'org': org,
                    'qr': qr,
                    'method_choices': PaymentQR.METHOD_CHOICES,
                })
        else:
            qr.amount = None
 
        order_raw = request.POST.get('order', '')
        if order_raw.isdigit():
            qr.order = int(order_raw)
 
        if request.FILES.get('qr_image'):
            # Delete old image from storage before replacing
            if qr.qr_image:
                try:
                    qr.qr_image.delete(save=False)
                except Exception:
                    pass
            qr.qr_image = request.FILES['qr_image']
 
        qr.save()
        messages.success(request, f'Payment QR "{qr.label}" updated.')
        return redirect('manage_payment_qr')
 
    # GET — render edit form
    return render(request, 'payment_qr_edit.html', {
        'org': org,
        'qr':  qr,
        'method_choices': PaymentQR.METHOD_CHOICES,
    })
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════
 
def _safe_int(value, default=0, min_val=None, max_val=None):
    """Parse an integer safely, clamping to optional min/max bounds."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    if min_val is not None:
        n = max(min_val, n)
    if max_val is not None:
        n = min(max_val, n)
    return n


from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import HttpResponse
import csv

from .models import PageView, AnalyticsEvent, Enquiry


PLAN_DAYS = {'trial': 7, 'silver': 30, 'gold': 30, 'platinum': 90}

PLAN_FEATURES = {
    'trial':    {'chart': False, 'breakdown': False, 'export': False, 'compare': False},
    'silver':   {'chart': True,  'breakdown': False, 'export': False, 'compare': False},
    'gold':     {'chart': True,  'breakdown': True,  'export': True,  'compare': True},
    'platinum': {'chart': True,  'breakdown': True,  'export': True,  'compare': True},
}


def _plan_level(org):
    return org.plan.level if (org and org.plan) else 'trial'


@login_required
def analytics_dashboard(request):
    org = request.user.organization
    if not org:
        return redirect('dashboard')

    level    = _plan_level(org)
    features = PLAN_FEATURES[level]
    days     = PLAN_DAYS[level]
    from_dt  = timezone.now() - timedelta(days=days)

    # ── Core stats (all plans) ────────────────────────────────────────────────
    total_views     = PageView.objects.filter(organization=org, created_at__gte=from_dt).count()
    unique_visitors = (
        PageView.objects
        .filter(organization=org, created_at__gte=from_dt)
        .values('session_key').distinct().count()
    )
    total_enquiries = Enquiry.objects.filter(organization=org, created_at__gte=from_dt).count()
    new_enquiries   = Enquiry.objects.filter(organization=org, status='new', created_at__gte=from_dt).count()
    wa_clicks       = AnalyticsEvent.objects.filter(
        organization=org, event_type='whatsapp_click', created_at__gte=from_dt
    ).count()
    phone_clicks    = AnalyticsEvent.objects.filter(
        organization=org, event_type='phone_click', created_at__gte=from_dt
    ).count()
    vcard_downloads = AnalyticsEvent.objects.filter(
        organization=org, event_type='vcard_download', created_at__gte=from_dt
    ).count()
    conversion_rate = round(total_enquiries / total_views * 100, 1) if total_views else 0.0

    # ── Daily trend chart (Silver+) ───────────────────────────────────────────
    chart_labels, daily_views, daily_enquiries = [], [], []
    if features['chart']:
        date_range = [
            (timezone.now().date() - timedelta(days=i))
            for i in range(days - 1, -1, -1)
        ]
        views_map = {
            r['day']: r['count']
            for r in (
                PageView.objects
                .filter(organization=org, created_at__gte=from_dt)
                .annotate(day=TruncDate('created_at'))
                .values('day').annotate(count=Count('id'))
            )
        }
        enq_map = {
            r['day']: r['count']
            for r in (
                Enquiry.objects
                .filter(organization=org, created_at__gte=from_dt)
                .annotate(day=TruncDate('created_at'))
                .values('day').annotate(count=Count('id'))
            )
        }
        for d in date_range:
            chart_labels.append(d.strftime('%-d %b'))
            daily_views.append(views_map.get(d, 0))
            daily_enquiries.append(enq_map.get(d, 0))

    # ── Product / service breakdown (Gold+) ───────────────────────────────────
    top_products, top_services = [], []
    if features['breakdown']:
        top_products = list(
            AnalyticsEvent.objects
            .filter(organization=org, event_type='product_view', created_at__gte=from_dt)
            .values('object_name').annotate(views=Count('id')).order_by('-views')[:6]
        )
        top_services = list(
            AnalyticsEvent.objects
            .filter(organization=org, event_type='service_view', created_at__gte=from_dt)
            .values('object_name').annotate(views=Count('id')).order_by('-views')[:6]
        )

    # ── Period-over-period (Gold+) ────────────────────────────────────────────
    prev_views = prev_enquiries = view_delta = enq_delta = None
    if features['compare']:
        prev_from      = from_dt - timedelta(days=days)
        prev_views     = PageView.objects.filter(
            organization=org, created_at__range=(prev_from, from_dt)
        ).count()
        prev_enquiries = Enquiry.objects.filter(
            organization=org, created_at__range=(prev_from, from_dt)
        ).count()
        view_delta = total_views - prev_views
        enq_delta  = total_enquiries - prev_enquiries

    # ── CSV export (Gold+) ────────────────────────────────────────────────────
    if request.GET.get('export') == 'csv' and features['export']:
        return _export_csv(org, from_dt)

    return render(request, 'analytics.html', {
        'org': org, 'level': level, 'features': features, 'days': days,
        'total_views': total_views, 'unique_visitors': unique_visitors,
        'total_enquiries': total_enquiries, 'new_enquiries': new_enquiries,
        'wa_clicks': wa_clicks, 'phone_clicks': phone_clicks,
        'vcard_downloads': vcard_downloads, 'conversion_rate': conversion_rate,
        'chart_labels': chart_labels, 'daily_views': daily_views,
        'daily_enquiries': daily_enquiries,
        'top_products': top_products, 'top_services': top_services,
        'prev_views': prev_views, 'prev_enquiries': prev_enquiries,
        'view_delta': view_delta, 'enq_delta': enq_delta,
    })


def _export_csv(org, from_dt):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{org.slug}_analytics.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Page Views', 'Enquiries'])
    from django.db.models.functions import TruncDate
    views_map = {
        r['day']: r['count']
        for r in (
            PageView.objects
            .filter(organization=org, created_at__gte=from_dt)
            .annotate(day=TruncDate('created_at'))
            .values('day').annotate(count=Count('id'))
        )
    }
    enq_map = {
        r['day']: r['count']
        for r in (
            Enquiry.objects
            .filter(organization=org, created_at__gte=from_dt)
            .annotate(day=TruncDate('created_at'))
            .values('day').annotate(count=Count('id'))
        )
    }
    for r in sorted(views_map.keys() | enq_map.keys()):
        writer.writerow([r, views_map.get(r, 0), enq_map.get(r, 0)])
    return response


# ── Logging helpers — call these from existing views ─────────────────────────

def log_page_view(request, org):
    """Add to public_landing(), product_detail(), visiting_card()."""
    try:
        if not request.session.session_key:
            request.session.create()
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR', '')
        )
        PageView.objects.create(
            organization=org,
            session_key=request.session.session_key or '',
            ip_hash=PageView.hash_ip(ip) if ip else '',
            referrer=request.META.get('HTTP_REFERER', '')[:500],
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
        )
    except Exception:
        pass


def log_event(request, org, event_type, object_id=None, object_name='', meta=None):
    """Call from cart_add, enquiry submit, WhatsApp button click handler, etc."""
    try:
        if not request.session.session_key:
            request.session.create()
        AnalyticsEvent.objects.create(
            organization=org,
            event_type=event_type,
            session_key=request.session.session_key or '',
            object_id=object_id,
            object_name=object_name,
            meta=meta or {},
        )
    except Exception:
        pass

@login_required
@require_POST
def bulk_org_action(request):
    """Bulk deactivate/activate organizations."""
    if not request.user.is_super_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    action = request.POST.get('action')
    org_ids = request.POST.get('org_ids', '')
    
    if not org_ids:
        messages.warning(request, 'No organizations selected.')
        return redirect('member_list')
    
    pk_list = [int(pk) for pk in org_ids.split(',') if pk.strip().isdigit()]
    
    # Remove current admin's org from the list to prevent self-deactivation
    if request.user.organization and request.user.organization.pk in pk_list:
        pk_list.remove(request.user.organization.pk)
        messages.warning(request, 'Your own organization was excluded from the bulk action.')
    
    orgs = Organization.objects.filter(pk__in=pk_list)
    count = orgs.count()
    
    if action == 'deactivate':
        updated = orgs.update(status='inactive', is_active=False)
        messages.success(request, f'{updated} organization(s) have been deactivated.')
    elif action == 'activate':
        updated = orgs.update(status='active', is_active=True)
        messages.success(request, f'{updated} organization(s) have been activated.')
    else:
        messages.error(request, 'Invalid action.')
        return redirect('member_list')
    
    return redirect('member_list')

def onboard_accept(request, token):
    """
    Public view — the magic link from the invitation email.
    The user completes their profile.  The account is created in
    'pending_approval' state; a super-admin must approve before they
    can log in.
    """
    from .models import InvitationToken  # adjust import path as needed
 
    invite = get_object_or_404(InvitationToken, token=token)
 
    # ── Already submitted — show waiting screen ───────────────────────────────
    if invite.approval_status == 'pending_review' and invite.status == 'accepted':
        return render(request, 'onboard_pending_review.html', {'invite': invite})
 
    if invite.approval_status == 'rejected':
        return render(request, 'onboard_rejected.html', {
            'invite':  invite,
            'reason':  invite.rejection_reason,
        })

    # ── Guard: token must still be valid ─────────────────────────────────────
    if not invite.is_valid:
        reason = 'expired' if invite.status == 'pending' else invite.status
        return render(request, 'onboard_invalid.html', {'reason': reason})
 
    if request.method == 'POST':
        errors = _validate_onboard_form(request.POST, invite)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            try:
                with transaction.atomic():
                    org, user = _create_org_and_user_from_onboard(
                        request.POST, request.FILES, invite
                    )
 
                    # ── Mark invitation accepted but awaiting admin review ────
                    invite.status          = 'accepted'
                    invite.accepted_at     = timezone.now()
                    invite.organization    = org
                    invite.approval_status = 'pending_review'   # ← KEY change
                    invite.email           = user.email
                    invite.phone           = normalize_indian_phone(user.phone)
                    invite.save()
 
                    # ── Notify all super admins by email ─────────────────────
                    _notify_admins_of_new_submission(invite, org, request)
 
                messages.info(
                    request,
                    'Your profile has been submitted successfully! '
                    'Our team will review and activate your account within 24 hours. '
                    'You will receive an update once approved.'
                )
                return redirect('onboard_pending_review', token=token)
 
            except Exception as exc:
                messages.error(request, f'Setup failed: {exc}')
 
    context = {
        'invite': invite,
        'plan':   invite.plan,
        'cat':    invite.main_category,
        'subcat': invite.sub_category,
    }
    return render(request, 'onboard_accept.html', context)
 
 
def onboard_pending_review(request, token):
    """
    Shown immediately after submission — tells the user their account
    is under review.
    """
    from .models import InvitationToken
    invite = get_object_or_404(InvitationToken, token=token)
    return render(request, 'onboard_pending_review.html', {'invite': invite})
 
 
def onboard_done(request, token):
    """
    Final success page shown after the admin approves and the user
    logs in for the first time.
    """
    from .models import InvitationToken
    invite = get_object_or_404(InvitationToken, token=token)
    return render(request, 'onboard_done.html', {
        'invite': invite,
        'org':    invite.organization,
    })
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  3. ADMIN APPROVAL VIEWS  (add to views.py)
# ─────────────────────────────────────────────────────────────────────────────
 
from django.contrib.auth.decorators import login_required
 
 
@login_required
def pending_approvals(request):
    """
    Super Admin — list of submitted onboarding profiles waiting for review.
    """
    if not request.user.is_super_admin:
        return redirect('dashboard')
 
    from .models import InvitationToken
    from django.core.paginator import Paginator
 
    pending = (
        InvitationToken.objects
        .filter(status='accepted', approval_status='pending_review')
        .select_related('plan', 'main_category', 'sub_category', 'organization')
        .order_by('-accepted_at')
    )
 
    paginator = Paginator(pending, 20)
    page      = paginator.get_page(request.GET.get('page'))
 
    return render(request, 'pending_approvals.html', {
        'page_obj': page,
        'total':    pending.count(),
    })
 
 
@login_required
def approve_member(request, pk):
    """
    Super Admin — approve a submitted onboarding.
    Activates the Organisation + User and sends a welcome email.
    """
    if not request.user.is_super_admin:
        return redirect('dashboard')
 
    from .models import InvitationToken
 
    invite = get_object_or_404(
        InvitationToken, pk=pk, status='accepted', approval_status='pending_review'
    )
    org  = invite.organization
    user = org.members.filter(role='org_admin').first()
 
    if request.method == 'POST':
        with transaction.atomic():
            invite = get_object_or_404(
                InvitationToken.objects.select_for_update(),
                pk=pk,
                status='accepted',
                approval_status='pending_review',
            )
            org = invite.organization
            user = org.members.filter(role='org_admin').first()

            # ── Activate organisation ─────────────────────────────────────────
            org.status    = 'active'
            org.is_active = True
            org.save(update_fields=['status', 'is_active'])
 
            # ── Activate user account ─────────────────────────────────────────
            if user:
                user.is_active = True
                user.save(update_fields=['is_active'])
 
            # ── Update invite record ──────────────────────────────────────────
            invite.approval_status = 'approved'
            invite.reviewed_by     = request.user
            invite.reviewed_at     = timezone.now()
            invite.save(update_fields=['approval_status', 'reviewed_by', 'reviewed_at'])
 
            # ── Award member-invite bonus (if applicable) ─────────────────────
            _award_member_invite_bonus(invite)
 
            # ── Send approval email to the new member ─────────────────────────
            _send_approval_email(invite, request)
 
        messages.success(
            request,
            f'✓ {org.name} has been approved and activated. '
            'Any eligible referral reward has now been released.'
        )
        return redirect('pending_approvals')
 
    # GET → confirmation page
    return render(request, 'approve_member_confirm.html', {
        'invite': invite,
        'org':    org,
        'user':   user,
    })
 
 
@login_required
def reject_member(request, pk):
    """
    Super Admin — reject a submitted onboarding with an optional reason.
    Sends a rejection email to the applicant.
    """
    if not request.user.is_super_admin:
        return redirect('dashboard')
 
    from .models import InvitationToken
 
    invite = get_object_or_404(
        InvitationToken, pk=pk, status='accepted', approval_status='pending_review'
    )
    org = invite.organization
 
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()
 
        with transaction.atomic():
            # ── Mark org as rejected ─────────────────────────────────────────
            org.status    = 'rejected'
            org.is_active = False
            org.save(update_fields=['status', 'is_active'])
 
            # ── Deactivate user account ──────────────────────────────────────
            user = org.members.filter(role='org_admin').first()
            if user:
                user.is_active = False
                user.save(update_fields=['is_active'])
 
            # ── Update invite record ─────────────────────────────────────────
            invite.approval_status  = 'rejected'
            invite.rejection_reason = reason
            invite.reviewed_by      = request.user
            invite.reviewed_at      = timezone.now()
            invite.save(update_fields=[
                'approval_status', 'rejection_reason',
                'reviewed_by', 'reviewed_at',
            ])
 
            # ── Send rejection email ─────────────────────────────────────────
            _send_rejection_email(invite, reason, request)
 
        messages.warning(
            request,
            f'Submission by {invite.email} has been rejected. '
            f'A notification email has been sent to them.'
        )
        return redirect('pending_approvals')
 
    # GET → confirmation + reason form
    return render(request, 'reject_member_confirm.html', {
        'invite': invite,
        'org':    org,
    })
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  4. EMAIL HELPERS  (add to views.py alongside existing _send_invitation_email)
# ─────────────────────────────────────────────────────────────────────────────
 
def _notify_admins_of_new_submission(invite, org, request):
    """
    Email every super-admin when a new onboarding form is submitted.
    """
    from .models import CustomUser
 
    admin_emails = list(
        CustomUser.objects
        .filter(role='super_admin', is_active=True)
        .values_list('email', flat=True)
    )
    if not admin_emails:
        return
 
    review_url = request.build_absolute_uri(
        f'/admin-panel/approvals/{invite.pk}/approve/'
    )
    reject_url = request.build_absolute_uri(
        f'/admin-panel/approvals/{invite.pk}/reject/'
    )
 
    subject = f'[Portal] New Member Submission — {org.name} (requires approval)'
    body = (
        f"A new business has completed the onboarding form and is awaiting your review.\n\n"
        f"Business  : {org.name}\n"
        f"Email     : {invite.email}\n"
        f"Plan      : {invite.plan.name if invite.plan else '—'}\n"
        f"Category  : {invite.main_category.name if invite.main_category else '—'}\n"
        f"Submitted : {invite.accepted_at.strftime('%d %b %Y, %H:%M') if invite.accepted_at else '—'}\n\n"
        f"Approve : {review_url}\n"
        f"Reject  : {reject_url}\n\n"
        f"— Portal Platform"
    )
 
    try:
        html_body = render_to_string('emails/admin_new_submission.html', {
            'invite':     invite,
            'org':        org,
            'review_url': review_url,
            'reject_url': reject_url,
        })
    except Exception:
        html_body = None
 
    send_mail(
        subject        = subject,
        message        = body,
        from_email     = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portal.com'),
        recipient_list = admin_emails,
        html_message   = html_body,
        fail_silently  = True,
    )
 
 
def _send_approval_email(invite, request):
    """
    Tell the new member their account has been approved.
    Includes a direct login link.
    """
    login_url = request.build_absolute_uri('/login/')
 
    subject = '🎉 Your Portal account has been approved!'
    body = (
        f"Hello {invite.organization.name},\n\n"
        f"Great news! Your account on Portal has been reviewed and approved.\n\n"
        f"You can now log in and start using your dashboard:\n"
        f"{login_url}\n\n"
        f"Email    : {invite.email}\n"
        f"Password : (the one you set during registration)\n\n"
        f"If you have any questions, reply to this email.\n\n"
        f"Welcome aboard!\n"
        f"— Portal Team"
    )
 
    try:
        html_body = render_to_string('emails/account_approved.html', {
            'invite':    invite,
            'org':       invite.organization,
            'login_url': login_url,
        })
    except Exception:
        html_body = None
 
    send_mail(
        subject        = subject,
        message        = body,
        from_email     = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portal.com'),
        recipient_list = [invite.email],
        html_message   = html_body,
        fail_silently  = True,
    )
 
 
def _send_rejection_email(invite, reason, request):
    """
    Notify the applicant that their submission was not approved.
    """
    subject = 'Update on your Portal application'
    body = (
        f"Hello,\n\n"
        f"Thank you for submitting your business details on Portal.\n\n"
        f"After review, we are unable to approve your account at this time"
        + (f" for the following reason:\n\n{reason}\n\n" if reason else ".\n\n") +
        f"If you believe this is a mistake or would like to reapply, "
        f"please contact our support team.\n\n"
        f"— Portal Team"
    )
 
    try:
        html_body = render_to_string('emails/account_rejected.html', {
            'invite': invite,
            'reason': reason,
        })
    except Exception:
        html_body = None
 
    send_mail(
        subject        = subject,
        message        = body,
        from_email     = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portal.com'),
        recipient_list = [invite.email],
        html_message   = html_body,
        fail_silently  = True,
    )
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  5. UPDATED _create_org_and_user_from_onboard
#     Only change: org.status = 'pending_approval', org.is_active = False
#                  user.is_active = False
# ─────────────────────────────────────────────────────────────────────────────
 
def _create_org_and_user_from_onboard(data, files, invite):
    """
    Create Organization + CustomUser from the onboarding POST data.
    Both are created INACTIVE until a super-admin approves.
    """
    from .models import (
        Organization, Service, VisitingCard,
        WhatsAppConfig, CustomUser,
    )
    from .utils import unique_organization_key

    account_email = (invite.email or data.get('email', '')).strip().lower()
    subdomain = invite.subdomain or unique_organization_key(
        Organization, data['company_name'], field='subdomain'
    )
 
    # ── Organisation ─────────────────────────────────────────────────────────
    org = Organization.objects.create(
        name             = data['company_name'].strip(),
        subdomain        = subdomain,
        category         = invite.main_category,
        sub_category     = invite.sub_category,
        plan             = invite.plan,
        plan_start_date  = timezone.now().date(),
        plan_end_date    = (
            timezone.now().date() + timezone.timedelta(days=invite.plan.duration_days)
            if invite.plan else None
        ),
        email            = account_email,
        phone            = data.get('mobile', '').strip(),
        whatsapp         = data.get('whatsapp', '').strip(),
        landline         = data.get('landline', '').strip(),
        website          = data.get('website', '').strip(),
        tagline          = data.get('tagline', '').strip(),
        description      = data.get('description', '').strip(),
        address_line1    = data.get('address', '').strip(),
        address_line2    = data.get('address2', '').strip(),
        city             = data.get('city', '').strip(),
        district         = data.get('district', '').strip(),
        state            = data.get('state', '').strip(),
        pincode          = data.get('pincode', '').strip(),
        status           = 'pending_approval',   # ← was 'active'
        is_active        = False,                 # ← was True
    )
 
    if files.get('logo'):
        org.logo = files['logo']
        org.save(update_fields=['logo'])
 
    # ── Default services from category template ────────────────────────────
    if invite.main_category:
        for i, svc_name in enumerate(invite.main_category.default_services):
            Service.objects.create(
                organization = org,
                name         = svc_name,
                icon         = invite.main_category.icon,
                order        = i,
                is_featured  = (i < 3),
            )
 
    # ── Auto-create visiting card & WhatsApp config ────────────────────────
    VisitingCard.objects.create(
        organization = org,
        contact_name = data.get('contact_name', '').strip(),
        designation  = data.get('designation', '').strip(),
    )
    whatsapp_number = data.get('whatsapp', '') or data.get('mobile', '')
    if whatsapp_number:
        WhatsAppConfig.objects.create(
            organization    = org,
            whatsapp_number = whatsapp_number.strip().replace('+', '').replace(' ', ''),
        )
 
    # ── User account ──────────────────────────────────────────────────────
    email_local = account_email.split('@')[0].replace('.', '_').replace('+', '_')
    username    = email_local
    counter     = 1
    while CustomUser.objects.filter(username=username).exists():
        username = f"{email_local}{counter}"
        counter += 1
 
    name_parts = data.get('contact_name', '').strip().split(' ', 1)
    user = CustomUser.objects.create_user(
        username     = username,
        email        = account_email,
        password     = data['password'],
        first_name   = name_parts[0],
        last_name    = name_parts[1] if len(name_parts) > 1 else '',
        phone        = data.get('mobile', '').strip(),
        landline     = data.get('landline', '').strip(),
        gender       = data.get('gender', 'male'),
        organization = org,
        role         = 'org_admin',
        is_active    = False,   # ← cannot log in until approved
    )
 
    if files.get('profile_photo'):
        user.profile_pic = files['profile_photo']
        user.save(update_fields=['profile_pic'])
 
    return org, user


from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt

from .models import Payment, Organization, PaymentQR

import base64
import requests
import json


# ═════════ PayPal BASE ═════════
PAYPAL_BASE = (
    "https://api-m.sandbox.paypal.com"
    if getattr(settings, "PAYPAL_MODE", "sandbox") == "sandbox"
    else "https://api-m.paypal.com"
)


# ═════════ TOKEN ═════════
def get_paypal_token():
    try:
        client_id = settings.PAYPAL_CLIENT_ID
        secret = settings.PAYPAL_SECRET

        auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()

        response = requests.post(
            f"{PAYPAL_BASE}/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )

        if response.status_code == 200:
            return response.json().get("access_token")

        return None

    except Exception as e:
        print("Token Error:", e)
        return None


# ═════════ CREATE ORDER ═════════
def create_paypal_order(
    amount,
    description="Payment",
    return_url=None,
    cancel_url=None,
    brand_name="Portal",
):
    try:
        token = get_paypal_token()
        if not token:
            return None, "Token error"

        site_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
        return_url = return_url or f"{site_url}/payment/success/"
        cancel_url = cancel_url or f"{site_url}/payment/cancel/"

        if return_url.startswith("/"):
            return_url = f"{site_url.rstrip('/')}{return_url}"
        if cancel_url.startswith("/"):
            cancel_url = f"{site_url.rstrip('/')}{cancel_url}"

        currency_code = getattr(settings, 'PAYPAL_CURRENCY', 'USD')
        response = requests.post(
            f"{PAYPAL_BASE}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": currency_code,
                            "value": str(amount),
                        },
                        "description": description,
                    }
                ],
                "application_context": {
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                    "brand_name": brand_name,
                    "user_action": "PAY_NOW",
                },
            },
        )

        if response.status_code in [200, 201]:
            return response.json(), None

        return None, response.text

    except Exception as e:
        return None, str(e)


# ═════════ CAPTURE ORDER ═════════
def capture_paypal_order(order_id):
    try:
        token = get_paypal_token()
        if not token:
            return None, "Token error"

        response = requests.post(
            f"{PAYPAL_BASE}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code in [200, 201]:
            return response.json(), None

        return None, response.text

    except Exception as e:
        return None, str(e)


# ═════════ PAYMENT PAGE ═════════
def payment_page(request, slug=None):
    org = None

    if slug:
        org = Organization.objects.filter(slug=slug).first()

    return render(
        request,
        "payment.html",
        {
            "org": org,
            "paypal_client_id": settings.PAYPAL_CLIENT_ID,
        },
    )


# ═════════ CREATE PAYMENT (AJAX) ═════════
@csrf_exempt
def paypal_create(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST only"})

    try:
        data = json.loads(request.body)
        qr = PaymentQR.objects.select_related('organization').filter(
            pk=data.get('qr_id'),
            method='paypal',
            is_active=True,
        ).first()
        if qr is None:
            return JsonResponse({"success": False, "error": "Payment option not found."}, status=404)

        if qr.amount is not None:
            amount = qr.amount
        else:
            from decimal import Decimal, InvalidOperation
            try:
                amount = Decimal(str(data.get("amount", "")).strip())
            except (InvalidOperation, ValueError):
                return JsonResponse(
                    {"success": False, "error": "Enter a valid payment amount."},
                    status=400,
                )
        if amount <= 0:
            return JsonResponse(
                {"success": False, "error": "Payment amount must be greater than zero."},
                status=400,
            )
        return_url = data.get("return_url")
        cancel_url = data.get("cancel_url")

        if return_url:
            request.session["paypal_return_url"] = return_url
        request.session["paypal_amount"] = str(amount)

        order_data, error = create_paypal_order(
            amount,
            description=f'Payment to {qr.organization.name}',
            return_url=return_url,
            cancel_url=cancel_url,
            brand_name=qr.organization.name,
        )

        if error:
            return JsonResponse({"success": False, "error": error})

        order_id = order_data["id"]

        approval_url = None
        for link in order_data.get("links", []):
            if link.get("rel") == "approve":
                approval_url = link.get("href")

        if not approval_url:
            return JsonResponse({"success": False, "error": "No approval URL"})

        Payment.objects.create(
            payment_id=order_id,
            amount=amount,
            status="pending",
        )

        return JsonResponse(
            {
                "success": True,
                "order_id": order_id,
                "approval_url": approval_url,
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# ═════════ SUCCESS ═════════
def payment_success(request):
    order_id = request.GET.get("token")

    if not order_id:
        return redirect("payment_failed")

    try:
        capture_data, error = capture_paypal_order(order_id)

        if error:
            Payment.objects.filter(payment_id=order_id).update(status="failed")
            return redirect("payment_failed")

        payment = Payment.objects.filter(payment_id=order_id).first()
        if payment:
            payment.status = "success"
            payment.save(update_fields=["status"])

        return_url = request.session.pop("paypal_return_url", None)
        session_amount = request.session.pop("paypal_amount", None)
        if return_url:
            return redirect(return_url)

        return render(
            request,
            "payment_success.html",
            {
                "transaction_id": capture_data.get("id", order_id),
                "amount": str(payment.amount) if payment else session_amount,
            },
        )

    except Exception:
        Payment.objects.filter(payment_id=order_id).update(status="failed")
        return redirect("payment_failed")


# ═════════ CANCEL ═════════
def payment_cancel(request):
    order_id = request.GET.get("token")

    if order_id:
        Payment.objects.filter(payment_id=order_id).update(status="failed")

    return_url = request.session.pop("paypal_return_url", None)
    if return_url:
        return redirect(return_url)

    return render(request, "payment_cancel.html")


# ═════════ FAILED ═════════
def payment_failed(request):
    return render(request, "payment_failed.html")

# ─────────────────────────────────────────────────────────────────────────────
#  ENDPOINT  —  POST /org/<slug>/whatsapp-click/
#  Called by frontend JS when visitor taps the WhatsApp button on any page.
# ─────────────────────────────────────────────────────────────────────────────
 
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Organization, Product, Service, AnalyticsEvent, CustomUser
from .views import log_event          # reuse the existing helper
 
 
@csrf_exempt                          # visitor is anonymous — no CSRF cookie
@require_POST
def log_whatsapp_click(request, slug):
    """
    Logs a whatsapp_click AnalyticsEvent and optionally emails every
    super-admin so they know a visitor enquired about a specific product
    or service via WhatsApp.
 
    Expected POST body (JSON or form-encoded):
        source        "product" | "service" | "general"
        object_id     pk of the Product / Service  (optional)
        visitor_name  string (optional — if visitor filled a name field)
        visitor_phone string (optional)
    """
    import json
 
    org = get_object_or_404(Organization, slug=slug, is_active=True)
 
    # ── Parse body (accept both JSON and form-encoded) ────────────────────
    try:
        payload = json.loads(request.body)
    except (ValueError, TypeError):
        payload = request.POST
 
    source        = payload.get('source', 'general')          # product / service / general
    object_id_raw = payload.get('object_id')
    visitor_name  = str(payload.get('visitor_name', '')).strip()
    visitor_phone = str(payload.get('visitor_phone', '')).strip()
 
    object_id   = int(object_id_raw) if object_id_raw else None
    object_name = ''
    object_url  = ''
 
    # ── Resolve the item name for richer notifications ────────────────────
    if source == 'product' and object_id:
        product = Product.objects.filter(pk=object_id, organization=org, is_active=True).first()
        if product:
            object_name = product.name
            object_url  = request.build_absolute_uri(
                f'/{slug}/product/{object_id}/'
            )
 
    elif source == 'service' and object_id:
        service = Service.objects.filter(pk=object_id, organization=org, is_active=True).first()
        if service:
            object_name = service.name
 
    # ── Log analytics event ───────────────────────────────────────────────
    log_event(
        request, org, 'whatsapp_click',
        object_id=object_id,
        object_name=object_name,
        meta={
            'source':        source,
            'visitor_name':  visitor_name,
            'visitor_phone': visitor_phone,
        },
    )
 
    # ── Email every active super-admin ────────────────────────────────────
    _notify_superadmin_whatsapp_click(
        org=org,
        source=source,
        object_name=object_name,
        object_url=object_url,
        visitor_name=visitor_name,
        visitor_phone=visitor_phone,
        request=request,
    )
 
    return JsonResponse({'ok': True})
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  HELPER  —  email all super-admins
# ─────────────────────────────────────────────────────────────────────────────
 
def _notify_superadmin_whatsapp_click(
    org: Organization,
    source: str,
    object_name: str,
    object_url: str,
    visitor_name: str,
    visitor_phone: str,
    request,
):
    """
    Sends a lightweight notification email to every active super-admin
    whenever a visitor taps the WhatsApp button on an org's public page.
    Uses fail_silently=True so a mail server hiccup never breaks the UX.
    """
    from django.core.mail import send_mail
    from django.conf import settings
    from django.utils import timezone
 
    admin_emails = list(
        CustomUser.objects
        .filter(role='super_admin', is_active=True)
        .values_list('email', flat=True)
    )
    if not admin_emails:
        return  # no super-admins configured — skip silently
 
    # ── Build human-readable context ──────────────────────────────────────
    now_str   = timezone.now().strftime('%d %b %Y, %H:%M')
    item_line = f'Item     : {object_name} ({source})' if object_name else f'Source   : {source}'
    link_line = f'Item URL : {object_url}\n' if object_url else ''
    visitor_line = ''
    if visitor_name or visitor_phone:
        visitor_line = (
            f'Visitor  : {visitor_name or "—"}  |  '
            f'Phone: {visitor_phone or "—"}\n'
        )
 
    org_dashboard_url = request.build_absolute_uri(f'/admin-panel/members/')
 
    subject = (
        f'[Portal] WhatsApp Enquiry — {org.name}'
        + (f' › {object_name}' if object_name else '')
    )
 
    body = (
        f'A visitor just tapped the WhatsApp button on Portal.\n\n'
        f'Organisation : {org.name}\n'
        f'{item_line}\n'
        f'{link_line}'
        f'Time     : {now_str}\n'
        f'{visitor_line}'
        f'\nView member dashboard:\n{org_dashboard_url}\n\n'
        f'— Portal Platform'
    )
 
    send_mail(
        subject        = subject,
        message        = body,
        from_email     = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portal.com'),
        recipient_list = admin_emails,
        fail_silently  = True,   # never crash the visitor's WhatsApp redirect
    )


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import json
 
@csrf_exempt
@require_POST
def log_whatsapp_click(request, slug):
    """
    Called by the frontend JS whenever a visitor taps any .wa-btn.
    1. Logs an AnalyticsEvent (existing system, unchanged).
    2. Creates an AdminNotification visible on the super-admin dashboard.
 
    POST body (JSON):
        source        "product" | "service" | "general"
        object_id     pk of Product / Service  (optional)
        visitor_name  string (optional)
        visitor_phone string (optional)
    """
    from .models import Organization, Product, Service, AdminNotification
    from .views  import log_event   # the existing helper in views.py
 
    org = get_object_or_404(Organization, slug=slug, is_active=True)
 
    # ── Parse request body ────────────────────────────────────────────────
    try:
        payload = json.loads(request.body)
    except (ValueError, TypeError):
        payload = request.POST
 
    source        = payload.get('source', 'general')
    object_id_raw = payload.get('object_id')
    visitor_name  = str(payload.get('visitor_name',  '')).strip()
    visitor_phone = str(payload.get('visitor_phone', '')).strip()
 
    object_id   = int(object_id_raw) if object_id_raw else None
    object_name = ''
 
    # ── Resolve item name ─────────────────────────────────────────────────
    if source == 'product' and object_id:
        p = Product.objects.filter(pk=object_id, organization=org, is_active=True).first()
        if p:
            object_name = p.name
 
    elif source == 'service' and object_id:
        s = Service.objects.filter(pk=object_id, organization=org, is_active=True).first()
        if s:
            object_name = s.name
 
    # ── 1. Log AnalyticsEvent (existing — unchanged) ──────────────────────
    log_event(
        request, org, 'whatsapp_click',
        object_id   = object_id,
        object_name = object_name,
        meta = {
            'source':        source,
            'visitor_name':  visitor_name,
            'visitor_phone': visitor_phone,
        },
    )
 
    # ── 2. Create AdminNotification (dashboard bell) ──────────────────────
    _create_dashboard_notification(
        org           = org,
        source        = source,
        object_name   = object_name,
        visitor_name  = visitor_name,
        visitor_phone = visitor_phone,
    )
 
    return JsonResponse({'ok': True})
 
 
def _create_dashboard_notification(
    org,
    source: str,
    object_name: str,
    visitor_name: str,
    visitor_phone: str,
):
    """
    Inserts one AdminNotification row.
 
    Throttle: one notification per org per item per 10 minutes so the
    dashboard doesn't flood if 50 visitors tap at once.
    """
    from .models import AdminNotification
    from django.utils import timezone
    from datetime import timedelta
 
    ten_min_ago = timezone.now() - timedelta(minutes=10)
 
    already = AdminNotification.objects.filter(
        organization      = org,
        notification_type = 'whatsapp_click',
        is_read           = False,
        created_at__gte   = ten_min_ago,
    )
    if object_name:
        already = already.filter(title__icontains=object_name)
    if already.exists():
        return  # throttled — skip
 
    # Build readable title & message
    if object_name:
        title = f'WhatsApp Enquiry — {org.name} › {object_name}'
    else:
        title = f'WhatsApp Enquiry — {org.name}'
 
    lines = [
        f'A visitor tapped the WhatsApp button on {org.name}\'s page.',
        f'',
        f'Organisation : {org.name}',
    ]
    if object_name:
        lines.append(f'Item         : {object_name} ({source})')
    else:
        lines.append(f'Source       : {source}')
    if visitor_name:
        lines.append(f'Visitor Name : {visitor_name}')
    if visitor_phone:
        lines.append(f'Visitor Phone: {visitor_phone}')
    lines.append(f'Time         : {timezone.now().strftime("%d %b %Y, %H:%M")}')
 
    AdminNotification.objects.create(
        notification_type = 'whatsapp_click',
        title             = title,
        message           = '\n'.join(lines),
        organization      = org,
        is_read           = False,
    )
 
@login_required
@require_POST
def mark_admin_notifications_read(request):

    if not request.user.is_super_admin:
        return JsonResponse({'ok': False, 'error': 'Access denied.'}, status=403)
 
    from .models import AdminNotification
    try:
        body = json.loads(request.body)
        nid  = body.get('id')
    except Exception:
        nid = None
 
    if nid:
        AdminNotification.objects.filter(pk=nid).update(is_read=True)
    else:
        AdminNotification.objects.filter(is_read=False).update(is_read=True)
 
    return JsonResponse({
        'ok':            True,
        'unread_count':  AdminNotification.unread_count(),
    })
