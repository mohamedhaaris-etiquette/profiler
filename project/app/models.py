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

    supply_chain_role = models.ForeignKey(
    'SupplyChainRole', on_delete=models.SET_NULL, null=True, blank=True,
    related_name='organizations')

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
    def visiting_card_person(self):
        try:
            vc = self.visiting_card
            return vc.contact_name or self.name
        except Exception:
            return self.name

    @property
    def visiting_card_designation(self):
        try:
            vc = self.visiting_card
            return vc.designation or (self.category.name if self.category else '')
        except Exception:
            return self.category.name if self.category else ''

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
    youtube_url = models.URLField(blank=True, help_text='YouTube demo video URL')
    instagram_url = models.URLField(blank=True, help_text='Instagram post URL')
    pdf_catalog = models.FileField(upload_to='catalogs/', blank=True, null=True, help_text='Downloadable PDF catalog')
    specs_json = models.JSONField(default=dict, blank=True, help_text='Key-value product specifications')
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
            f"Hi!  I'm using Portal to manage my business *{org.name}*. "
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


"""
models_additions.py
===================
Add these new models to your existing models.py.
They extend the current structure to support:
  1. Email-only invitation flow (admin sends invite → user self-onboards)
  2. Supply chain hierarchy (Manufacturer → Distributor → Dealer → Seller → Customer)
  3. Digital visiting card
  4. Payment QR code
  5. WhatsApp enquiry config
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone


# ── 1. INVITATION TOKEN ───────────────────────────────────────────────────────
class InvitationToken(models.Model):
    """
    Created by Super Admin when adding a new member via email only.
    The invited person clicks the link and completes their profile.
    """
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('accepted', 'Accepted'),
        ('expired',  'Expired'),
        ('revoked',  'Revoked'),
    ]


    INVITE_TYPE_CHOICES = [
        ('admin',  'Admin Invite'),
        ('member', 'Member Invite'),
    ]

    # Who sent it and to which email
    invited_by   = models.ForeignKey(
        'CustomUser', on_delete=models.SET_NULL, null=True, related_name='sent_invitations'
    )
    email        = models.EmailField(db_index=True)

    referred_by_org = models.ForeignKey(
        'Organization', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_member_invitations',
        help_text='Set when a member org sends the invite (for bonus tracking).'
    )
    invite_type = models.CharField(
        max_length=10, choices=INVITE_TYPE_CHOICES, default='admin'
    )
    invite_bonus_points = models.PositiveIntegerField(
        default=0,
        help_text='OrgPoints to award to referred_by_org when this invite is accepted.'
    )
    bonus_rewarded = models.BooleanField(
        default=False,
        help_text='True once the referral bonus has been credited.'
    )

    # Pre-assigned plan / category so they land on the right onboarding
    plan         = models.ForeignKey('Plan', on_delete=models.SET_NULL, null=True, blank=True)
    main_category = models.ForeignKey('BusinessCategory', on_delete=models.SET_NULL, null=True, blank=True)
    sub_category  = models.ForeignKey('SubCategory', on_delete=models.SET_NULL, null=True, blank=True)
    subdomain     = models.SlugField(max_length=100, blank=True, null=True,
                                     help_text='Pre-assigned subdomain (optional)')
    site_title    = models.CharField(max_length=200, blank=True)

    # Token
    token  = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Timestamps
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    # The org/user created after acceptance
    organization = models.OneToOneField(
        'Organization', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invitation'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invite → {self.email} [{self.status}]"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return self.status == 'pending' and self.expires_at > timezone.now()

    def get_onboard_url(self, request=None):
        from django.urls import reverse
        path = reverse('onboard_accept', args=[str(self.token)])
        if request:
            return request.build_absolute_uri(path)
        return path


# ── 2. SUPPLY CHAIN ROLE & HIERARCHY ─────────────────────────────────────────
class SupplyChainRole(models.Model):
    """
    Defines a node-type in the supply chain.
    Examples: Manufacturer, Distributor, Dealer, Wholesaler, Retailer,
              Service Provider, Agency, Technician, Freelancer, Customer
    """
    ROLE_TYPE_CHOICES = [
        ('manufacturer',    'Manufacturer'),
        ('distributor',     'Distributor'),
        ('dealer',          'Dealer / Wholesaler'),
        ('retailer',        'Retailer / Reseller'),
        ('service_agency',  'Service Agency'),
        ('technician',      'Technician'),
        ('freelancer',      'Freelancer'),
        ('customer',        'Customer'),
    ]

    name        = models.CharField(max_length=100)
    role_type   = models.CharField(max_length=30, choices=ROLE_TYPE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    icon        = models.CharField(max_length=50, default='diagram-3')
    order       = models.PositiveIntegerField(default=0)
    color       = models.CharField(max_length=7, default='#2563eb')
    is_active   = models.BooleanField(default=True)

    # Which roles can be a parent of this role
    # e.g. Distributor's allowed parents = [Manufacturer]
    allowed_parent_roles = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        related_name='allowed_child_roles',
        help_text='Which roles are allowed as parent of this role'
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class SupplyChainLink(models.Model):
    """
    Connects two Organizations in the supply chain.
    e.g.  parent=Manufacturer  ←→  child=Distributor
          parent=Distributor   ←→  child=Dealer
    """
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('active',   'Active'),
        ('inactive', 'Inactive'),
        ('rejected', 'Rejected'),
    ]

    parent    = models.ForeignKey(
        'Organization', on_delete=models.CASCADE, related_name='supply_chain_children'
    )
    child     = models.ForeignKey(
        'Organization', on_delete=models.CASCADE, related_name='supply_chain_parents'
    )
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    note      = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('parent', 'child')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.parent.name} → {self.child.name} [{self.status}]"


# ── Add to Organization model (as a migration addition) ───────────────────────
# Add these fields to your existing Organization model:
#
#   supply_chain_role = models.ForeignKey(
#       SupplyChainRole, on_delete=models.SET_NULL, null=True, blank=True,
#       related_name='organizations'
#   )
#
# Then run:  python manage.py makemigrations && python manage.py migrate


# ── 3. DIGITAL VISITING CARD ──────────────────────────────────────────────────
class VisitingCard(models.Model):
    """
    A shareable digital business card for an Organization.
    Accessible at /card/<org_slug>/  — renders a mobile-first card page.
    """
    THEME_CHOICES = [
        ('classic',   'Classic'),
        ('modern',    'Modern'),
        ('bold',      'Bold'),
        ('minimal',   'Minimal'),
        ('gradient',  'Gradient'),
    ]

    organization  = models.OneToOneField(
        'Organization', on_delete=models.CASCADE, related_name='visiting_card'
    )
    theme         = models.CharField(max_length=20, choices=THEME_CHOICES, default='modern')

    # Card owner details (may differ from org defaults)
    contact_name  = models.CharField(max_length=100, blank=True)
    designation   = models.CharField(max_length=100, blank=True)
    tagline       = models.CharField(max_length=200, blank=True)
    profile_photo = models.ImageField(upload_to='visiting_cards/', blank=True, null=True)

    # Optional override links
    direct_phone     = models.CharField(max_length=20, blank=True)
    direct_whatsapp  = models.CharField(max_length=20, blank=True)
    direct_email     = models.EmailField(blank=True)

    # Social links (can reuse org ones or override)
    linkedin_url  = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url   = models.URLField(blank=True)
    youtube_url   = models.URLField(blank=True)

    # QR + analytics
    total_views   = models.PositiveIntegerField(default=0)
    total_saves   = models.PositiveIntegerField(default=0)  # .vcf downloads

    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Card — {self.organization.name}"

    def get_vcard_text(self):
        """Generate a .vcf vCard string for download."""
        org  = self.organization
        name = self.contact_name or org.name
        phone = self.direct_phone or org.phone
        email = self.direct_email or org.email

        lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"FN:{name}",
            f"ORG:{org.name}",
        ]
        if self.designation:
            lines.append(f"TITLE:{self.designation}")
        if phone:
            lines.append(f"TEL;TYPE=CELL:{phone}")
        if email:
            lines.append(f"EMAIL:{email}")
        if org.website:
            lines.append(f"URL:{org.website}")
        if org.address_line1:
            addr = f"{org.address_line1}, {org.city}, {org.state} {org.pincode}"
            lines.append(f"ADR;TYPE=WORK:;;{addr};;;;")
        lines.append("END:VCARD")
        return "\n".join(lines)


# ── 4. PAYMENT QR CODE ────────────────────────────────────────────────────────
class PaymentQR(models.Model):
    """
    Stores one or more payment QR codes / UPI IDs for an Organization.
    Displayed on the landing page for quick payments / advance bookings.
    """
    METHOD_CHOICES = [
        ('upi',        'UPI (GPay / PhonePe / Paytm)'),
        ('bank',       'Bank Transfer'),
        ('paypal',     'PayPal'),
        ('stripe',     'Stripe'),
        ('razorpay',   'Razorpay'),
        ('other',      'Other'),
    ]

    organization = models.ForeignKey(
        'Organization', on_delete=models.CASCADE, related_name='payment_qrs'
    )
    label        = models.CharField(max_length=100, default='Pay Now')
    method       = models.CharField(max_length=20, choices=METHOD_CHOICES, default='upi')
    upi_id       = models.CharField(max_length=100, blank=True,
                                    help_text='e.g. business@okicici')
    qr_image     = models.ImageField(upload_to='payment_qr/', blank=True, null=True,
                                     help_text='Upload QR image from your payment app')
    is_primary   = models.BooleanField(default=False)
    is_active    = models.BooleanField(default=True)
    order        = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-is_primary']

    def __str__(self):
        return f"{self.organization.name} — {self.label} ({self.method})"


# ── 5. WHATSAPP ENQUIRY CONFIG ────────────────────────────────────────────────
class WhatsAppConfig(models.Model):
    """
    Controls the WhatsApp enquiry button behaviour on the landing page.
    """
    organization     = models.OneToOneField(
        'Organization', on_delete=models.CASCADE, related_name='whatsapp_config'
    )
    whatsapp_number  = models.CharField(max_length=20,
                                        help_text='With country code, e.g. 919876543210')
    greeting_message = models.TextField(
        default="Hi! I found your business on Portal and I'd like to enquire.",
        help_text='Pre-filled WhatsApp message when customer taps the button'
    )
    show_float_button = models.BooleanField(default=True,
                                            help_text='Floating WhatsApp button on landing page')
    show_in_enquiry_form = models.BooleanField(default=True,
                                               help_text='Show WA button after form submission')
    business_hours_only  = models.BooleanField(default=False,
                                               help_text='Only show button during working hours')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"WA Config — {self.organization.name}"

    def get_wa_url(self, custom_message: str = '') -> str:
        import urllib.parse
        msg = custom_message or self.greeting_message
        return f"https://wa.me/{self.whatsapp_number}?text={urllib.parse.quote(msg)}"


class Cart(models.Model):
    """
    Session-scoped cart — works for anonymous visitors.
    Created lazily when first item is added.
    Linked to an Organization so items can only come from one org at a time.
    """
    STATUS_CHOICES = [
        ('active',    'Active'),
        ('checkout',  'Checked Out'),
        ('abandoned', 'Abandoned'),
    ]
 
    session_key  = models.CharField(max_length=64, db_index=True)
    organization = models.ForeignKey(
        'Organization', on_delete=models.CASCADE, related_name='carts'
    )
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
 
    # Optional: if the visitor later submits an enquiry we link it here
    enquiry = models.OneToOneField(
        'Enquiry', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cart'
    )
 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        ordering = ['-updated_at']
 
    def __str__(self):
        return f"Cart [{self.session_key[:8]}] — {self.organization.name} ({self.item_count} items)"
 
    # ── Computed helpers ──────────────────────────────────────────────────────
 
    @property
    def item_count(self):
        return sum(i.quantity for i in self.items.all())
 
    @property
    def total(self):
        return sum(i.line_total for i in self.items.all())
 
    @property
    def items_list(self):
        return self.items.select_related('product', 'service').all()
 
    def get_whatsapp_summary(self, org_name: str = '') -> str:
        """
        Build a WhatsApp-ready order summary string.
        Used by the "Enquire via WhatsApp" button on checkout.
        """
        import urllib.parse
        lines = [f"Hi! I'd like to enquire about the following from *{org_name or self.organization.name}*:"]
        lines.append("")
        for item in self.items.select_related('product', 'service'):
            label = item.product.name if item.product else (item.service.name if item.service else item.custom_label)
            price = f"₹{item.unit_price}" if item.unit_price else ""
            lines.append(f"• {label} × {item.quantity} {price}")
        lines.append(f"\n*Total: ₹{self.total}*")
        return urllib.parse.quote("\n".join(lines))
 
 
class CartItem(models.Model):
    """
    A line-item in a Cart.
    Can reference a Product OR a Service (or neither for custom entries).
    """
    cart        = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
 
    # One of these should be set, or custom_label for custom items
    product     = models.ForeignKey(
        'Product', on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items'
    )
    service     = models.ForeignKey(
        'Service', on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items'
    )
    custom_label = models.CharField(max_length=200, blank=True)
 
    quantity    = models.PositiveIntegerField(default=1)
    unit_price  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
 
    # Snapshot of item name/price at time of adding (protects against edits)
    name_snapshot  = models.CharField(max_length=200, blank=True)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
 
    note       = models.CharField(max_length=300, blank=True,
                                  help_text='Customer note for this line item')
    added_at   = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['added_at']
        unique_together = [('cart', 'product'), ('cart', 'service')]
 
    def __str__(self):
        return f"{self.display_name} × {self.quantity}"
 
    def save(self, *args, **kwargs):
        # Snapshot name & price on first save
        if not self.name_snapshot:
            if self.product:
                self.name_snapshot  = self.product.name
                self.price_snapshot = self.product.effective_price
                if not self.unit_price:
                    self.unit_price = self.product.effective_price
            elif self.service:
                self.name_snapshot  = self.service.name
                self.price_snapshot = self.service.price
                if not self.unit_price:
                    self.unit_price = self.service.price
            else:
                self.name_snapshot = self.custom_label
        super().save(*args, **kwargs)
 
    @property
    def display_name(self):
        return self.name_snapshot or (
            self.product.name if self.product else
            self.service.name if self.service else
            self.custom_label
        )
 
    @property
    def display_image(self):
        """Return the primary image field for cart display."""
        if self.product and self.product.image:
            return self.product.image
        if self.service and self.service.image:
            return self.service.image
        return None
 
    @property
    def line_total(self):
        if self.unit_price:
            return self.unit_price * self.quantity
        return 0
 
    @property
    def item_type(self):
        if self.product:
            return 'product'
        if self.service:
            return 'service'
        return 'custom'
    

class MemberInviteConfig(models.Model):
    """
    Admin-controlled settings for the member-to-member invite feature.
    Singleton pattern: always use MemberInviteConfig.get_config().
    Editable via Django Admin.
    """
 
    bonus_points_per_invite = models.PositiveIntegerField(
        default=50,
        help_text='OrgPoints awarded to the inviting org when their invitee joins.'
    )
 
    # Per-plan invite caps (how many people each org can invite)
    max_invites_trial    = models.PositiveIntegerField(default=2,   help_text='Trial plan: max invites allowed')
    max_invites_silver   = models.PositiveIntegerField(default=5,   help_text='Silver plan: max invites allowed')
    max_invites_gold     = models.PositiveIntegerField(default=20,  help_text='Gold plan: max invites allowed')
    max_invites_platinum = models.PositiveIntegerField(default=100, help_text='Platinum plan: max invites allowed')
 
    allow_member_invites = models.BooleanField(
        default=True,
        help_text='Master switch — disable to prevent all member-to-member invites.'
    )
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        verbose_name        = 'Member Invite Configuration'
        verbose_name_plural = 'Member Invite Configuration'
 
    def __str__(self):
        return f'MemberInviteConfig (bonus={self.bonus_points_per_invite} pts, active={self.allow_member_invites})'
 
    # ── Singleton helper ──────────────────────────────────────────────────────
    @classmethod
    def get_config(cls):
        """Return the single config row, creating it with defaults if absent."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
 
    # ── Per-org invite limit ──────────────────────────────────────────────────
    def get_limit_for_org(self, org) -> int:
        """Return how many member invites this org is allowed to send."""
        if not org or not org.plan:
            return self.max_invites_trial
        return {
            'trial':    self.max_invites_trial,
            'silver':   self.max_invites_silver,
            'gold':     self.max_invites_gold,
            'platinum': self.max_invites_platinum,
        }.get(org.plan.level, self.max_invites_trial)