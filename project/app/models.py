from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class BusinessCategory(models.Model):
    """Pre-set templates for business types (Electrician, Plumber, etc.)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, default='briefcase')  # Bootstrap icon name
    description = models.TextField(blank=True)
    default_services = models.JSONField(default=list)   # Pre-set services list
    color_primary = models.CharField(max_length=7, default='#2563eb')
    color_secondary = models.CharField(max_length=7, default='#1e40af')
    banner_tagline = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name_plural = 'Business Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Organization(models.Model):
    YEARS_CHOICES = [(str(y), str(y)) for y in range(1970, timezone.now().year + 1)][::-1]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(BusinessCategory, on_delete=models.SET_NULL, null=True,blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    tagline = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    # Contact details
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    whatsapp = models.CharField(max_length=15, blank=True)
    website = models.URLField(blank=True)

    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    # Business details (Justdial-like)
    established_year = models.CharField(max_length=4, blank=True)
    gst_number = models.CharField(max_length=20, blank=True)
    working_hours = models.CharField(max_length=100, default='Mon-Sat: 9 AM - 6 PM')
    is_open_sunday = models.BooleanField(default=False)
    accepts_online_payment = models.BooleanField(default=False)
    home_service_available = models.BooleanField(default=False)

    # Social media
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)

    # Meta
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base = slugify(self.name)
            slug = base
            n = 1
            while Organization.objects.filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_services(self):
        return self.services.filter(is_active=True)

    def get_full_address(self):
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts += [self.city, self.state, self.pincode]
        return ', '.join(parts)


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('org_admin', 'Organization Admin'),
        ('staff', 'Staff'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='org_admin')
    phone = models.CharField(max_length=15, blank=True)
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == 'super_admin' or self.is_superuser

    @property
    def is_org_admin(self):
        return self.role == 'org_admin'


class Service(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_unit = models.CharField(max_length=50, blank=True, help_text="e.g. per hour, per unit")
    icon = models.CharField(max_length=50, default='tools')
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class Enquiry(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='enquiries')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Internal notes")

    class Meta:
        verbose_name_plural = 'Enquiries'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} → {self.organization.name} ({self.subject})"


class GalleryImage(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='gallery/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.organization.name} - Image {self.pk}"


class Testimonial(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='testimonials')
    client_name = models.CharField(max_length=100)
    client_role = models.CharField(max_length=100, blank=True)
    message = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client_name} → {self.organization.name}"