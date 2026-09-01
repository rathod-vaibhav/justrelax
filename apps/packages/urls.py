from django.urls import path
from . import views

urlpatterns = [
    path('', views.packages_list_view, name='packages_list'),
    path('<slug:slug>/', views.package_detail_view, name='package_detail'),
]

