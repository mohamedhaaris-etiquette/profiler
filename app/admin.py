"""
admin.py — Portal Platform
Django admin configuration for all models.
Access at /django-admin/
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone

from .models import (
    BusinessCategory, SubCategory, Plan,
    Organization, CustomUser,
    Service, Product, Enquiry,
    GalleryImage, Testimonial,
    ReferralProgram, ReferralCode, Referral, ReferralBonus,
    InvitationToken, SupplyChainRole, SupplyChainLink,
    VisitingCard, PaymentQR, WhatsAppConfig,
    Cart, CartItem, MemberInviteConfig,
    PageView, AnalyticsEvent, HeroSlide, PromoBanner, LandingPageConfig,
    BusinessFeature, MaximiseStep, FAQItem, SuccessStory, DealerLocation,
    TeamRole, StaffAvailability,
)


# ── BUSINESS CATEGORY ────────────────────────────────────────────────────────

class SubCategoryInline(admin.TabularInline):
    model        = SubCategory
    extra        = 2
    fields       = ('name', 'slug', 'icon', 'is_active', 'order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display   = ('name', 'slug', 'icon', 'color_primary')
    prepopulated_fields = {'slug': ('name',)}
    inlines        = [SubCategoryInline]
    search_fields  = ('name',)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'main_category', 'is_active', 'order')
    list_filter   = ('main_category', 'is_active')
    search_fields = ('name',)


# ── PLAN ─────────────────────────────────────────────────────────────────────

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'level', 'price', 'duration_days',
        'max_services', 'max_products', 'max_staff', 'max_invites',
        'max_hero_slides', 'max_promos', 'is_active', 'order',
    )
    list_editable = ('is_active', 'order', 'price')
    ordering     = ('order',)
    prepopulated_fields = {'level': ('name',)}


# ── ORGANISATION ─────────────────────────────────────────────────────────────

class ServiceInline(admin.TabularInline):
    model  = Service
    extra  = 0
    fields = ('name', 'price', 'price_unit', 'is_featured', 'is_active', 'order')


class ProductInline(admin.TabularInline):
    model  = Product
    extra  = 0
    fields = ('name', 'price', 'discount_price', 'in_stock', 'is_active')
    show_change_link = True


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display  = (
        'name', 'subdomain', 'category', 'plan_badge_display',
        'status_badge_display', 'city', 'is_verified', 'is_active', 'created_at',
    )
    list_filter   = ('status', 'plan', 'category', 'is_verified', 'is_active')
    search_fields = ('name', 'email', 'phone', 'subdomain', 'city')
    readonly_fields = ('created_at', 'updated_at', 'slug')
    inlines       = [ServiceInline]
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'subdomain', 'tagline', 'description', 'logo')
        }),
        ('Category & Plan', {
            'fields': ('category', 'sub_category', 'plan', 'plan_start_date', 'plan_end_date', 'status')
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'whatsapp', 'landline', 'website')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'district', 'state', 'pincode')
        }),
        ('Business Details', {
            'fields': ('established_year', 'gst_number', 'working_hours', 'is_open_sunday',
                       'accepts_online_payment', 'home_service_available')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_url', 'linkedin_url', 'twitter_url'),
            'classes': ('collapse',),
        }),
        ('Meta', {
            'fields': ('is_verified', 'is_active', 'file_attachment', 'supply_chain_role',
                       'created_at', 'updated_at')
        }),
    )

    def plan_badge_display(self, obj):
        if not obj.plan:
            return '—'
        colors = {
            'trial': '#6b7280', 'silver': '#64748b',
            'gold': '#d97706', 'platinum': '#7c3aed',
        }
        c = colors.get(obj.plan.level, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            c, obj.plan.name
        )
    plan_badge_display.short_description = 'Plan'

    def status_badge_display(self, obj):
        colors = {
            'active': '#22c55e', 'inactive': '#6b7280',
            'suspended': '#ef4444', 'pending': '#f59e0b',
        }
        c = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            c, obj.status.title()
        )
    status_badge_display.short_description = 'Status'


# ── CUSTOM USER ───────────────────────────────────────────────────────────────

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display  = ('username', 'get_full_name', 'email', 'role', 'team_role', 'organization', 'phone', 'is_active')
    list_filter   = ('role', 'is_active', 'organization')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    fieldsets     = UserAdmin.fieldsets + (
        ('Portal Fields', {
            'fields': ('role', 'organization', 'phone', 'landline',
                       'gender', 'date_of_birth', 'profile_pic', 'team_role')
        }),
    )


@admin.register(TeamRole)
class TeamRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'slug', 'is_active', 'order')
    list_filter = ('is_active', 'organization')
    search_fields = ('name', 'slug', 'organization__name')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(StaffAvailability)
class StaffAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('staff', 'status', 'updated_at')
    list_filter = ('status',)


# ── SERVICE ───────────────────────────────────────────────────────────────────

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display  = ('name', 'organization', 'price', 'price_unit', 'is_featured', 'is_active', 'order')
    list_filter   = ('is_featured', 'is_active', 'organization')
    search_fields = ('name', 'organization__name')


# ── PRODUCT ───────────────────────────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ('name', 'organization', 'price', 'discount_price', 'in_stock', 'is_active', 'created_at')
    list_filter   = ('in_stock', 'is_active', 'condition', 'organization')
    search_fields = ('name', 'sku', 'brand', 'organization__name')
    readonly_fields = ('created_at',)


# ── ENQUIRY ───────────────────────────────────────────────────────────────────

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'organization', 'subject', 'status', 'phone', 'created_at')
    list_filter   = ('status', 'organization')
    search_fields = ('name', 'email', 'phone', 'subject', 'organization__name')
    readonly_fields = ('created_at',)
    list_editable = ('status',)


# ── GALLERY ───────────────────────────────────────────────────────────────────

@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('organization', 'caption', 'order')
    list_filter  = ('organization',)


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'is_active', 'order', 'updated_at')
    list_filter = ('is_active', 'organization')
    search_fields = ('title', 'organization__name')


@admin.register(PromoBanner)
class PromoBannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'is_active', 'starts_at', 'ends_at', 'order')
    list_filter = ('is_active', 'organization')
    search_fields = ('title', 'organization__name')


@admin.register(BusinessFeature)
class BusinessFeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'is_active', 'order')
    list_filter = ('is_active', 'organization')
    search_fields = ('title', 'description', 'organization__name')


@admin.register(MaximiseStep)
class MaximiseStepAdmin(admin.ModelAdmin):
    list_display = ('title', 'organization', 'is_active', 'order')
    list_filter = ('is_active', 'organization')
    search_fields = ('title', 'description', 'organization__name')


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ('question', 'organization', 'is_active', 'order')
    list_filter = ('is_active', 'organization')
    search_fields = ('question', 'answer', 'organization__name')


@admin.register(SuccessStory)
class SuccessStoryAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'title', 'organization', 'is_active', 'order')
    list_filter = ('is_active', 'organization')
    search_fields = ('business_name', 'title', 'story', 'organization__name')


@admin.register(DealerLocation)
class DealerLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'city', 'phone', 'is_active', 'order')
    list_filter = ('is_active', 'organization', 'city')
    search_fields = ('name', 'address', 'city', 'organization__name')


# ── TESTIMONIAL ───────────────────────────────────────────────────────────────

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display  = ('client_name', 'organization', 'rating', 'is_active', 'created_at')
    list_filter   = ('is_active', 'organization', 'rating')
    search_fields = ('client_name', 'organization__name')


# ── REFERRAL SYSTEM ───────────────────────────────────────────────────────────

@admin.register(ReferralProgram)
class ReferralProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_per_referral', 'is_active')
    list_editable = ('is_active',)


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display  = ('organization', 'code', 'total_clicks', 'created_at')
    search_fields = ('code', 'organization__name')
    readonly_fields = ('created_at',)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display  = ('referrer', 'referred', 'status', 'points_awarded', 'created_at')
    list_filter   = ('status',)
    readonly_fields = ('created_at', 'confirmed_at')


@admin.register(ReferralBonus)
class ReferralBonusAdmin(admin.ModelAdmin):
    list_display  = ('organization', 'transaction_type', 'points', 'note', 'created_at')
    list_filter   = ('transaction_type',)
    search_fields = ('organization__name', 'note')


# ── INVITATION TOKEN ──────────────────────────────────────────────────────────

@admin.register(InvitationToken)
class InvitationTokenAdmin(admin.ModelAdmin):
    list_display  = ('recipient', 'delivery_channel', 'invited_by', 'plan', 'status', 'approval_status', 'invite_type', 'expires_at', 'created_at')
    list_filter   = ('status', 'approval_status', 'delivery_channel', 'invite_type', 'plan')
    search_fields = ('email', 'phone')
    readonly_fields = ('token', 'created_at', 'accepted_at')

    @admin.display(description='Recipient')
    def recipient(self, obj):
        return obj.email or (f'+{obj.phone}' if obj.phone else '—')


# ── SUPPLY CHAIN ──────────────────────────────────────────────────────────────

@admin.register(SupplyChainRole)
class SupplyChainRoleAdmin(admin.ModelAdmin):
    list_display  = ('name', 'role_type', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    prepopulated_fields = {'role_type': ('name',)}


@admin.register(SupplyChainLink)
class SupplyChainLinkAdmin(admin.ModelAdmin):
    list_display  = ('parent', 'child', 'status', 'created_at')
    list_filter   = ('status',)
    readonly_fields = ('created_at', 'approved_at')


# ── VISITING CARD ─────────────────────────────────────────────────────────────

@admin.register(VisitingCard)
class VisitingCardAdmin(admin.ModelAdmin):
    list_display  = ('organization', 'theme', 'contact_name', 'total_views', 'total_saves', 'is_active')
    list_filter   = ('theme', 'is_active')
    search_fields = ('organization__name', 'contact_name')


# ── PAYMENT QR ────────────────────────────────────────────────────────────────

@admin.register(PaymentQR)
class PaymentQRAdmin(admin.ModelAdmin):
    list_display  = ('organization', 'label', 'method', 'amount', 'upi_id', 'is_primary', 'is_active')
    list_filter   = ('method', 'is_active')
    search_fields = ('organization__name', 'upi_id')


# ── WHATSAPP CONFIG ───────────────────────────────────────────────────────────

@admin.register(WhatsAppConfig)
class WhatsAppConfigAdmin(admin.ModelAdmin):
    list_display  = ('organization', 'whatsapp_number', 'show_float_button', 'is_active')
    search_fields = ('organization__name', 'whatsapp_number')


# ── CART ──────────────────────────────────────────────────────────────────────

class CartItemInline(admin.TabularInline):
    model  = CartItem
    extra  = 0
    fields = ('product', 'service', 'quantity', 'unit_price', 'name_snapshot')
    readonly_fields = ('name_snapshot', 'added_at')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display   = ('session_key', 'organization', 'status', 'item_count', 'total', 'created_at')
    list_filter    = ('status', 'organization')
    readonly_fields = ('created_at', 'updated_at')
    inlines        = [CartItemInline]


# ── MEMBER INVITE CONFIG ──────────────────────────────────────────────────────

@admin.register(MemberInviteConfig)
class MemberInviteConfigAdmin(admin.ModelAdmin):
    list_display = (
        'bonus_points_per_invite', 'allow_member_invites',
        'max_invites_trial', 'max_invites_silver',
        'max_invites_gold', 'max_invites_platinum',
    )

    def has_add_permission(self, request):
        return not MemberInviteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ── ANALYTICS ────────────────────────────────────────────────────────────────

@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display  = ('organization', 'session_key', 'referrer', 'created_at')
    list_filter   = ('organization',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display  = ('organization', 'event_type', 'object_name', 'session_key', 'created_at')
    list_filter   = ('event_type', 'organization')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(LandingPageConfig)
class LandingPageConfigAdmin(admin.ModelAdmin):
    list_display = ('organization', 'primary_color', 'accent_color', 'updated_at')
    search_fields = ('organization__name',)
    readonly_fields = ('updated_at',)
