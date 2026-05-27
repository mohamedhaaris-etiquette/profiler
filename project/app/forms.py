from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import (
    CustomUser, Organization, Enquiry, Service,
    BusinessCategory, SubCategory, Plan, Product
)


# ── Shared widget helpers ──────────────────────────────────────────────────────
FC  = 'form-control'
FS  = 'form-select'
FC_LG = 'form-control form-control-lg'


# ════════════════════════════════════════════════════════════════
#  ADD MEMBER — STEP 1  (Site details + Plan)
#  Filled by Admin staff when creating a new member/organisation
# ════════════════════════════════════════════════════════════════
class AddMemberStep1Form(forms.Form):
    """
    Step 1 — Site URL (subdomain), Site Title, Main Category,
              Sub Category, Plan selection.
    """
    site_url = forms.SlugField(
        label='Site URL (Subdomain)',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': FC,
            'placeholder': 'e.g. johns-electricals',
        }),
        help_text='Subdomain name assigned by Admin.'
    )
    site_title = forms.CharField(
        label='Site Title (Business Name)',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': FC,
            'placeholder': 'Business / Organisation Name',
        }),
    )
    main_category = forms.ModelChoiceField(
        queryset=BusinessCategory.objects.all(),
        empty_label='Please select a Category',
        widget=forms.Select(attrs={'class': FS, 'id': 'id_main_category'}),
    )
    sub_category = forms.ModelChoiceField(
        queryset=SubCategory.objects.none(),   # populated via JS / __init__
        required=False,
        empty_label='Please select sub category',
        widget=forms.Select(attrs={'class': FS, 'id': 'id_sub_category'}),
    )
    plan = forms.ModelChoiceField(
        queryset=Plan.objects.filter(is_active=True).order_by('order'),
        empty_label='Please select a Plan',
        widget=forms.Select(attrs={'class': FS}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If main_category is bound, filter sub_category queryset
        if 'main_category' in self.data:
            try:
                cat_id = int(self.data.get('main_category'))
                self.fields['sub_category'].queryset = SubCategory.objects.filter(
                    main_category_id=cat_id, is_active=True
                )
            except (ValueError, TypeError):
                pass
        elif self.initial.get('main_category'):
            self.fields['sub_category'].queryset = SubCategory.objects.filter(
                main_category=self.initial['main_category'], is_active=True
            )

    def clean_site_url(self):
        url = self.cleaned_data['site_url'].lower().strip()
        if Organization.objects.filter(subdomain=url).exists():
            raise forms.ValidationError('This subdomain is already in use.')
        return url


# ════════════════════════════════════════════════════════════════
#  ADD MEMBER — STEP 2  (Contact + Account + Plan dates + Status)
# ════════════════════════════════════════════════════════════════
class AddMemberStep2Form(forms.Form):
    """
    Step 2 — Contact Name, Company Name, Email, Mobile, WhatsApp,
              Landline, Profile Picture, Gender, DOB, Password,
              Address, City, District, State, Pincode, User Role,
              Plan Start/End Date, Website, Status, File Attachment.
    """
    # ── Contact / Account ─────────────────────────────────────────
    contact_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'Full Name'}),
    )
    company_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'Company / Business Name'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': FC, 'placeholder': 'Email Address'}),
    )
    mobile = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'Mobile Number'}),
    )
    whatsapp = forms.CharField(
        max_length=15, required=False,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'WhatsApp Number'}),
    )
    landline = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'Landline Number'}),
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': FC}),
    )
    gender = forms.ChoiceField(
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        widget=forms.RadioSelect(),
        initial='male',
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': FC, 'type': 'date', 'placeholder': 'Date of Birth'}),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': FC, 'placeholder': '••••••••••••'}),
    )

    # ── Address ───────────────────────────────────────────────────
    address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'Street / Building No.'}),
    )
    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'City'}),
    )
    district = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'District'}),
    )
    state = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'State'}),
    )
    pincode = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'PIN Code'}),
    )

    # ── Role & Plan dates ─────────────────────────────────────────
    user_role = forms.ChoiceField(
        choices=[
            ('',          'Please select a User Role'),
            ('org_admin', 'Organization Admin'),
            ('staff',     'Staff'),
        ],
        widget=forms.Select(attrs={'class': FS}),
    )
    plan_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': FC, 'type': 'date', 'placeholder': 'Plan Start Date'}),
    )
    plan_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': FC, 'type': 'date', 'placeholder': 'Plan End Date'}),
    )

    # ── Website / Status / Attachment ─────────────────────────────
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': FC, 'placeholder': 'https://yourbusiness.com'}),
    )
    status = forms.ChoiceField(
        choices=[
            ('',          'Please select a Status'),
            ('active',    'Active'),
            ('inactive',  'Inactive'),
            ('suspended', 'Suspended'),
            ('pending',   'Pending'),
        ],
        widget=forms.Select(attrs={'class': FS}),
    )
    file_attachment = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': FC}),
        help_text='Optional document (agreement, certificate, etc.)',
    )

    # ── Also need username for the login account ───────────────────
    username = forms.CharField(
        max_length=50, required=False,
        widget=forms.TextInput(attrs={'class': FC, 'placeholder': 'Login Username (auto if blank)'}),
        help_text='Leave blank to auto-generate from email.',
    )

    def clean_password(self):
        pwd = self.cleaned_data.get('password', '')
        if len(pwd) < 6:
            raise forms.ValidationError('Password must be at least 6 characters.')
        return pwd

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if username and CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('plan_start_date')
        end = cleaned.get('plan_end_date')
        if start and end and end < start:
            self.add_error('plan_end_date', 'Plan end date must be after start date.')
        return cleaned


# ════════════════════════════════════════════════════════════════
#  Original public signup (unchanged, kept for referral flow)
# ════════════════════════════════════════════════════════════════
class OrganizationSignupForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': FC}))
    last_name  = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': FC}))
    username   = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': FC}))
    user_email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Your Email', 'class': FC}))
    user_phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'placeholder': 'Your Phone', 'class': FC}))
    password1  = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': FC}))
    password2  = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': FC}))

    class Meta:
        model = Organization
        fields = [
            'name', 'category', 'logo', 'tagline', 'description',
            'email', 'phone', 'whatsapp', 'website',
            'address_line1', 'address_line2', 'city', 'state', 'pincode',
            'established_year', 'gst_number', 'working_hours',
            'is_open_sunday', 'accepts_online_payment', 'home_service_available',
        ]
        widgets = {
            'name':          forms.TextInput(attrs={'placeholder': 'Organization / Business Name', 'class': FC}),
            'tagline':       forms.TextInput(attrs={'placeholder': 'e.g. Your trusted electrical partner', 'class': FC}),
            'description':   forms.Textarea(attrs={'rows': 3, 'placeholder': 'Brief description...', 'class': FC}),
            'email':         forms.EmailInput(attrs={'placeholder': 'Business Email', 'class': FC}),
            'phone':         forms.TextInput(attrs={'placeholder': '+91 XXXXX XXXXX', 'class': FC}),
            'whatsapp':      forms.TextInput(attrs={'placeholder': 'WhatsApp Number', 'class': FC}),
            'website':       forms.URLInput(attrs={'placeholder': 'https://yourbusiness.com', 'class': FC}),
            'address_line1': forms.TextInput(attrs={'placeholder': 'Street / Building No.', 'class': FC}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Area / Locality (Optional)', 'class': FC}),
            'city':          forms.TextInput(attrs={'placeholder': 'City', 'class': FC}),
            'state':         forms.TextInput(attrs={'placeholder': 'State', 'class': FC}),
            'pincode':       forms.TextInput(attrs={'placeholder': 'PIN Code', 'class': FC}),
            'established_year': forms.TextInput(attrs={'placeholder': 'e.g. 2010', 'class': FC}),
            'gst_number':    forms.TextInput(attrs={'placeholder': 'GST Number (Optional)', 'class': FC}),
            'working_hours': forms.TextInput(attrs={'placeholder': 'Mon-Sat: 9 AM - 6 PM', 'class': FC}),
        }

    def clean_password2(self):
        p1, p2 = self.cleaned_data.get('password1'), self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords don't match.")
        if p1 and len(p1) < 6:
            raise forms.ValidationError("Password must be at least 6 characters.")
        return p2

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username


# ── Login ──────────────────────────────────────────────────────────────────────
class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Username', 'class': FC_LG
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Password', 'class': FC_LG
    }))

class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ['name', 'phone', 'email', 'service', 'product', 'subject', 'message']

    def __init__(self, organization=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['service'].queryset = Service.objects.filter(
                organization=organization, is_active=True
            )
            self.fields['product'].queryset = Product.objects.filter(  # ← ADD THIS
                organization=organization, is_active=True
            )
        self.fields['service'].required = False
        self.fields['product'].required = False

# ── Service ───────────────────────────────────────────────────────────────────
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'price', 'price_unit', 'icon', 'is_featured']
        widgets = {
            'name':        forms.TextInput(attrs={'class': FC, 'placeholder': 'Service Name'}),
            'description': forms.Textarea(attrs={'class': FC, 'rows': 3}),
            'price':       forms.NumberInput(attrs={'class': FC, 'placeholder': '0.00'}),
            'price_unit':  forms.TextInput(attrs={'class': FC, 'placeholder': 'e.g. per visit'}),
            'icon':        forms.TextInput(attrs={'class': FC, 'placeholder': 'e.g. tools'}),
        }


# ── Product ───────────────────────────────────────────────────────────────────
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'sku', 'category', 'brand',
            'price', 'discount_price', 'stock_quantity', 'unit',
            'condition', 'icon', 'image', 'image2', 'image3',
            'is_featured', 'in_stock', 'is_active',
        ]
        widgets = {
            'name':           forms.TextInput(attrs={'class': FC, 'placeholder': 'Product Name'}),
            'description':    forms.Textarea(attrs={'class': FC, 'rows': 3}),
            'sku':            forms.TextInput(attrs={'class': FC, 'placeholder': 'SKU / Product Code'}),
            'category':       forms.TextInput(attrs={'class': FC, 'placeholder': 'e.g. Electronics, Tools'}),
            'brand':          forms.TextInput(attrs={'class': FC, 'placeholder': 'Brand name'}),
            'price':          forms.NumberInput(attrs={'class': FC, 'placeholder': '0.00', 'step': '0.01'}),
            'discount_price': forms.NumberInput(attrs={'class': FC, 'placeholder': 'Optional sale price', 'step': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'class': FC, 'placeholder': '0'}),
            'unit':           forms.TextInput(attrs={'class': FC, 'placeholder': 'e.g. piece, kg, box'}),
            'condition':      forms.Select(attrs={'class': FS}),
            'icon':           forms.TextInput(attrs={'class': FC, 'placeholder': 'e.g. box-seam'}),
        }


# ── Organisation Update ───────────────────────────────────────────────────────
class OrganizationUpdateForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            'name', 'logo', 'tagline', 'description',
            'email', 'phone', 'whatsapp', 'landline', 'website',
            'address_line1', 'address_line2', 'city', 'district', 'state', 'pincode',
            'working_hours', 'is_open_sunday', 'accepts_online_payment', 'home_service_available',
            'facebook_url', 'instagram_url', 'linkedin_url', 'twitter_url',
            'status',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': FC}),
            'tagline':     forms.TextInput(attrs={'class': FC}),
            'landline':    forms.TextInput(attrs={'class': FC, 'placeholder': 'Landline Number'}),
            'district':    forms.TextInput(attrs={'class': FC, 'placeholder': 'District'}),
            'status':      forms.Select(attrs={'class': FS}),
        }

# ── Super Admin Registration ───────────────────────────────────────────────────
class SuperAdminRegisterForm(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
    )
    last_name = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name (optional)'}),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
    )
    phone = forms.CharField(
        max_length=15, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password', 'id': 'id_password1'}),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password', 'id': 'id_password2'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned_data