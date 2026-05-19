"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/services/', views.manage_services, name='manage_services'),
    path('dashboard/services/add/', views.add_service, name='add_service'),
    path('dashboard/services/edit/<int:pk>/', views.edit_service, name='edit_service'),
    path('dashboard/services/delete/<int:pk>/', views.delete_service, name='delete_service'),
    path('dashboard/enquiries/', views.enquiries_list, name='enquiries'),
    path('dashboard/enquiries/<int:pk>/update/', views.update_enquiry_status, name='update_enquiry'),
    path('dashboard/settings/', views.org_settings, name='org_settings'),
    path('org/<slug:slug>/', views.public_landing, name='public_landing'),
]
