from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.agent_dashboard_view, name='agent_dashboard'),
    path('markups/', views.agent_markups_view, name='agent_markups'),
    path('wallet/', views.agent_wallet_view, name='agent_wallet'),
    path('kyc/', views.agent_kyc_upload_view, name='agent_kyc_upload'),
]
