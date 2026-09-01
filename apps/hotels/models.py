from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class Destination(models.Model):
    city = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='India')
    image = models.ImageField(upload_to='destinations/', blank=True, null=True)
    tagline = models.CharField(max_length=200, blank=True, null=True)
    is_popular = models.BooleanField(default=True)

    class Meta:
        ordering = ['city']

    def __str__(self):
        return f"{self.city}, {self.country}"


class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon_code = models.CharField(max_length=50, default='ph-check-circle', help_text="Phosphor or FA icon class")

    class Meta:
        verbose_name_plural = 'Amenities'
        ordering = ['name']

    def __str__(self):
        return self.name


class Hotel(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='hotels')
    address = models.TextField()
    star_rating = models.PositiveSmallIntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(5)])
    user_rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5)
    reviews_count = models.PositiveIntegerField(default=120)
    
    hero_image = models.ImageField(upload_to='hotels/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    check_in_time = models.CharField(max_length=20, default='14:00')
    check_out_time = models.CharField(max_length=20, default='11:00')
    
    amenities = models.ManyToManyField(Amenity, blank=True, related_name='hotels')
    free_cancellation = models.BooleanField(default=True)
    breakfast_included_default = models.BooleanField(default=True)
    
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def min_price(self):
        cheapest_room = self.rooms.filter(is_active=True).order_by('base_price_per_night').first()
        return cheapest_room.base_price_per_night if cheapest_room else 0.00

    def __str__(self):
        return f"{self.name} ({self.destination.city})"


class HotelImage(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='hotel_gallery/')
    caption = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"Image for {self.hotel.name}"


class RoomType(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    name = models.CharField(max_length=150, help_text="e.g. Deluxe Room, Executive Suite")
    bed_type = models.CharField(max_length=100, default='1 King Bed or 2 Twin Beds')
    max_adults = models.PositiveIntegerField(default=2)
    max_children = models.PositiveIntegerField(default=1)
    room_size_sqft = models.PositiveIntegerField(default=320)
    
    base_price_per_night = models.DecimalField(max_digits=10, decimal_places=2, default=3500.00)
    tax_pct = models.DecimalField(max_digits=4, decimal_places=2, default=12.00)
    
    free_breakfast = models.BooleanField(default=True)
    free_cancellation = models.BooleanField(default=True)
    cancellation_deadline_hours = models.PositiveIntegerField(default=24)
    
    total_inventory = models.PositiveIntegerField(default=10)
    room_image = models.ImageField(upload_to='rooms/', blank=True, null=True)
    amenities_summary = models.CharField(max_length=255, default='Free High Speed Wi-Fi, Air Conditioning, Smart TV, Tea/Coffee maker')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.hotel.name} - {self.name}"
