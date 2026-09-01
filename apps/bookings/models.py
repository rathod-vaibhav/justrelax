from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid

class BookingType(models.TextChoices):
    FLIGHT = 'FLIGHT', _('Flight')
    HOTEL = 'HOTEL', _('Hotel')
    PACKAGE = 'PACKAGE', _('Holiday Package')

class BookingStatus(models.TextChoices):
    CONFIRMED = 'CONFIRMED', _('Confirmed')
    PENDING = 'PENDING', _('Pending')
    CANCELLED = 'CANCELLED', _('Cancelled')
    REFUNDED = 'REFUNDED', _('Refunded')
    COMPLETED = 'COMPLETED', _('Completed')

class PaymentStatus(models.TextChoices):
    PAID = 'PAID', _('Paid')
    PENDING = 'PENDING', _('Pending')
    FAILED = 'FAILED', _('Failed')
    REFUNDED = 'REFUNDED', _('Refunded')

class MasterBooking(models.Model):
    booking_reference = models.CharField(max_length=30, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    booking_type = models.CharField(max_length=20, choices=BookingType.choices)
    
    booking_status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.CONFIRMED)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PAID)
    
    is_agent_booking = models.BooleanField(default=False)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='agent_client_bookings')
    
    # Financials
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    agent_markup_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Customer Details
    contact_name = models.CharField(max_length=150)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=25)
    special_requests = models.TextField(blank=True, null=True)
    
    # Agent Customization for White-Labeling
    agent_ticket_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            prefix = "JR"
            uid = uuid.uuid4().hex[:7].upper()
            self.booking_reference = f"{prefix}-{uid}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking_reference} ({self.get_booking_type_display()}) - {self.contact_name}"


class FlightBookingItem(models.Model):
    booking = models.OneToOneField(MasterBooking, on_delete=models.CASCADE, related_name='flight_item')
    flight_instance = models.ForeignKey('flights.FlightDailyInstance', on_delete=models.CASCADE, related_name='bookings')
    cabin_class = models.CharField(max_length=20, default='ECONOMY')
    pnr_number = models.CharField(max_length=15, default='JR-PNR-88')
    passengers_count = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Flight Item for {self.booking.booking_reference} ({self.pnr_number})"


class PassengerDetail(models.Model):
    flight_item = models.ForeignKey(FlightBookingItem, on_delete=models.CASCADE, related_name='passengers')
    title = models.CharField(max_length=10, default='Mr')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, default='Male')
    age = models.PositiveIntegerField(default=28)
    seat_number = models.CharField(max_length=10, blank=True, null=True)
    meal_preference = models.CharField(max_length=50, default='Standard Meal')
    ticket_number = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return f"{self.title} {self.first_name} {self.last_name} (Seat: {self.seat_number or 'Unassigned'})"


class HotelBookingItem(models.Model):
    booking = models.OneToOneField(MasterBooking, on_delete=models.CASCADE, related_name='hotel_item')
    hotel = models.ForeignKey('hotels.Hotel', on_delete=models.CASCADE)
    room_type = models.ForeignKey('hotels.RoomType', on_delete=models.CASCADE)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    num_rooms = models.PositiveIntegerField(default=1)
    num_nights = models.PositiveIntegerField(default=1)
    num_guests = models.PositiveIntegerField(default=2)

    def __str__(self):
        return f"Hotel Item for {self.booking.booking_reference} - {self.hotel.name}"


class PackageBookingItem(models.Model):
    booking = models.OneToOneField(MasterBooking, on_delete=models.CASCADE, related_name='package_item')
    package = models.ForeignKey('packages.HolidayPackage', on_delete=models.CASCADE)
    travel_date = models.DateField()
    num_travelers = models.PositiveIntegerField(default=2)

    def __str__(self):
        return f"Package Item for {self.booking.booking_reference} - {self.package.title}"


class PaymentTransaction(models.Model):
    booking = models.ForeignKey(MasterBooking, on_delete=models.CASCADE, related_name='transactions')
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=50, default='UPI / NetBanking')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PAID)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Txn {self.transaction_id} - {self.amount} ({self.status})"
