from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class BusinessCategory(models.Model):
    """Pre-set templates for business types (Electrician, Plumber, etc.)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, default='briefcase')
    description = models.TextField(blank=True)
    default_services = models.JSONField(default=list)
    color_primary = models.CharField(max_length=7, default='#2563eb')
    color_secondary = models.CharField(max_length=7, default='#1e40af')
    banner_tagline = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name_plural = 'Business Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


# ── NEW: Sub Category ─────────────────────────────────────────────────────────
class SubCategory(models.Model):
    """Sub-categories under a main BusinessCategory"""
    main_category = models.ForeignKey(
        BusinessCategory, on_delete=models.CASCADE, related_name='sub_categories'
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)
    icon = models.CharField(max_length=50, default='tag')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Sub Categories'
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.main_category.name} → {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(f"{self.main_category.slug}-{self.name}")
        super().save(*args, **kwargs)


# ── NEW: Plan ─────────────────────────────────────────────────────────────────
class Plan(models.Model):
    """Subscription plans — Trial / Silver / Gold / Platinum (managed by Admin)"""
    PLAN_LEVEL_CHOICES = [
        ('trial',    'Trial'),
        ('silver',   'Silver'),
        ('gold',     'Gold'),
        ('platinum', 'Platinum'),
    ]
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=PLAN_LEVEL_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.PositiveIntegerField(
        default=30, help_text='Plan validity in days (e.g. 30, 365)'
    )
    max_services = models.PositiveIntegerField(default=5, help_text='Max services allowed')
    max_products = models.PositiveIntegerField(default=10, help_text='Max products allowed')
    max_staff = models.PositiveIntegerField(default=1, help_text='Max staff accounts')
    features = models.JSONField(default=list, help_text='List of feature strings')
    is_active = models.BooleanField(default=True)
    color = models.CharField(max_length=7, default='#2563eb', help_text='Badge color (hex)')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'level']

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"

    @property
    def badge_color_map(self):
        return {
            'trial':    '#6b7280',
            'silver':   '#64748b',
            'gold':     '#d97706',
            'platinum': '#7c3aed',
        }.get(self.level, '#2563eb')


# ── Organization ──────────────────────────────────────────────────────────────
class Organization(models.Model):
    """Represents a business/company registered on the platform"""
    YEARS_CHOICES = [(str(y), str(y)) for y in range(1970, timezone.now().year + 1)][::-1]

    STATUS_CHOICES = [
        ('active',    'Active'),
        ('inactive',  'Inactive'),
        ('suspended', 'Suspended'),
        ('pending',   'Pending'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)

    # ── NEW: subdomain (given by Admin) ──────────────────────────────────────
    subdomain = models.SlugField(
        max_length=100, unique=True, blank=True, null=True,
        help_text='Subdomain name assigned by Admin (e.g. "johns-electricals")'
    )

    category = models.ForeignKey(
        BusinessCategory, on_delete=models.SET_NULL, null=True, blank=True
    )

    # ── NEW: sub category ────────────────────────────────────────────────────
    sub_category = models.ForeignKey(
        SubCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='organizations'
    )

    # ── NEW: plan ─────────────────────────────────────────────────────────────
    plan = models.ForeignKey(
        Plan, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='organizations'
    )
    plan_start_date = models.DateField(null=True, blank=True)
    plan_end_date = models.DateField(null=True, blank=True)

    # ── NEW: status ───────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active'
    )

    

    # ── NEW: file attachment ──────────────────────────────────────────────────
    file_attachment = models.FileField(
        upload_to='org_attachments/', blank=True, null=True,
        help_text='Optional document attachment (agreement, certificate, etc.)'
    )

    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    tagline = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    # Contact details
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    whatsapp = models.CharField(max_length=15, blank=True)
    landline = models.CharField(max_length=20, blank=True)   # ── NEW
    website = models.URLField(blank=True)

    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True)  # ── NEW
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    # Business details
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
        parts += [self.city]
        if self.district:
            parts.append(self.district)
        parts += [self.state, self.pincode]
        return ', '.join(parts)

    @property
    def is_plan_active(self):
        if not self.plan_end_date:
            return False
        return self.plan_end_date >= timezone.now().date()

    @property
    def plan_badge_color(self):
        return self.plan.badge_color_map if self.plan else '#6b7280'


# ── CustomUser ────────────────────────────────────────────────────────────────
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('org_admin',   'Organization Admin'),
        ('staff',       'Staff'),
    ]
    GENDER_CHOICES = [
        ('male',   'Male'),
        ('female', 'Female'),
        ('other',  'Other'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        null=True, blank=True, related_name='members'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='org_admin')
    phone = models.CharField(max_length=15, blank=True)
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)

    # ── NEW fields ────────────────────────────────────────────────────────────
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, blank=True, default='male'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    landline = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_super_admin(self):
        return self.role == 'super_admin' or self.is_superuser

    @property
    def is_org_admin(self):
        return self.role == 'org_admin'


# ── Service ───────────────────────────────────────────────────────────────────
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


# ── Enquiry ───────────────────────────────────────────────────────────────────
class Enquiry(models.Model):
    STATUS_CHOICES = [
        ('new',         'New'),
        ('contacted',   'Contacted'),
        ('in_progress', 'In Progress'),
        ('resolved',    'Resolved'),
        ('closed',      'Closed'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='enquiries')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Internal notes")

    class Meta:
        verbose_name_plural = 'Enquiries'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} → {self.organization.name} ({self.subject})"


# ── GalleryImage ──────────────────────────────────────────────────────────────
class GalleryImage(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='gallery/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.organization.name} - Image {self.pk}"


# ── Product ───────────────────────────────────────────────────────────────────
class Product(models.Model):
    CONDITION_CHOICES = [
        ('new',         'New'),
        ('used',        'Used'),
        ('refurbished', 'Refurbished'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=100, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=50, default='piece')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    icon = models.CharField(max_length=50, default='box-seam')
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    in_stock = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.organization.name} — {self.name}"

    @property
    def discount_percent(self):
        if self.discount_price and self.price > 0:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price else self.price


# ── Testimonial ───────────────────────────────────────────────────────────────
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


# ── Referral System ───────────────────────────────────────────────────────────
import uuid as _uuid


class ReferralProgram(models.Model):
    name = models.CharField(max_length=100, default='Default Program')
    points_per_referral = models.PositiveIntegerField(default=100)
    bonus_description = models.CharField(max_length=200, default='100 OrgPoints per successful referral')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.points_per_referral} pts)"


class ReferralCode(models.Model):
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name='referral_code'
    )
    code = models.CharField(max_length=12, unique=True, db_index=True)
    total_clicks = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organization.name} → {self.code}"

    @staticmethod
    def generate_code():
        import random, string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    def get_invite_url(self, request=None):
        from django.urls import reverse
        path = reverse('signup_with_ref', args=[self.code])
        if request:
            return request.build_absolute_uri(path)
        return path

    def get_whatsapp_url(self, request=None):
        import urllib.parse
        url = self.get_invite_url(request)
        org = self.organization
        msg = (
            f"Hi!  I'm using OrgPortal to manage my business *{org.name}*. "
            f"Register your business using my invite link and we both get bonus points!\n\n"
            f"{url}\n\n"
            f"Use referral code: *{self.code}*"
        )
        return f"https://wa.me/?text={urllib.parse.quote(msg)}"


class Referral(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('rewarded',  'Rewarded'),
    ]
    referrer = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='referrals_made')
    referred = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='referred_by', null=True, blank=True)
    code = models.ForeignKey(ReferralCode, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    points_awarded = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.referrer.name} referred {self.referred.name if self.referred else '?'}"


class ReferralBonus(models.Model):
    TRANSACTION_TYPES = [
        ('earn',   'Earned'),
        ('redeem', 'Redeemed'),
        ('expire', 'Expired'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='bonus_transactions')
    referral = models.ForeignKey(Referral, on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, default='earn')
    points = models.IntegerField()
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.organization.name}: {'+' if self.points > 0 else ''}{self.points} pts"

    @classmethod
    def get_balance(cls, organization):
        from django.db.models import Sum
        result = cls.objects.filter(organization=organization).aggregate(total=Sum('points'))
        return result['total'] or 0