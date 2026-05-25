from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from .models import Organization, CustomUser, BusinessCategory, Service, Enquiry, GalleryImage, Testimonial, Product
from .forms import (
    OrganizationSignupForm, CustomLoginForm, EnquiryForm,
    ServiceForm, OrganizationUpdateForm, ProductForm
)


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    categories = BusinessCategory.objects.all()
    return render(request, 'home.html', {'categories': categories})


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
                    messages.success(request, f'Welcome to OrgPortal, {org.name}! Your profile is ready.')
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


def public_landing(request, slug):
    """Public-facing landing page for an organization"""
    org = get_object_or_404(Organization, slug=slug, is_active=True)
    services = org.get_services()
    featured_services = services.filter(is_featured=True)
    products = org.products.filter(is_active=True)
    featured_products = products.filter(is_featured=True)
    gallery = org.gallery.all()[:8]
    testimonials = org.testimonials.filter(is_active=True)

    enquiry_form = EnquiryForm(organization=org)
    enquiry_success = False

    if request.method == 'POST':
        enquiry_form = EnquiryForm(organization=org, data=request.POST)
        if enquiry_form.is_valid():
            enq = enquiry_form.save(commit=False)
            enq.organization = org
            enq.save()
            enquiry_success = True
            enquiry_form = EnquiryForm(organization=org)
            messages.success(request, 'Your enquiry has been submitted! We will contact you soon.')

    return render(request, 'landing.html', {
        'org': org,
        'services': services,
        'featured_services': featured_services,
        'products': products,
        'featured_products': featured_products,
        'gallery': gallery,
        'testimonials': testimonials,
        'enquiry_form': enquiry_form,
        'enquiry_success': enquiry_success,
    })


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
    org = request.user.organization
    status_filter = request.GET.get('status', '')
    enquiries = org.enquiries.all()
    if status_filter:
        enquiries = enquiries.filter(status=status_filter)
    return render(request, 'enquiries.html', {
        'enquiries': enquiries,
        'org': org,
        'status_filter': status_filter,
        'enquiry_statuses': Enquiry.STATUS_CHOICES,
    })


@login_required
def update_enquiry_status(request, pk):
    org = request.user.organization
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
                        messages.success(request, f'Welcome to OrgPortal, {org.name}!')

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