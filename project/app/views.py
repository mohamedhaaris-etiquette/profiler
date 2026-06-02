from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from .models import *
from .forms import (
    OrganizationSignupForm, CustomLoginForm, EnquiryForm,
    ServiceForm, OrganizationUpdateForm, ProductForm ,SuperAdminRegisterForm
)




def home(request):
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


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    categories = BusinessCategory.objects.all()
    form = OrganizationSignupForm()

    if request.method == 'POST':
        form = OrganizationSignupForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create organization
                    org = form.save(commit=False)
                    org.save()

                    # Create admin user
                    user = CustomUser.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['user_email'],
                        password=form.cleaned_data['password1'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        phone=form.cleaned_data['user_phone'],
                        organization=org,
                        role='org_admin',
                    )

                    # Pre-fill services from category template
                    if org.category:
                        for i, svc_name in enumerate(org.category.default_services):
                            Service.objects.create(
                                organization=org,
                                name=svc_name,
                                icon=org.category.icon,
                                order=i,
                                is_featured=(i < 3),
                            )

                    login(request, user)
                    messages.success(request, f'Welcome to Portal, {org.name}! Your profile is ready.')
                    return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
        else:
            messages.error(request, 'Please fix the errors below.')

    return render(request, 'signup.html', {'form': form, 'categories': categories})


def login_view(request):
    if request.user.is_authenticated:
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

    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def dashboard(request):
    user = request.user
    if user.is_super_admin:
        orgs = Organization.objects.all().order_by('-created_at')
        total_enquiries = Enquiry.objects.count()
        new_enquiries = Enquiry.objects.filter(status='new').count()
        total_products = Product.objects.count()
        return render(request, 'super_admin_dashboard.html', {
            'orgs': orgs,
            'total_enquiries': total_enquiries,
            'new_enquiries': new_enquiries,
            'total_products': total_products,
        })

    org = user.organization
    if not org:
        messages.warning(request, 'You are not linked to any organization.')
        return redirect('login')

    services = org.get_services()
    products = org.products.filter(is_active=True)
    enquiries = org.enquiries.all()[:10]
    new_enquiries = org.enquiries.filter(status='new').count()
    testimonials = org.testimonials.filter(is_active=True)[:5]

    return render(request, 'dashboard.html', {
        'org': org,
        'services': services,
        'products': products,
        'enquiries': enquiries,
        'new_enquiries': new_enquiries,
        'testimonials': testimonials,
        'total_enquiries': org.enquiries.count(),
        'total_products': products.count(),
    })

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

def public_landing(request, slug):
    """Public-facing landing page for an organization (with notifications)."""
    from django.shortcuts import render, redirect, get_object_or_404
    from django.contrib import messages as dj_messages
    from .models import Organization
    from .forms import EnquiryForm
    from .notifications import notify_admin_whatsapp, notify_nearest_staff

    org = get_object_or_404(Organization, slug=slug, is_active=True)

    services          = org.get_services()
    featured_services = services.filter(is_featured=True)
    products          = org.products.filter(is_active=True)
    featured_products = products.filter(is_featured=True)
    gallery           = org.gallery.all()[:8]
    testimonials      = org.testimonials.filter(is_active=True)
    payment_qrs       = org.payment_qrs.filter(is_active=True)      # ← ADDED

    wa_admin_url = ''    # WhatsApp deep-link to notify admin (set after POST)

    if request.method == 'POST':
        enquiry_form = EnquiryForm(organization=org, data=request.POST)
        if enquiry_form.is_valid():
            enquiry              = enquiry_form.save(commit=False)
            enquiry.organization = org
            enquiry.save()

            # ── Notify admin ─────────────────────────────────────────────
            wa_admin_url = notify_admin_whatsapp(enquiry)

            # ── Auto-notify backup staff if any is unavailable ────────────
            notify_nearest_staff(enquiry)

            dj_messages.success(
                request,
                'Your enquiry has been submitted! We will contact you within 24 hours.'
            )
            # Pass wa_admin_url in session so it survives redirect
            request.session['wa_admin_url'] = wa_admin_url
            return redirect('public_landing', slug=slug)
    else:
        enquiry_form = EnquiryForm(organization=org)
        # Retrieve the admin url from session (after redirect)
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
        'payment_qrs':       payment_qrs,                           # ← ADDED
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
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            svc = form.save(commit=False)
            svc.organization = org
            svc.save()
            messages.success(request, 'Service added successfully.')
            return redirect('manage_services')
    else:
        form = ServiceForm()
    return render(request, 'service_form.html', {'form': form, 'org': org, 'action': 'Add'})


@login_required
def edit_service(request, pk):
    org = request.user.organization
    svc = get_object_or_404(Service, pk=pk, organization=org)
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=svc)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service updated.')
            return redirect('manage_services')
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
        enquiries = org.enquiries.all() if org else Enquiry.objects.none()
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


@login_required
def update_enquiry_status(request, pk):
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
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.organization = org
            product.save()
            messages.success(request, f'Product "{product.name}" added successfully.')
            return redirect('manage_products')
    else:
        form = ProductForm()
    return render(request, 'product_form.html', {
        'form': form, 'org': org, 'action': 'Add New'
    })


@login_required
def edit_product(request, pk):
    org = request.user.organization
    product = get_object_or_404(Product, pk=pk, organization=org)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated.')
            return redirect('manage_products')
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
    org = request.user.organization
    if request.method == 'POST':
        form = OrganizationUpdateForm(request.POST, request.FILES, instance=org)
        if form.is_valid():
            form.save()
            messages.success(request, 'Organization profile updated.')
            return redirect('org_settings')
    else:
        form = OrganizationUpdateForm(instance=org)
    return render(request, 'org_settings.html', {'form': form, 'org': org})



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
    """Signup page pre-loaded with a referral code."""
    try:
        ref = ReferralCode.objects.select_related('organization').get(code=ref_code)
        ref.total_clicks += 1
        ref.save(update_fields=['total_clicks'])
    except ReferralCode.DoesNotExist:
        ref = None

    if request.user.is_authenticated:
        return redirect('dashboard')

    categories = BusinessCategory.objects.all()
    form = OrganizationSignupForm()

    if request.method == 'POST':
        form = OrganizationSignupForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    org = form.save(commit=False)
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
                    )

                    if org.category:
                        for i, svc_name in enumerate(org.category.default_services):
                            Service.objects.create(
                                organization=org, name=svc_name,
                                icon=org.category.icon, order=i, is_featured=(i < 3),
                            )

                    # ── Award referral bonus ──────────────────────
                    if ref:
                        program = ReferralProgram.objects.filter(is_active=True).first()
                        pts = program.points_per_referral if program else 100

                        referral_obj = Referral.objects.create(
                            referrer=ref.organization,
                            referred=org,
                            code=ref,
                            status='rewarded',
                            points_awarded=pts,
                            confirmed_at=timezone.now(),
                        )
                        ReferralBonus.objects.create(
                            organization=ref.organization,
                            referral=referral_obj,
                            transaction_type='earn',
                            points=pts,
                            note=f'Referral bonus — {org.name} joined via your invite',
                        )
                        messages.success(
                            request,
                            f'Welcome! You joined via {ref.organization.name}\'s invite. '
                            f'They earned {pts} OrgPoints!'
                        )
                    else:
                        messages.success(request, f'Welcome to Portal, {org.name}!')

                    login(request, user)
                    return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
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
    org = request.user.organization
    if not org:
        return redirect('dashboard')

    ref_code = _get_or_create_referral_code(org)
    invite_url = ref_code.get_invite_url(request)
    whatsapp_url = ref_code.get_whatsapp_url(request)

    referrals = Referral.objects.filter(referrer=org).select_related('referred')
    bonus_transactions = ReferralBonus.objects.filter(organization=org)
    total_points = ReferralBonus.get_balance(org)

    program = ReferralProgram.objects.filter(is_active=True).first()

    return render(request, 'referral_dashboard.html', {
        'org': org,
        'ref_code': ref_code,
        'invite_url': invite_url,
        'whatsapp_url': whatsapp_url,
        'referrals': referrals,
        'bonus_transactions': bonus_transactions,
        'total_points': total_points,
        'total_referrals': referrals.count(),
        'rewarded_referrals': referrals.filter(status='rewarded').count(),
        'program': program,
    })


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
    already_exists = CustomUser.objects.filter(role='super_admin').exists()

    if already_exists and not (request.user.is_authenticated and request.user.is_super_admin):
        messages.error(request, 'A Super Admin already exists. Contact them to create additional accounts.')
        return redirect('login')

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
        email        = request.POST.get('email', '').strip().lower()
        plan_id      = request.POST.get('plan')
        cat_id       = request.POST.get('main_category')
        subcat_id    = request.POST.get('sub_category') or None
        subdomain    = request.POST.get('subdomain', '').strip() or None
        site_title   = request.POST.get('site_title', '').strip()
 
        # Basic validation
        errors = []
        if not email:
            errors.append('Email is required.')
        if InvitationToken.objects.filter(email=email, status='pending').exists():
            errors.append(f'A pending invitation already exists for {email}.')
        if Organization.objects.filter(email=email).exists():
            errors.append(f'{email} is already a registered member.')
        if subdomain and Organization.objects.filter(subdomain=subdomain).exists():
            errors.append(f'Subdomain "{subdomain}" is already taken.')
 
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            plan    = Plan.objects.filter(pk=plan_id).first()
            cat     = BusinessCategory.objects.filter(pk=cat_id).first()
            subcat  = SubCategory.objects.filter(pk=subcat_id).first() if subcat_id else None
 
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
                messages.error(request, f'Setup failed: {exc}')
 
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
 
 
def _validate_onboard_form(data: dict) -> list:
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

