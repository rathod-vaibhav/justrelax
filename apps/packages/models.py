from django.db import models
from django.utils.text import slugify

class PackageCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon_code = models.CharField(max_length=50, default='ph-compass')
    banner_image = models.ImageField(upload_to='package_categories/', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Package Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class HolidayPackage(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    category = models.ForeignKey(PackageCategory, on_delete=models.SET_NULL, null=True, related_name='packages')
    
    destination_city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    
    duration_days = models.PositiveIntegerField(default=5)
    duration_nights = models.PositiveIntegerField(default=4)
    
    starting_price = models.DecimalField(max_digits=10, decimal_places=2, default=24999.00)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=29999.00)
    
    hero_image = models.ImageField(upload_to='packages/', blank=True, null=True)
    overview = models.TextField()
    highlights = models.TextField(help_text="Line-separated highlights")
    
    inclusions = models.TextField(default="Accommodation in 4-Star Hotels\nDaily Buffet Breakfast & Dinner\nAirport Pick & Drop in AC Sedan\nSightseeing Tour as per itinerary\n24/7 On-trip Assistance")
    exclusions = models.TextField(default="Airfare / Train fare unless specified\nPersonal expenses & tips\nActivity / Entrance tickets not mentioned\nTravel Insurance")
    
    user_rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.8)
    reviews_count = models.PositiveIntegerField(default=84)
    
    flights_included = models.BooleanField(default=False)
    hotels_included = models.BooleanField(default=True)
    transfers_included = models.BooleanField(default=True)
    meals_included = models.BooleanField(default=True)
    
    is_featured = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def duration_formatted(self):
        return f"{self.duration_nights}N / {self.duration_days}D"

    @property
    def highlights_list(self):
        return [h.strip() for h in self.highlights.split('\n') if h.strip()]

    @property
    def inclusions_list(self):
        return [i.strip() for i in self.inclusions.split('\n') if i.strip()]

    @property
    def exclusions_list(self):
        return [e.strip() for e in self.exclusions.split('\n') if e.strip()]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.title}-{self.destination_city}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.duration_formatted})"


class PackageImage(models.Model):
    package = models.ForeignKey(HolidayPackage, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='package_gallery/')
    caption = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"Gallery image for {self.package.title}"


class PackageItineraryDay(models.Model):
    package = models.ForeignKey(HolidayPackage, on_delete=models.CASCADE, related_name='itinerary_days')
    day_number = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200, help_text="e.g. Arrival in Srinagar & Dal Lake Shikara Ride")
    description = models.TextField()
    stay_info = models.CharField(max_length=200, default='Overnight stay at 4-Star Deluxe Hotel')
    meals_info = models.CharField(max_length=150, default='Dinner Included')
    activity_icon = models.CharField(max_length=50, default='ph-map-pin')

    class Meta:
        ordering = ['day_number']

    def __str__(self):
        return f"{self.package.title} - Day {self.day_number}: {self.title}"
