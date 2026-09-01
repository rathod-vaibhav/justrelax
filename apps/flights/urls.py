from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.flight_search_view, name='flight_search'),
    path('api/seat-map/<int:instance_id>/', views.flight_seat_map_api, name='flight_seat_map_api'),
]

