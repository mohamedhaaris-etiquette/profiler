"""
forms.py — Portal Platform
All Django forms used across views.py and views_features.py
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify
from urllib.parse import urlparse

from .models import (
    Organization, CustomUser, Service, Product,
    BusinessCategory, SubCategory, Plan, Enquiry,
    HeroSlide, PromoBanner, BusinessFeature, MaximiseStep,
    FAQItem, SuccessStory, DealerLocation,
)


def _clean_cms_link(value):
    value = (value or '').strip()
    allowed = ('#', '/', 'https://', 'http://', 'tel:', 'mailto:')
    if value and not value.startswith(allowed):
        raise forms.ValidationError(
            'Use a section link (#enquiry), a local path (/contact/), or a full http(s) URL.'
        )
    return value


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH FORMS
# ══════════════════════════════════════════════════════════════════════════════

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or email',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )


class SuperAdminRegisterForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    phone = forms.CharField(
        max_length=15, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone (optional)'})
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1', '')
        p2 = cleaned.get('password2', '')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        return cleaned


# ══════════════════════════════════════════════════════════════════════════════
#  ORGANISATION SIGNUP FORM
# ══════════════════════════════════════════════════════════════════════════════

class OrganizationSignupForm(forms.ModelForm):
    """Used in public signup and signup_with_ref."""

    # User fields (not on Organization model)
    first_name  = forms.CharField(max_length=50,  widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name   = forms.CharField(max_length=50,  required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    username    = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    user_email  = forms.EmailField(label='Your Email', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    user_phone  = forms.CharField(max_length=15,  widget=forms.TextInput(attrs={'class': 'form-control'}))
    password1   = forms.CharField(label='Password',         widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2   = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model  = Organization
        fields = [
            'name', 'category', 'email', 'phone', 'whatsapp',
            'address_line1', 'address_line2', 'city', 'state', 'pincode',
            'logo', 'tagline', 'description', 'website',
            'gst_number', 'working_hours',
        ]
        widgets = {
            'name':         forms.TextInput(attrs={'class': 'form-control'}),
            'category':     forms.Select(attrs={'class': 'form-select'}),
            'email':        forms.EmailInput(attrs={'class': 'form-control'}),
            'phone':        forms.TextInput(attrs={'class': 'form-control'}),
            'whatsapp':     forms.TextInput(attrs={'class': 'form-control'}),
            'address_line1':forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2':forms.TextInput(attrs={'class': 'form-control'}),
            'city':         forms.TextInput(attrs={'class': 'form-control'}),
            'state':        forms.TextInput(attrs={'class': 'form-control'}),
            'pincode':      forms.TextInput(attrs={'class': 'form-control'}),
            'tagline':      forms.TextInput(attrs={'class': 'form-control'}),
            'description':  forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'website':      forms.URLInput(attrs={'class': 'form-control'}),
            'gst_number':   forms.TextInput(attrs={'class': 'form-control'}),
            'working_hours':forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_username(self):
        u = self.cleaned_data['username']
        if CustomUser.objects.filter(username=u).exists():
            raise forms.ValidationError('Username already taken.')
        return u

    def clean_user_email(self):
        e = self.cleaned_data['user_email'].lower()
        if CustomUser.objects.filter(email=e).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return e

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password1')
        if password != cleaned.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        if password:
            validate_password(password)
        return cleaned


# ══════════════════════════════════════════════════════════════════════════════
#  ORGANISATION UPDATE FORM (Dashboard Settings)
# ══════════════════════════════════════════════════════════════════════════════
class OrganizationUpdateForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            'name',
            'tagline',
            'description',
            'logo',

            'email',
            'phone',
            'whatsapp',
            'website',

            'address_line1',
            'address_line2',
            'city',
            'state',
            'pincode',

            'facebook_url',
            'instagram_url',
            'linkedin_url',
            'twitter_url',

            'working_hours',
            'is_open_sunday',
            'accepts_online_payment',
            'home_service_available',
        ]

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
            }),
            'logo': forms.FileInput(attrs={
    'class': 'form-control',
    'accept': 'image/png,image/jpeg,image/webp',
}),

            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),

            'address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),

            'facebook_url': forms.URLInput(attrs={'class': 'form-control'}),
            'instagram_url': forms.URLInput(attrs={'class': 'form-control'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control'}),
            'twitter_url': forms.URLInput(attrs={'class': 'form-control'}),

            'working_hours': forms.TextInput(attrs={'class': 'form-control'}),
            'is_open_sunday': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'accepts_online_payment': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'home_service_available': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }

class HeroSlideForm(forms.ModelForm):
    class Meta:
        model = HeroSlide
        fields = [
            'eyebrow', 'title', 'subtitle', 'image',
            'primary_label', 'primary_url',
            'secondary_label', 'secondary_url',
            'is_active', 'order',
        ]
        widgets = {
            'eyebrow': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'subtitle': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'primary_label': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_url': forms.TextInput(attrs={'class': 'form-control'}),
            'secondary_label': forms.TextInput(attrs={'class': 'form-control'}),
            'secondary_url': forms.TextInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def clean_primary_url(self):
        return _clean_cms_link(self.cleaned_data.get('primary_url'))

    def clean_secondary_url(self):
        return _clean_cms_link(self.cleaned_data.get('secondary_url'))


class PromoBannerForm(forms.ModelForm):
    class Meta:
        model = PromoBanner
        fields = [
            'badge_text', 'title', 'description', 'image',
            'cta_label', 'cta_url', 'starts_at', 'ends_at',
            'is_active', 'order',
        ]
        widgets = {
            'badge_text': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'cta_label': forms.TextInput(attrs={'class': 'form-control'}),
            'cta_url': forms.TextInput(attrs={'class': 'form-control'}),
            'starts_at': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'ends_at': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['starts_at'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['ends_at'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean(self):
        cleaned = super().clean()
        starts_at = cleaned.get('starts_at')
        ends_at = cleaned.get('ends_at')
        if starts_at and ends_at and ends_at <= starts_at:
            raise forms.ValidationError('The promotion end time must be after its start time.')
        return cleaned

    def clean_cta_url(self):
        return _clean_cms_link(self.cleaned_data.get('cta_url'))


class BusinessFeatureForm(forms.ModelForm):
    class Meta:
        model = BusinessFeature
        fields = ['icon', 'title', 'description', 'is_active', 'order']
        widgets = {
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class MaximiseStepForm(forms.ModelForm):
    class Meta:
        model = MaximiseStep
        fields = [
            'icon', 'title', 'description', 'cta_label', 'cta_url',
            'is_active', 'order',
        ]
        widgets = {
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'cta_label': forms.TextInput(attrs={'class': 'form-control'}),
            'cta_url': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def clean_cta_url(self):
        return _clean_cms_link(self.cleaned_data.get('cta_url'))


class FAQItemForm(forms.ModelForm):
    class Meta:
        model = FAQItem
        fields = ['question', 'answer', 'is_active', 'order']
        widgets = {
            'question': forms.TextInput(attrs={'class': 'form-control'}),
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class SuccessStoryForm(forms.ModelForm):
    class Meta:
        model = SuccessStory
        fields = [
            'business_name', 'title', 'story', 'result_value',
            'result_label', 'image', 'is_active', 'order',
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'story': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'result_value': forms.TextInput(attrs={'class': 'form-control'}),
            'result_label': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class DealerLocationForm(forms.ModelForm):
    class Meta:
        model = DealerLocation
        fields = [
            'name', 'address', 'city', 'phone', 'whatsapp', 'map_url',
            'latitude', 'longitude', 'is_active', 'order',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control'}),
            'map_url': forms.URLInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.000001', 'min': -90, 'max': 90,
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.000001', 'min': -180, 'max': 180,
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def clean(self):
        cleaned = super().clean()
        latitude = cleaned.get('latitude')
        longitude = cleaned.get('longitude')
        if (latitude is None) != (longitude is None):
            raise forms.ValidationError('Enter both latitude and longitude, or leave both blank.')
        return cleaned


class FooterSettingsForm(forms.Form):
    facebook_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://facebook.com/...'}),
    )
    instagram_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://instagram.com/...'}),
    )
    linkedin_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://linkedin.com/...'}),
    )
    twitter_url = forms.URLField(
        label='X / Twitter URL',
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://x.com/...'}),
    )
    google_maps_embed_url = forms.URLField(
        label='Google Maps embed URL',
        max_length=1000,
        required=False,
        help_text='In Google Maps choose Share → Embed a map, then paste only the iframe src URL.',
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://www.google.com/maps/embed?pb=...',
        }),
    )

    def clean_google_maps_embed_url(self):
        value = (self.cleaned_data.get('google_maps_embed_url') or '').strip()
        if not value:
            return ''
        parsed = urlparse(value)
        hostname = (parsed.hostname or '').lower()
        allowed_hosts = {
            'google.com', 'www.google.com', 'maps.google.com',
            'google.co.in', 'www.google.co.in', 'maps.google.co.in',
        }
        if parsed.scheme != 'https' or hostname not in allowed_hosts or '/maps' not in parsed.path:
            raise forms.ValidationError('Paste a secure Google Maps embed URL.')
        return value


# ══════════════════════════════════════════════════════════════════════════════
#  SERVICE FORM
# ══════════════════════════════════════════════════════════════════════════════

class ServiceForm(forms.ModelForm):
    class Meta:
        model  = Service
        fields = [
            'name', 'description', 'price', 'price_unit',
            'icon', 'video_url', 'tags',
            'image', 'image2', 'banner_image', 'before_image', 'after_image',
            'is_featured', 'is_active', 'order',
        ]
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'price_unit':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. per hour'}),
            'icon':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bootstrap icon name'}),
            'video_url':   forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtu.be/...'}),
            'tags':        forms.HiddenInput(attrs={'id': 'tagsHidden'}),
            'image':       forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image2':      forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'banner_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'before_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'after_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'order':       forms.HiddenInput(),
        }

    def clean_tags(self):
        raw_tags = self.cleaned_data.get('tags', '')
        tags = []
        for tag in raw_tags.split(','):
            clean_tag = tag.strip()
            if clean_tag and clean_tag.lower() not in [item.lower() for item in tags]:
                tags.append(clean_tag)
        return ','.join(tags)


# ══════════════════════════════════════════════════════════════════════════════
#  PRODUCT FORM
# ══════════════════════════════════════════════════════════════════════════════

class ProductForm(forms.ModelForm):
    class Meta:
        model  = Product
        fields = [
            'name', 'description', 'sku', 'category', 'brand',
            'price', 'discount_price', 'stock_quantity', 'unit', 'condition',
            'image', 'image2', 'image3', 'icon',
            'is_featured', 'is_active', 'in_stock', 'order',
            'youtube_url', 'instagram_url', 'pdf_catalog', 'specs_json',
        ]
        widgets = {
            'name':           forms.TextInput(attrs={'class': 'form-control'}),
            'description':    forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sku':            forms.TextInput(attrs={'class': 'form-control'}),
            'category':       forms.TextInput(attrs={'class': 'form-control'}),
            'brand':          forms.TextInput(attrs={'class': 'form-control'}),
            'price':          forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'unit':           forms.TextInput(attrs={'class': 'form-control'}),
            'condition':      forms.Select(attrs={'class': 'form-select'}),
            'icon':           forms.TextInput(attrs={'class': 'form-control'}),
            'order':          forms.HiddenInput(),
            'youtube_url':    forms.URLInput(attrs={'class': 'form-control'}),
            'instagram_url':  forms.URLInput(attrs={'class': 'form-control'}),
            'specs_json':     forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 7,
                'placeholder': '{"color": "red", "size": "L"}',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get('price')
        discount_price = cleaned.get('discount_price')
        if price is not None and discount_price is not None and discount_price > price:
            self.add_error('discount_price', 'Sale price must be less than or equal to the regular price.')
        return cleaned

    def clean_specs_json(self):
        return self.cleaned_data.get('specs_json') or {}


# ══════════════════════════════════════════════════════════════════════════════
#  ENQUIRY FORM (Public)
# ══════════════════════════════════════════════════════════════════════════════

class EnquiryForm(forms.ModelForm):
    """Rendered on the public landing page."""

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        if organization:
            self.fields['service'].queryset = organization.services.filter(is_active=True)
            self.fields['product'].queryset = organization.products.filter(is_active=True)
        else:
            self.fields['service'].queryset = Service.objects.none()
            self.fields['product'].queryset = Product.objects.none()

    class Meta:
        model  = Enquiry
        fields = ['name', 'email', 'phone', 'subject', 'message', 'service', 'product']
        widgets = {
            'name':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'email':   forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'phone':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'How can we help?'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us more about your requirement...'}),
            'service': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        digits = phone.replace('+', '').replace('-', '').replace(' ', '')
        if len(digits) < 7:
            raise forms.ValidationError('Please enter a valid phone number.')
        return phone


# ══════════════════════════════════════════════════════════════════════════════
#  ADD MEMBER — TWO-STEP WIZARD
# ══════════════════════════════════════════════════════════════════════════════

class AddMemberStep1Form(forms.Form):
    """Step 1: URL, category, plan."""
    site_url = forms.SlugField(
        label='Site URL / Subdomain',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. johns-electricals',
        })
    )
    site_title = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Site / Business Title'})
    )
    main_category = forms.ModelChoiceField(
        queryset=BusinessCategory.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_main_category'})
    )
    sub_category = forms.ModelChoiceField(
        queryset=SubCategory.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_sub_category'})
    )
    plan = forms.ModelChoiceField(
        queryset=Plan.objects.filter(is_active=True).order_by('order'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_site_url(self):
        slug = self.cleaned_data['site_url'].lower()
        from .models import Organization
        if Organization.objects.filter(subdomain=slug).exists():
            raise forms.ValidationError(f'The subdomain "{slug}" is already taken.')
        return slug


class AddMemberStep2Form(forms.Form):
    """Step 2: Contact details, credentials."""
    company_name   = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business / Company Name'}))
    contact_name   = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Owner / Contact Full Name'}))
    email          = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    mobile         = forms.CharField(max_length=15,  widget=forms.TextInput(attrs={'class': 'form-control'}))
    whatsapp       = forms.CharField(max_length=15,  required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    landline       = forms.CharField(max_length=20,  required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    website        = forms.URLField(required=False,  widget=forms.URLInput(attrs={'class': 'form-control'}))

    address        = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    city           = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    district       = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    state          = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    pincode        = forms.CharField(max_length=10,  widget=forms.TextInput(attrs={'class': 'form-control'}))

    plan_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    plan_end_date   = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    status = forms.ChoiceField(
        choices=Organization.STATUS_CHOICES,
        initial='active',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    file_attachment = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    username        = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Auto-generated if blank'}))
    password        = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password_confirm= forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    user_role       = forms.ChoiceField(
        choices=[('org_admin', 'Org Admin'), ('staff', 'Staff')],
        initial='org_admin',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    gender          = forms.ChoiceField(
        choices=CustomUser.GENDER_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_of_birth   = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        from .models import CustomUser
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_pincode(self):
        pc = self.cleaned_data.get('pincode', '').strip()
        if not pc.isdigit():
            raise forms.ValidationError('Pincode must be numeric.')
        return pc

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password', '')
        p2 = cleaned.get('password_confirm', '')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        return cleaned
