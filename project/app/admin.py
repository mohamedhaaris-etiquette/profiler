from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Organization, BusinessCategory, Service, Enquiry, GalleryImage, Testimonial


@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'color_primary']
    prepopulated_fields = {'slug': ('name',)}


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1


class EnquiryInline(admin.TabularInline):
    model = Enquiry
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'city', 'phone', 'is_verified', 'is_active', 'created_at']
    list_filter = ['category', 'city', 'is_verified', 'is_active']
    search_fields = ['name', 'email', 'phone', 'city']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ServiceInline, EnquiryInline]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'slug', 'category', 'logo', 'tagline', 'description')}),
        ('Contact', {'fields': ('email', 'phone', 'whatsapp', 'website')}),
        ('Address', {'fields': ('address_line1', 'address_line2', 'city', 'state', 'pincode')}),
        ('Business Details', {'fields': ('established_year', 'gst_number', 'working_hours', 'is_open_sunday', 'accepts_online_payment', 'home_service_available')}),
        ('Social Media', {'fields': ('facebook_url', 'instagram_url', 'linkedin_url', 'twitter_url')}),
        ('Status', {'fields': ('is_verified', 'is_active', 'created_at', 'updated_at')}),
    )


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'organization']
    list_filter = ['role', 'organization']
    fieldsets = UserAdmin.fieldsets + (
        ('Organization', {'fields': ('organization', 'role', 'phone', 'profile_pic')}),
    )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'price', 'is_featured', 'is_active']
    list_filter = ['organization', 'is_featured', 'is_active']


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'subject', 'status', 'created_at']
    list_filter = ['status', 'organization']
    readonly_fields = ['created_at']


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['client_name', 'organization', 'rating', 'is_active']


admin.site.site_header = 'Portal Administration'
admin.site.site_title = 'Portal'