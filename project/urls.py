"""
urls.py — Portal Platform
Complete URL configuration for all views.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ── Import all views ──────────────────────────────────────────────────────────
from app import views
from app import views_features
from app import views_member_invite
from app import views_cms

urlpatterns = [

    # ── Django Admin ──────────────────────────────────────────────────────────
    path('django-admin/', admin.site.urls),

    # ── Auth ──────────────────────────────────────────────────────────────────
    path('',                    views.home,                  name='home'),
    path('signup/',             views.signup_view,            name='signup'),
    path('login/',              views.login_view,             name='login'),
    path('logout/',             views.logout_view,            name='logout'),
    path('register-admin/',     views.register_super_admin,  name='register_super_admin'),

    # ── Password Reset (Django built-in) ──────────────────────────────────────
    path('accounts/password_reset/', 
     __import__('django.contrib.auth.views', fromlist=['PasswordResetView']).PasswordResetView.as_view(), 
     name='password_reset'),
path('accounts/password_reset/done/',
     __import__('django.contrib.auth.views', fromlist=['PasswordResetDoneView']).PasswordResetDoneView.as_view(),
     name='password_reset_done'),
path('accounts/reset/<uidb64>/<token>/',
     __import__('django.contrib.auth.views', fromlist=['PasswordResetConfirmView']).PasswordResetConfirmView.as_view(),
     name='password_reset_confirm'),
path('accounts/reset/done/',
     __import__('django.contrib.auth.views', fromlist=['PasswordResetCompleteView']).PasswordResetCompleteView.as_view(),
     name='password_reset_complete'),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('dashboard/',          views.dashboard,             name='dashboard'),

    # ── Single-page CMS ──────────────────────────────────────────────────────
    path('dashboard/page-cms/', views_cms.page_cms, name='page_cms'),
    path('dashboard/page-cms/config/', views_cms.page_config_update, name='page_config_update'),
    path('dashboard/page-cms/hero/add/', views_cms.hero_create, name='hero_create'),
    path('dashboard/page-cms/hero/<int:pk>/edit/', views_cms.hero_edit, name='hero_edit'),
    path('dashboard/page-cms/hero/<int:pk>/delete/', views_cms.hero_delete, name='hero_delete'),
    path('dashboard/page-cms/promo/add/', views_cms.promo_create, name='promo_create'),
    path('dashboard/page-cms/promo/<int:pk>/edit/', views_cms.promo_edit, name='promo_edit'),
    path('dashboard/page-cms/promo/<int:pk>/delete/', views_cms.promo_delete, name='promo_delete'),
    path(
        'dashboard/page-cms/content/<str:kind>/add/',
        views_cms.content_create,
        name='cms_content_create',
    ),
    path(
        'dashboard/page-cms/content/<str:kind>/<int:pk>/edit/',
        views_cms.content_edit,
        name='cms_content_edit',
    ),
    path(
        'dashboard/page-cms/content/<str:kind>/<int:pk>/delete/',
        views_cms.content_delete,
        name='cms_content_delete',
    ),
    path(
        'dashboard/page-cms/footer/',
        views_cms.footer_settings_update,
        name='footer_settings_update',
    ),
    path(
        'dashboard/page-cms/<str:kind>/<int:pk>/update/',
        views_cms.cms_item_update,
        name='cms_item_update',
    ),

    # ── Analytics ─────────────────────────────────────────────────────────────
    path('dashboard/analytics/', views.analytics_dashboard, name='analytics'),

    # ── Services ──────────────────────────────────────────────────────────────
    path('dashboard/services/',                    views.manage_services, name='manage_services'),
    path('dashboard/services/add/',                views.add_service,     name='add_service'),
    path('dashboard/services/<int:pk>/edit/',      views.edit_service,    name='edit_service'),
    path('dashboard/services/<int:pk>/delete/',    views.delete_service,  name='delete_service'),

    # ── Products ──────────────────────────────────────────────────────────────
    path('dashboard/products/',                         views.manage_products,      name='manage_products'),
    path('dashboard/products/add/',                     views.add_product,           name='add_product'),
    path('dashboard/products/<int:pk>/edit/',           views.edit_product,          name='edit_product'),
    path('dashboard/products/<int:pk>/delete/',         views.delete_product,        name='delete_product'),
    path('dashboard/products/<int:pk>/toggle-stock/',   views.toggle_product_stock,  name='toggle_product_stock'),

    # ── Enquiries ─────────────────────────────────────────────────────────────
    path('dashboard/enquiries/',                    views.enquiries_list,         name='enquiries'),
    path('dashboard/enquiries/<int:pk>/status/',    views.update_enquiry_status,  name='update_enquiry_status'),
    path('dashboard/enquiries/<int:pk>/delete/',    views.delete_enquiry,         name='delete_enquiry'),

    # ── Gallery ───────────────────────────────────────────────────────────────
    path('dashboard/gallery/',                          views.manage_gallery,       name='manage_gallery'),
    path('dashboard/gallery/add/',                      views.add_gallery_images,   name='add_gallery_images'),
    path('dashboard/gallery/<int:pk>/delete/',          views.delete_gallery_image, name='delete_gallery_image'),

    # ── Testimonials ──────────────────────────────────────────────────────────
    path('dashboard/testimonials/',                     views.manage_testimonials,  name='manage_testimonials'),
    path('dashboard/testimonials/add/',                 views.add_testimonial,      name='add_testimonial'),
    path('dashboard/testimonials/<int:pk>/edit/',       views.edit_testimonial,     name='edit_testimonial'),
    path('dashboard/testimonials/<int:pk>/delete/',     views.delete_testimonial,   name='delete_testimonial'),

    # ── Staff ─────────────────────────────────────────────────────────────────
    path('dashboard/staff/',                            views.staff_list,           name='staff_list'),
    path('dashboard/staff/<int:pk>/edit/',              views.edit_staff,           name='edit_staff'),
    path('dashboard/staff/<int:pk>/toggle-active/',     views.toggle_staff_active,  name='toggle_staff_active'),
    path('dashboard/staff/<int:pk>/delete/',            views.delete_staff,         name='delete_staff'),
    path('dashboard/staff/<int:user_pk>/availability/', views.toggle_staff_availability, name='toggle_staff_availability'),

    # ── Org Settings ──────────────────────────────────────────────────────────
    path('dashboard/settings/',  views.org_settings,  name='org_settings'),

    # ── Visiting Card ─────────────────────────────────────────────────────────
    path('dashboard/visiting-card/',    views.edit_visiting_card,            name='edit_visiting_card'),
    path('card/<slug:slug>/',           views_features.visiting_card,        name='visiting_card'),
    path('card/<slug:slug>/download/',  views_features.download_vcard,       name='download_vcard'),

    # ── Payment QR ────────────────────────────────────────────────────────────
    path('dashboard/payment-qr/',                       views_features.manage_payment_qr,  name='manage_payment_qr'),
    path('dashboard/payment-qr/add/',                   views_features.add_payment_qr,     name='add_payment_qr'),
    path('dashboard/payment-qr/<int:pk>/edit/',         views.edit_payment_qr,             name='edit_payment_qr'),
    path('dashboard/payment-qr/<int:pk>/delete/',       views_features.delete_payment_qr,  name='delete_payment_qr'),

    # ── WhatsApp Config ───────────────────────────────────────────────────────
    path('dashboard/whatsapp/', views_features.edit_whatsapp_config, name='edit_whatsapp_config'),

    # ── Supply Chain ──────────────────────────────────────────────────────────
    path('dashboard/supply-chain/',                   views_features.supply_chain_view,  name='supply_chain'),
    path('dashboard/supply-chain/link/',              views_features.link_supply_chain,  name='link_supply_chain'),
    path('dashboard/supply-chain/<int:pk>/update/',   views_features.update_chain_link,  name='update_chain_link'),
    path('dashboard/supply-chain/<int:pk>/delete/',   views.delete_chain_link,           name='delete_chain_link'),

    # ── Referral System ───────────────────────────────────────────────────────
    path('dashboard/referrals/',       views.referral_dashboard,  name='referral_dashboard'),
    path('join/<str:ref_code>/',       views.signup_with_ref,     name='signup_with_ref'),

    # ── Admin Member Management ───────────────────────────────────────────────
    path('admin-panel/members/',                views.member_list,       name='member_list'),
    path('admin-panel/members/add/',            views.add_member,        name='add_member'),
    path('admin-panel/members/<int:pk>/edit/',  views.edit_member,       name='edit_member'),
    path('admin-panel/members/<int:pk>/delete/', views.org_soft_delete,  name='org_soft_delete'),
    path('admin-panel/members/bulk-action/',    views.bulk_org_action,   name='bulk_org_action'),

    # ── Admin Invitations ─────────────────────────────────────────────────────
    path('admin-panel/invite/',                       views.invite_member,       name='invite_member'),
    path('admin-panel/invitations/',                  views.invitation_list,     name='invitation_list'),
    path('admin-panel/invitations/<int:pk>/resend/',  views.resend_invitation,   name='resend_invitation'),
    path('admin-panel/invitations/<int:pk>/revoke/',  views.revoke_invitation,   name='revoke_invitation'),
    path('admin-panel/invitations/<int:pk>/delete/',  views.admin_delete_invite, name='admin_delete_invite'),

    # Alias: delete_invitation used in templates
    path('admin-panel/invitations/<int:pk>/remove/',  views.delete_invitation,   name='delete_invitation'),

    # ── Onboarding (Magic Link) ───────────────────────────────────────────────
    path('onboard/<uuid:token>/',       views.onboard_accept,  name='onboard_accept'),
    path('onboard/<uuid:token>/done/',  views.onboard_done,    name='onboard_done'),

    # ── Member-to-Member Invites ──────────────────────────────────────────────
    path('dashboard/invite/',                              views_member_invite.member_send_invite,  name='member_send_invite'),
    path('dashboard/invites/',                             views_member_invite.member_invite_list,  name='member_invite_list'),
    path('dashboard/invites/<int:pk>/resend/',             views_member_invite.member_resend_invite, name='member_resend_invite'),
    path('dashboard/invites/<int:pk>/revoke/',             views_member_invite.member_revoke_invite, name='member_revoke_invite'),
    path('dashboard/invites/<int:pk>/delete/',             views.member_delete_invite,              name='member_delete_invite'),

    # ── AJAX Helpers ─────────────────────────────────────────────────────────
    path('ajax/subcategories/',  views.load_sub_categories,  name='load_sub_categories'),

    # ── Cart ──────────────────────────────────────────────────────────────────
    path('org/<slug:slug>/cart/',                           views.cart_view,     name='cart_view'),
    path('org/<slug:slug>/cart/json/',                      views.cart_json,     name='cart_json'),
    path('org/<slug:slug>/cart/add/',                       views.cart_add,      name='cart_add'),
    path('org/<slug:slug>/cart/<int:item_pk>/update/',      views.cart_update,   name='cart_update'),
    path('org/<slug:slug>/cart/<int:item_pk>/remove/',      views.cart_remove,   name='cart_remove'),
    path('org/<slug:slug>/cart/clear/',                     views.cart_clear,    name='cart_clear'),
    path('org/<slug:slug>/cart/checkout/',                  views.cart_checkout, name='cart_checkout'),

    # ── Public Org Pages ─────────────────────────────────────────────────────
    path('org/<slug:slug>/',                              views.public_landing,         name='public_landing'),
    path('org/<slug:slug>/content.json',                  views_cms.public_content_json, name='public_content_json'),
    path('org/<slug:slug>/product/<int:pk>/',             views.product_detail,         name='public_product_detail'),
    path('org/<slug:slug>/product/<int:pk>/json/',        views.product_detail_json,    name='product_detail_json'),
    path('org/<slug:slug>/product/<int:pk>/catalog/',     views.download_product_catalog, name='download_product_catalog'),

    # ── Discovery ─────────────────────────────────────────────────────────────
    path('discover/',                          views_features.discovery_home,      name='discovery_home'),
    path('discover/<slug:cat_slug>/',          views_features.discovery_category,  name='discovery_category'),


      path('onboard/<uuid:token>/pending/',
         views.onboard_pending_review, name='onboard_pending_review'),
 
    # ── Super Admin — approval management ────────────────────────────────
    path('admin-panel/approvals/',
         views.pending_approvals,  name='pending_approvals'),
    path('admin-panel/approvals/<int:pk>/approve/',
         views.approve_member,     name='approve_member'),
    path('admin-panel/approvals/<int:pk>/reject/',
         views.reject_member,      name='reject_member'),

      path('payment/', views.payment_page, name='payment_page'),
    path('payment/create/', views.paypal_create, name='paypal_create'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('payment/failed/', views.payment_failed, name='payment_failed'),

   path('org/<slug:slug>/payment/', views.payment_page, name='org_payment'),

   path(
    'org/<slug:slug>/whatsapp-click/',
    views.log_whatsapp_click,
    name='log_whatsapp_click',
),

path(
    'dashboard/notifications/mark-read/',
    views.mark_admin_notifications_read,
    name='mark_admin_notifications_read',
),

]

# ── Serve media files in development ─────────────────────────────────────────
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
