"""
urls.py — Full updated URL configuration
=========================================
Replaces the existing urls.py entirely.

New additions vs original:
  ► Invitation flow:    invite_member, onboard_accept, onboard_done,
                        invitation_list, resend_invitation, revoke_invitation
  ► Visiting card:      visiting_card, download_vcard
  ► Payment QR:         manage_payment_qr, add_payment_qr, delete_payment_qr
  ► WhatsApp config:    edit_whatsapp_config
  ► Supply chain:       supply_chain, link_supply_chain, update_chain_link
  ► Discovery (public): discovery_home, discovery_category
  ► Admin member mgmt:  member_list, edit_member, register_super_admin
"""

from django.contrib import admin
from django.urls import path
from app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Auth ─────────────────────────────────────────────────────────────────
    path('',        views.home,         name='home'),
    path('signup/',  views.signup_view,  name='signup'),
    path('login/',  views.login_view,   name='login'),
    path('logout/', views.logout_view,  name='logout'),

    # ── Invitation + Onboarding flow (replaces open signup) ──────────────────
    path('dashboard/invite/',                   views.invite_member,       name='invite_member'),
    path('dashboard/invitations/',              views.invitation_list,     name='invitation_list'),
    path('dashboard/invitations/<int:pk>/resend/', views.resend_invitation, name='resend_invitation'),
    path('dashboard/invitations/<int:pk>/revoke/', views.revoke_invitation, name='revoke_invitation'),

    # Public onboarding (magic link from email)
    path('onboard/<uuid:token>/',      views.onboard_accept, name='onboard_accept'),
    path('onboard/<uuid:token>/done/', views.onboard_done,   name='onboard_done'),

    # Keep referral-based signup if needed
    path('invite/<str:ref_code>/', views.signup_with_ref, name='signup_with_ref'),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),

    # Services
    path('dashboard/services/',                  views.manage_services, name='manage_services'),
    path('dashboard/services/add/',              views.add_service,     name='add_service'),
    path('dashboard/services/edit/<int:pk>/',    views.edit_service,    name='edit_service'),
    path('dashboard/services/delete/<int:pk>/',  views.delete_service,  name='delete_service'),

    # Products
    path('dashboard/products/',                       views.manage_products,     name='manage_products'),
    path('dashboard/products/add/',                   views.add_product,         name='add_product'),
    path('dashboard/products/edit/<int:pk>/',          views.edit_product,        name='edit_product'),
    path('dashboard/products/delete/<int:pk>/',        views.delete_product,      name='delete_product'),
    path('dashboard/products/toggle-stock/<int:pk>/', views.toggle_product_stock, name='toggle_product_stock'),

    # Enquiries
    path('dashboard/enquiries/',                    views.enquiries_list,        name='enquiries'),
    path('dashboard/enquiries/<int:pk>/update/',    views.update_enquiry_status, name='update_enquiry'),

    # Settings
    path('dashboard/settings/', views.org_settings, name='org_settings'),

    # Visiting Card (dashboard settings)
    path('dashboard/card/edit/', views.edit_visiting_card, name='edit_visiting_card'),

    # Payment QR
    path('dashboard/payment-qr/',                      views.manage_payment_qr, name='manage_payment_qr'),
    path('dashboard/payment-qr/add/',                  views.add_payment_qr,    name='add_payment_qr'),
    path('dashboard/payment-qr/<int:pk>/delete/',      views.delete_payment_qr, name='delete_payment_qr'),

    # WhatsApp config
    path('dashboard/whatsapp/', views.edit_whatsapp_config, name='edit_whatsapp_config'),

    # Supply Chain
    path('dashboard/supply-chain/',                         views.supply_chain_view, name='supply_chain'),
    path('dashboard/supply-chain/link/',                    views.link_supply_chain, name='link_supply_chain'),
    path('dashboard/supply-chain/<int:pk>/status/',         views.update_chain_link, name='update_chain_link'),

    # Referrals
    path('dashboard/referrals/', views.referral_dashboard, name='referral_dashboard'),

    # ── Member-to-member invite + bonus ──────────────────────────────────────
    path('dashboard/my-invites/',                      views.member_send_invite,   name='member_send_invite'),
    path('dashboard/my-invites/list/',                 views.member_invite_list,   name='member_invite_list'),
    path('dashboard/my-invites/<int:pk>/resend/',      views.member_resend_invite, name='member_resend_invite'),
    path('dashboard/my-invites/<int:pk>/revoke/',      views.member_revoke_invite, name='member_revoke_invite'),

    # Super Admin — Member management
    path('dashboard/members/',                 views.member_list,  name='member_list'),
    path('dashboard/members/add/',             views.add_member,   name='add_member'),
    path('dashboard/members/<int:pk>/edit/',   views.edit_member,  name='edit_member'),

    # Super Admin — Register
    path('setup/super-admin/', views.register_super_admin, name='register_super_admin'),

    # ── AJAX ─────────────────────────────────────────────────────────────────
    path('ajax/subcategories/', views.load_sub_categories, name='load_sub_categories'),

    # ── PUBLIC — Discovery (Justdial-style) ───────────────────────────────────
    path('discover/',                    views.discovery_home,     name='discovery_home'),
    path('discover/<slug:cat_slug>/',    views.discovery_category, name='discovery_category'),

    # ── PUBLIC — Organisation pages ───────────────────────────────────────────
    path('org/<slug:slug>/',              views.public_landing,       name='public_landing'),
    path('org/<slug:slug>/product/<int:pk>/',      views.product_detail,        name='public_product_detail'),
    path('org/<slug:slug>/product/<int:pk>/json/', views.product_detail_json,   name='public_product_detail_json'),
    path('org/<slug:slug>/product/<int:pk>/catalog/', views.download_product_catalog, name='download_product_catalog'),

    # ── PUBLIC — Digital Visiting Card ────────────────────────────────────────


    path('card/<slug:slug>/',            views.visiting_card,  name='visiting_card'),
    path('card/<slug:slug>/download.vcf', views.download_vcard, name='download_vcard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)