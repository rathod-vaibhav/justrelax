from django.db import models
from django.utils.translation import gettext_lazy as _

class CabinClass(models.TextChoices):
    ECONOMY = 'ECONOMY', _('Economy')
    PREMIUM_ECONOMY = 'PREMIUM_ECONOMY', _('Premium Economy')
    BUSINESS = 'BUSINESS', _('Business')
    FIRST = 'FIRST', _('First Class')

class Airport(models.Model):
    code = models.CharField(max_length=4, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    city = models.CharField(max_length=100, db_index=True)
    country = models.CharField(max_length=100, default='India')
    terminal_info = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['city', 'code']

    def __str__(self):
        return f"{self.city} ({self.code}) - {self.name}"


class Airline(models.Model):
    code = models.CharField(max_length=4, unique=True)
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='airlines/', blank=True, null=True)
    baggage_policy = models.CharField(max_length=255, default='Cabin: 7kg | Check-in: 15kg')

    def __str__(self):
        return f"{self.name} ({self.code})"


class FlightSchedule(models.Model):
    flight_number = models.CharField(max_length=20, db_index=True)
    airline = models.ForeignKey(Airline, on_delete=models.CASCADE, related_name='schedules')
    origin = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='departures')
    destination = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='arrivals')
    
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(help_text="Flight duration in minutes")
    
    is_direct = models.BooleanField(default=True)
    stops_count = models.PositiveIntegerField(default=0)
    stop_details = models.CharField(max_length=150, blank=True, null=True, help_text="e.g. 1 Stop at BOM (1h 15m)")
    aircraft_type = models.CharField(max_length=100, default='Airbus A320neo')
    operating_days = models.CharField(max_length=20, default='1,2,3,4,5,6,7', help_text="Comma separated days (1=Mon, 7=Sun)")
    is_active = models.BooleanField(default=True)

    @property
    def duration_formatted(self):
        hours = self.duration_minutes // 60
        mins = self.duration_minutes % 60
        return f"{hours}h {mins}m"

    def __str__(self):
        return f"{self.airline.name} {self.flight_number}: {self.origin.code} -> {self.destination.code}"


class FlightDailyInstance(models.Model):
    schedule = models.ForeignKey(FlightSchedule, on_delete=models.CASCADE, related_name='instances')
    departure_datetime = models.DateTimeField(db_index=True)
    arrival_datetime = models.DateTimeField()
    
    economy_price = models.DecimalField(max_digits=10, decimal_places=2, default=4500.00)
    business_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    economy_seats_available = models.PositiveIntegerField(default=120)
    business_seats_available = models.PositiveIntegerField(default=12)
    
    refundable = models.BooleanField(default=True)
    cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=1500.00)
    free_meal = models.BooleanField(default=False)
    
    status = models.CharField(max_length=20, default='ON_TIME')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['departure_datetime', 'economy_price']

    @property
    def duration_formatted(self):
        return self.schedule.duration_formatted

    def __str__(self):
        return f"{self.schedule.flight_number} on {self.departure_datetime.strftime('%d %b %Y')}"


class FlightSeat(models.Model):
    flight_instance = models.ForeignKey(FlightDailyInstance, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=5)
    cabin_class = models.CharField(max_length=20, choices=CabinClass.choices, default=CabinClass.ECONOMY)
    row = models.PositiveIntegerField(default=1)
    column = models.CharField(max_length=1, default='A')
    is_window = models.BooleanField(default=False)
    is_aisle = models.BooleanField(default=False)
    is_extra_legroom = models.BooleanField(default=False)
    seat_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_booked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('flight_instance', 'seat_number')
        ordering = ['row', 'column']

    def __str__(self):
        return f"{self.seat_number} ({self.cabin_class}) - {'Booked' if self.is_booked else 'Available'}"
