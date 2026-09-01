from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('confirmation/<str:ref>/', views.booking_confirmation_view, name='booking_confirmation'),
    path('voucher/<str:ref>/', views.booking_voucher_view, name='booking_voucher'),
    path('my-trips/', views.my_bookings_view, name='my_bookings'),
    path('cancel/<str:ref>/', views.cancel_booking_view, name='cancel_booking'),
    path('api/validate-coupon/', views.validate_coupon_api, name='validate_coupon_api'),
]

