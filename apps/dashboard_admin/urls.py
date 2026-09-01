from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('agents/', views.admin_agents_view, name='admin_agents'),
    path('agents/<int:agent_id>/action/', views.admin_agent_action_view, name='admin_agent_action'),
    path('users/', views.admin_users_view, name='admin_users'),
    path('bookings/', views.admin_bookings_view, name='admin_bookings'),
    path('flights/', views.admin_flights_view, name='admin_flights'),
    path('hotels/', views.admin_hotels_view, name='admin_hotels'),
    path('packages/', views.admin_packages_view, name='admin_packages'),
    path('coupons/', views.admin_coupons_view, name='admin_coupons'),
    path('logs/', views.admin_logs_view, name='admin_logs'),
    path('delete/<str:master_type>/<int:item_id>/', views.admin_delete_master_view, name='admin_delete_master'),
    path('delete-gallery-image/<str:img_type>/<int:img_id>/', views.admin_delete_gallery_image_view, name='admin_delete_gallery_image'),
    path('history/<str:master_type>/<int:item_id>/', views.admin_item_history_view, name='admin_item_history'),
]
