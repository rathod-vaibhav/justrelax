from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from apps.accounts.views import home_view

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', home_view, name='home'),
    
    # Portals & Modules
    path('auth/', include('apps.accounts.urls')),
    path('flights/', include('apps.flights.urls')),
    path('hotels/', include('apps.hotels.urls')),
    path('packages/', include('apps.packages.urls')),
    path('bookings/', include('apps.bookings.urls')),
    path('agent/', include('apps.agents.urls')),
    path('admin-panel/', include('apps.dashboard_admin.urls')),

    # Media and Static file serving with browser caching middleware
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
