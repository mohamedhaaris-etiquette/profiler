from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser, Organization, Enquiry, Service, BusinessCategory, Product


class OrganizationSignupForm(forms.ModelForm):
    # User fields
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    username = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    user_email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Your Email'}))
    user_phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'placeholder': 'Your Phone'}))
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

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
            'name': forms.TextInput(attrs={'placeholder': 'Organization / Business Name'}),
            'tagline': forms.TextInput(attrs={'placeholder': 'e.g. Your trusted electrical partner'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Brief description of your business...'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Business Email'}),
            'phone': forms.TextInput(attrs={'placeholder': '+91 XXXXX XXXXX'}),
            'whatsapp': forms.TextInput(attrs={'placeholder': 'WhatsApp Number'}),
            'website': forms.URLInput(attrs={'placeholder': 'https://yourbusiness.com'}),
            'address_line1': forms.TextInput(attrs={'placeholder': 'Street / Building No.'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Area / Locality (Optional)'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'placeholder': 'PIN Code'}),
            'established_year': forms.TextInput(attrs={'placeholder': 'e.g. 2010'}),
            'gst_number': forms.TextInput(attrs={'placeholder': 'GST Number (Optional)'}),
            'working_hours': forms.TextInput(attrs={'placeholder': 'Mon-Sat: 9 AM - 6 PM'}),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
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


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Username', 'class': 'form-control form-control-lg'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Password', 'class': 'form-control form-control-lg'
    }))


class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ['name', 'email', 'phone', 'subject', 'service', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your Full Name', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Your Email', 'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone Number', 'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'placeholder': 'Subject', 'class': 'form-control'}),
            'message': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Your message...', 'class': 'form-control'}),
            'service': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, organization=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if organization:
            self.fields['service'].queryset = Service.objects.filter(organization=organization, is_active=True)
            self.fields['service'].required = False
            self.fields['service'].empty_label = 'Select a Service (Optional)'


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'price', 'price_unit', 'icon', 'is_featured']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Service Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'price_unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. per visit'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. tools'}),
        }


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
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Product description...'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SKU / Product Code'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Electronics, Tools'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brand name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optional sale price', 'step': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. piece, kg, box'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. box-seam, cpu, tools'}),
        }


class OrganizationUpdateForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            'name', 'logo', 'tagline', 'description',
            'email', 'phone', 'whatsapp', 'website',
            'address_line1', 'address_line2', 'city', 'state', 'pincode',
            'working_hours', 'is_open_sunday', 'accepts_online_payment', 'home_service_available',
            'facebook_url', 'instagram_url', 'linkedin_url', 'twitter_url',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control'}),
        }