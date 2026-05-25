"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app import views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Services
    path('dashboard/services/', views.manage_services, name='manage_services'),
    path('dashboard/services/add/', views.add_service, name='add_service'),
    path('dashboard/services/edit/<int:pk>/', views.edit_service, name='edit_service'),
    path('dashboard/services/delete/<int:pk>/', views.delete_service, name='delete_service'),

    # Products
    path('dashboard/products/', views.manage_products, name='manage_products'),
    path('dashboard/products/add/', views.add_product, name='add_product'),
    path('dashboard/products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('dashboard/products/delete/<int:pk>/', views.delete_product, name='delete_product'),
    path('dashboard/products/toggle-stock/<int:pk>/', views.toggle_product_stock, name='toggle_product_stock'),

    # Enquiries
    path('dashboard/enquiries/', views.enquiries_list, name='enquiries'),
    path('dashboard/enquiries/<int:pk>/update/', views.update_enquiry_status, name='update_enquiry'),

    # Settings
    path('dashboard/settings/', views.org_settings, name='org_settings'),

    # Public landing page
    path('org/<slug:slug>/', views.public_landing, name='public_landing'),

    path('dashboard/referrals/', views.referral_dashboard, name='referral_dashboard'),
    path('invite/<str:ref_code>/', views.signup_with_ref, name='signup_with_ref')
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)