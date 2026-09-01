from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class UserRole(models.TextChoices):
    CUSTOMER = 'CUSTOMER', _('Customer')
    AGENT = 'AGENT', _('Travel Agent')
    STAFF = 'STAFF', _('Operations Staff')
    ADMIN = 'ADMIN', _('Super Administrator')

class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CUSTOMER)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_agent(self):
        return self.role == UserRole.AGENT

    @property
    def is_customer(self):
        return self.role == UserRole.CUSTOMER

    @property
    def is_admin_or_staff(self):
        return self.role in [UserRole.ADMIN, UserRole.STAFF] or self.is_superuser or self.is_staff

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class KycStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending Verification')
    APPROVED = 'APPROVED', _('Approved / Active')
    REJECTED = 'REJECTED', _('Rejected')

class AgentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='agent_profile')
    agency_name = models.CharField(max_length=150)
    agency_license_no = models.CharField(max_length=100, blank=True, null=True)
    tax_or_pan = models.CharField(max_length=100, blank=True, null=True)
    gstin = models.CharField(max_length=50, blank=True, null=True)
    agency_phone = models.CharField(max_length=25, blank=True, null=True)
    agency_email = models.EmailField(blank=True, null=True)
    agency_address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='India')
    agency_logo = models.ImageField(upload_to='agent_logos/', blank=True, null=True)

    # KYC & Verification
    kyc_status = models.CharField(max_length=20, choices=KycStatus.choices, default=KycStatus.PENDING)
    kyc_document = models.FileField(upload_to='agent_kyc/', blank=True, null=True)
    kyc_notes = models.TextField(blank=True, null=True)

    # B2B Credit & Markups
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    markup_flight_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Default Flight markup %")
    markup_hotel_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Default Hotel markup %")
    markup_package_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Default Package markup %")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.agency_name} ({self.user.username}) - {self.kyc_status}"
