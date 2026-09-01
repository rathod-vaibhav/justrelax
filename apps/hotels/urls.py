from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.hotel_search_view, name='hotel_search'),
    path('<int:hotel_id>/', views.hotel_detail_view, name='hotel_detail'),
]

