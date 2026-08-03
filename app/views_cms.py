import json
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import (
    BusinessFeatureForm, DealerLocationForm, FAQItemForm, FooterSettingsForm,
    HeroSlideForm, MaximiseStepForm, PromoBannerForm, SuccessStoryForm,
)
from .models import (
    BusinessFeature, DealerLocation, FAQItem, HeroSlide, LandingPageConfig,
    MaximiseStep, Organization, Plan, PromoBanner, SuccessStory,
)


CONTENT_TYPES = {
    'feature': {
        'model': BusinessFeature,
        'form': BusinessFeatureForm,
        'title': 'Feature',
        'plural': 'Features',
        'icon': 'stars',
        'show_field': 'show_features',
        'description': 'Explain the real benefits and capabilities customers receive.',
    },
    'maximise': {
        'model': MaximiseStep,
        'form': MaximiseStepForm,
        'title': 'Maximise Step',
        'plural': 'Learn How to Maximise',
        'icon': 'graph-up-arrow',
        'show_field': 'show_maximise',
        'description': 'Guide visitors through the best way to use your services or products.',
    },
    'faq': {
        'model': FAQItem,
        'form': FAQItemForm,
        'title': 'FAQ',
        'plural': 'Frequently Asked Questions',
        'icon': 'question-circle',
        'show_field': 'show_faq',
        'description': 'Answer common questions before a customer needs to call.',
    },
    'story': {
        'model': SuccessStory,
        'form': SuccessStoryForm,
        'title': 'Success Story',
        'plural': 'Success Stories',
        'icon': 'trophy',
        'show_field': 'show_success_stories',
        'description': 'Publish genuine outcomes, case studies and customer transformations.',
    },
    'dealer': {
        'model': DealerLocation,
        'form': DealerLocationForm,
        'title': 'Dealer Location',
        'plural': 'Nearest Dealers',
        'icon': 'geo-alt',
        'show_field': 'show_dealers',
        'description': 'Add branches or partners visitors can call, message or locate.',
    },
}


def _editable_organization(request):
    org = getattr(request.user, 'organization', None)
    if not org or not request.user.is_org_admin:
        return None
    return org


def _content_limit(org, field, fallback=1):
    if not org.plan:
        return fallback
    return getattr(org.plan, field, fallback)


def _enable_landing_section(org, field):
    """Keep newly enabled CMS content visible on the public landing page."""
    config, _ = LandingPageConfig.objects.get_or_create(organization=org)
    if not getattr(config, field):
        setattr(config, field, True)
        config.save(update_fields=[field, 'updated_at'])


def _cms_collections(org, page_config):
    collections = []
    for kind, config in CONTENT_TYPES.items():
        rows = []
        for item in config['model'].objects.filter(organization=org):
            if kind == 'faq':
                title, copy = item.question, item.answer
            elif kind == 'story':
                title, copy = item.title, item.story
            elif kind == 'dealer':
                title, copy = item.name, item.address
            else:
                title, copy = item.title, item.description
            rows.append({
                'item': item,
                'title': title,
                'copy': copy,
                'image': getattr(item, 'image', None),
            })
        collections.append({
            'kind': kind,
            'title': config['plural'],
            'description': config['description'],
            'icon': config['icon'],
            'rows': rows,
            'is_visible': getattr(page_config, config['show_field']),
        })
    return collections


@login_required
@require_POST
def page_config_update(request):
    """Save the owner-only landing-page editor without a full page reload."""
    org = _editable_organization(request)
    if not org:
        return JsonResponse({'ok': False, 'error': 'Access denied.'}, status=403)

    try:
        payload = json.loads(request.body or '{}')
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid request.'}, status=400)

    color_fields = ('primary_color', 'accent_color', 'background_color')
    colors = {}
    for field in color_fields:
        value = str(payload.get(field, '')).strip()
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            return JsonResponse(
                {'ok': False, 'error': f'{field.replace("_", " ").title()} is invalid.'},
                status=400,
            )
        colors[field] = value.lower()

    business_name = str(payload.get('business_name', '')).strip()
    hero_title = str(payload.get('hero_title', '')).strip()
    hero_subtitle = str(payload.get('hero_subtitle', '')).strip()
    description = str(payload.get('description', '')).strip()
    if not business_name or len(business_name) > 200:
        return JsonResponse(
            {'ok': False, 'error': 'Business name is required and must be under 200 characters.'},
            status=400,
        )
    if len(hero_title) > 220 or len(hero_subtitle) > 2000 or len(description) > 5000:
        return JsonResponse({'ok': False, 'error': 'One or more text fields are too long.'}, status=400)

    visibility_fields = (
        'show_stats',
        'show_featured_services',
        'show_promos',
        'show_about',
        'show_services',
        'show_products',
        'show_gallery',
        'show_testimonials',
        'show_payment',
        'show_contact',
        'show_plans',
        'show_features',
        'show_maximise',
        'show_faq',
        'show_success_stories',
        'show_dealers',
        'show_footer_map',
    )

    with transaction.atomic():
        org.name = business_name
        org.description = description
        org.save(update_fields=['name', 'description', 'updated_at'])
        config, _ = LandingPageConfig.objects.get_or_create(organization=org)
        config.hero_title = hero_title
        config.hero_subtitle = hero_subtitle
        for field, value in colors.items():
            setattr(config, field, value)
        for field in visibility_fields:
            setattr(config, field, payload.get(field) is True)
        config.save()

    return JsonResponse({
        'ok': True,
        'message': 'Page changes saved.',
        'updated_at': config.updated_at.isoformat(),
    })


@login_required
def page_cms(request):
    org = _editable_organization(request)
    if not org:
        messages.error(request, 'Only a business administrator can edit page content.')
        return redirect('dashboard')

    hero_slides = org.hero_slides.all()
    promo_banners = org.promo_banners.all()
    page_config, _ = LandingPageConfig.objects.get_or_create(organization=org)
    footer_form = FooterSettingsForm(initial={
        'facebook_url': org.facebook_url,
        'instagram_url': org.instagram_url,
        'linkedin_url': org.linkedin_url,
        'twitter_url': org.twitter_url,
        'google_maps_embed_url': page_config.google_maps_embed_url,
    })
    return render(request, 'page_cms.html', {
        'org': org,
        'hero_slides': hero_slides,
        'promo_banners': promo_banners,
        'hero_limit': _content_limit(org, 'max_hero_slides'),
        'promo_limit': _content_limit(org, 'max_promos'),
        'promos_visible': page_config.show_promos,
        'cms_collections': _cms_collections(org, page_config),
        'plans': Plan.objects.filter(is_active=True).order_by('order', 'level'),
        'footer_form': footer_form,
        'page_config': page_config,
    })


@login_required
def hero_create(request):
    org = _editable_organization(request)
    if not org:
        return redirect('dashboard')
    limit = _content_limit(org, 'max_hero_slides')
    if org.hero_slides.count() >= limit:
        messages.warning(request, f'Your plan allows {limit} hero slide(s).')
        return redirect('page_cms')

    form = HeroSlideForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.organization = org
        item.save()
        messages.success(request, 'Hero slide added.')
        return redirect('page_cms')
    return render(request, 'cms_item_form.html', {
        'form': form,
        'org': org,
        'title': 'Add Hero Slide',
        'item_type': 'hero',
    })


@login_required
def hero_edit(request, pk):
    org = _editable_organization(request)
    item = get_object_or_404(HeroSlide, pk=pk, organization=org)
    form = HeroSlideForm(request.POST or None, request.FILES or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Hero slide updated.')
        return redirect('page_cms')
    return render(request, 'cms_item_form.html', {
        'form': form,
        'org': org,
        'title': 'Edit Hero Slide',
        'item_type': 'hero',
        'item': item,
    })


@login_required
@require_POST
def hero_delete(request, pk):
    org = _editable_organization(request)
    item = get_object_or_404(HeroSlide, pk=pk, organization=org)
    item.delete()
    messages.success(request, 'Hero slide removed.')
    return redirect('page_cms')


@login_required
def promo_create(request):
    org = _editable_organization(request)
    if not org:
        return redirect('dashboard')
    limit = _content_limit(org, 'max_promos')
    if org.promo_banners.count() >= limit:
        messages.warning(request, f'Your plan allows {limit} promotional banner(s).')
        return redirect('page_cms')

    form = PromoBannerForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.organization = org
        item.save()
        if item.is_active:
            _enable_landing_section(org, 'show_promos')
        messages.success(request, 'Promotion added.')
        return redirect('page_cms')
    return render(request, 'cms_item_form.html', {
        'form': form,
        'org': org,
        'title': 'Add Promotion',
        'item_type': 'promo',
    })


@login_required
def promo_edit(request, pk):
    org = _editable_organization(request)
    item = get_object_or_404(PromoBanner, pk=pk, organization=org)
    form = PromoBannerForm(request.POST or None, request.FILES or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        if item.is_active:
            _enable_landing_section(org, 'show_promos')
        messages.success(request, 'Promotion updated.')
        return redirect('page_cms')
    return render(request, 'cms_item_form.html', {
        'form': form,
        'org': org,
        'title': 'Edit Promotion',
        'item_type': 'promo',
        'item': item,
    })


@login_required
@require_POST
def promo_delete(request, pk):
    org = _editable_organization(request)
    item = get_object_or_404(PromoBanner, pk=pk, organization=org)
    item.delete()
    messages.success(request, 'Promotion removed.')
    return redirect('page_cms')


@login_required
def content_create(request, kind):
    org = _editable_organization(request)
    config = CONTENT_TYPES.get(kind)
    if not org or config is None:
        messages.error(request, 'That CMS section is not available.')
        return redirect('dashboard')

    form = config['form'](request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.organization = org
        item.save()
        if item.is_active:
            _enable_landing_section(org, config['show_field'])
        messages.success(request, f"{config['title']} added.")
        return redirect('page_cms')
    return render(request, 'cms_item_form.html', {
        'form': form,
        'org': org,
        'title': f"Add {config['title']}",
        'item_type': kind,
    })


@login_required
def content_edit(request, kind, pk):
    org = _editable_organization(request)
    config = CONTENT_TYPES.get(kind)
    if not org or config is None:
        messages.error(request, 'That CMS section is not available.')
        return redirect('dashboard')

    item = get_object_or_404(config['model'], pk=pk, organization=org)
    form = config['form'](
        request.POST or None,
        request.FILES or None,
        instance=item,
    )
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        if item.is_active:
            _enable_landing_section(org, config['show_field'])
        messages.success(request, f"{config['title']} updated.")
        return redirect('page_cms')
    return render(request, 'cms_item_form.html', {
        'form': form,
        'org': org,
        'title': f"Edit {config['title']}",
        'item_type': kind,
        'item': item,
    })


@login_required
@require_POST
def content_delete(request, kind, pk):
    org = _editable_organization(request)
    config = CONTENT_TYPES.get(kind)
    if not org or config is None:
        messages.error(request, 'That CMS section is not available.')
        return redirect('dashboard')
    item = get_object_or_404(config['model'], pk=pk, organization=org)
    item.delete()
    messages.success(request, f"{config['title']} removed.")
    return redirect('page_cms')


@login_required
@require_POST
def footer_settings_update(request):
    org = _editable_organization(request)
    if not org:
        messages.error(request, 'Only a business administrator can edit footer content.')
        return redirect('dashboard')

    form = FooterSettingsForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            for field in ('facebook_url', 'instagram_url', 'linkedin_url', 'twitter_url'):
                setattr(org, field, form.cleaned_data[field])
            org.save(update_fields=[
                'facebook_url', 'instagram_url', 'linkedin_url', 'twitter_url', 'updated_at',
            ])
            page_config, _ = LandingPageConfig.objects.get_or_create(organization=org)
            page_config.google_maps_embed_url = form.cleaned_data['google_maps_embed_url']
            page_config.show_footer_map = True
            page_config.save(update_fields=[
                'google_maps_embed_url', 'show_footer_map', 'updated_at',
            ])
        messages.success(request, 'Footer social links and map updated.')
        return redirect('page_cms')

    hero_slides = org.hero_slides.all()
    promo_banners = org.promo_banners.all()
    page_config, _ = LandingPageConfig.objects.get_or_create(organization=org)
    messages.error(request, 'Please correct the footer settings below.')
    return render(request, 'page_cms.html', {
        'org': org,
        'hero_slides': hero_slides,
        'promo_banners': promo_banners,
        'hero_limit': _content_limit(org, 'max_hero_slides'),
        'promo_limit': _content_limit(org, 'max_promos'),
        'promos_visible': page_config.show_promos,
        'cms_collections': _cms_collections(org, page_config),
        'plans': Plan.objects.filter(is_active=True).order_by('order', 'level'),
        'footer_form': form,
        'page_config': page_config,
    }, status=400)


@login_required
@require_POST
def cms_item_update(request, kind, pk):
    """Small AJAX endpoint for fast active/order changes."""
    org = _editable_organization(request)
    model_map = {'hero': HeroSlide, 'promo': PromoBanner}
    model_map.update({
        item_kind: config['model'] for item_kind, config in CONTENT_TYPES.items()
    })
    model = model_map.get(kind)
    if not org or model is None:
        return JsonResponse({'ok': False, 'error': 'Access denied.'}, status=403)

    item = get_object_or_404(model, pk=pk, organization=org)
    try:
        payload = json.loads(request.body or '{}')
    except (TypeError, ValueError):
        payload = request.POST

    changed = []
    if 'is_active' in payload:
        value = payload['is_active']
        item.is_active = value is True or str(value).lower() in {'1', 'true', 'on', 'yes'}
        changed.append('is_active')
    if 'order' in payload:
        try:
            item.order = max(0, int(payload['order']))
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'Order must be a number.'}, status=400)
        changed.append('order')
    if changed:
        item.save(update_fields=changed + ['updated_at'])
        if item.is_active:
            if kind == 'promo':
                _enable_landing_section(org, 'show_promos')
            elif kind in CONTENT_TYPES:
                _enable_landing_section(org, CONTENT_TYPES[kind]['show_field'])
    return JsonResponse({'ok': True, 'id': item.pk, 'kind': kind})


@require_GET
def public_content_json(request, slug):
    """Cache-friendly JSON for AJAX/lazy public-page rendering."""
    org = get_object_or_404(
        Organization.objects.select_related('category', 'sub_category', 'plan'),
        slug=slug,
        is_active=True,
        status='active',
    )
    now = timezone.now()
    promos = org.promo_banners.filter(is_active=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gte=now),
    )
    payload = {
        'organization': {
            'name': org.name,
            'slug': org.slug,
            'tagline': org.tagline,
            'city': org.city,
            'category': org.category.name if org.category else '',
        },
        'heroes': [
            {
                'id': item.pk,
                'eyebrow': item.eyebrow,
                'title': item.title,
                'subtitle': item.subtitle,
                'image': request.build_absolute_uri(item.image.url) if item.image else '',
                'primary_label': item.primary_label,
                'primary_url': item.primary_url,
                'secondary_label': item.secondary_label,
                'secondary_url': item.secondary_url,
            }
            for item in org.hero_slides.filter(is_active=True)[:10]
        ],
        'promos': [
            {
                'id': item.pk,
                'badge': item.badge_text,
                'title': item.title,
                'description': item.description,
                'image': request.build_absolute_uri(item.image.url) if item.image else '',
                'cta_label': item.cta_label,
                'cta_url': item.cta_url,
            }
            for item in promos[:20]
        ],
        'services': list(org.services.filter(is_active=True).values(
            'id', 'name', 'description', 'price', 'price_unit', 'is_featured'
        )[:50]),
        'products': list(org.products.filter(is_active=True).values(
            'id', 'name', 'description', 'price', 'discount_price',
            'in_stock', 'is_featured'
        )[:50]),
        'features': list(org.landing_features.filter(is_active=True).values(
            'id', 'icon', 'title', 'description', 'order'
        )[:30]),
        'maximise_steps': list(org.maximise_steps.filter(is_active=True).values(
            'id', 'icon', 'title', 'description', 'cta_label', 'cta_url', 'order'
        )[:30]),
        'faqs': list(org.faq_items.filter(is_active=True).values(
            'id', 'question', 'answer', 'order'
        )[:50]),
        'success_stories': list(org.success_stories.filter(is_active=True).values(
            'id', 'business_name', 'title', 'story',
            'result_value', 'result_label', 'order'
        )[:30]),
        'dealers': list(org.dealer_locations.filter(is_active=True).values(
            'id', 'name', 'address', 'city', 'phone', 'whatsapp',
            'map_url', 'latitude', 'longitude', 'order'
        )[:50]),
        'plans': list(Plan.objects.filter(is_active=True).values(
            'id', 'name', 'level', 'price', 'duration_days', 'features', 'color', 'order'
        )[:20]),
    }
    response = JsonResponse(payload)
    response['Cache-Control'] = 'public, max-age=60, stale-while-revalidate=300'
    return response
