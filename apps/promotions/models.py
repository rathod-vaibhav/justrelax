from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class DiscountType(models.TextChoices):
    PERCENTAGE = 'PERCENTAGE', _('Percentage (%)')
    FIXED = 'FIXED', _('Flat Amount (₹)')

class ApplicableService(models.TextChoices):
    ALL = 'ALL', _('All Services')
    FLIGHT = 'FLIGHT', _('Flights Only')
    HOTEL = 'HOTEL', _('Hotels Only')
    PACKAGE = 'PACKAGE', _('Holiday Packages Only')

class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True, db_index=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.FIXED)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount in ₹ or percentage %")
    min_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_discount_cap = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    applicable_to = models.CharField(max_length=20, choices=ApplicableService.choices, default=ApplicableService.ALL)
    valid_until = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_discount(self, total_amount):
        if total_amount < self.min_spend:
            return 0.00
        if self.discount_type == DiscountType.PERCENTAGE:
            disc = (total_amount * self.discount_value) / 100
            return min(disc, self.max_discount_cap)
        else:
            return min(self.discount_value, total_amount)

    def __str__(self):
        return f"{self.code} - {self.title}"


class PromoBanner(models.Model):
    title = models.CharField(max_length=150)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    badge = models.CharField(max_length=50, default='Special Offer')
    image = models.ImageField(upload_to='banners/', blank=True, null=True)
    link_url = models.CharField(max_length=255, default='/')
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class CustomerReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=20, choices=ApplicableService.choices)
    rating = models.PositiveSmallIntegerField(default=5)
    title = models.CharField(max_length=150)
    comment = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} ({self.rating}★) - {self.title}"
