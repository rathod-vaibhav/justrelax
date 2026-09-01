from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Destination, Amenity, Hotel, RoomType

def hotel_search_view(request):
    city_query = request.GET.get('city', 'Goa')
    checkin_str = request.GET.get('checkin')
    checkout_str = request.GET.get('checkout')
    rooms_count = int(request.GET.get('rooms', 1))
    adults_count = int(request.GET.get('adults', 2))
    
    # Filter parameters
    star_ratings = request.GET.getlist('stars')
    selected_amenities = request.GET.getlist('amenity')
    max_price = request.GET.get('max_price')
    sort_by = request.GET.get('sort', 'popular')

    # Dates
    today = timezone.now().date()
    if checkin_str:
        try:
            checkin_date = datetime.strptime(checkin_str, '%Y-%m-%d').date()
        except ValueError:
            checkin_date = today + timedelta(days=1)
    else:
        checkin_date = today + timedelta(days=1)

    if checkout_str:
        try:
            checkout_date = datetime.strptime(checkout_str, '%Y-%m-%d').date()
        except ValueError:
            checkout_date = checkin_date + timedelta(days=2)
    else:
        checkout_date = checkin_date + timedelta(days=2)

    nights = max(1, (checkout_date - checkin_date).days)

    hotels_qs = Hotel.objects.filter(is_active=True).prefetch_related('amenities', 'rooms')
    if city_query:
        hotels_qs = hotels_qs.filter(destination__city__icontains=city_query)

    if star_ratings:
        hotels_qs = hotels_qs.filter(star_rating__in=[int(s) for s in star_ratings])

    if selected_amenities:
        hotels_qs = hotels_qs.filter(amenities__name__in=selected_amenities).distinct()

    # Agent Markup consideration
    agent_markup_pct = Decimal('0.00')
    if request.user.is_authenticated and getattr(request.user, 'is_agent', False):
        if hasattr(request.user, 'agent_profile'):
            agent_markup_pct = request.user.agent_profile.markup_hotel_pct

    hotel_results = []
    for h in hotels_qs:
        min_p = h.min_price
        if max_price and min_p > Decimal(max_price):
            continue
        markup_val = (min_p * agent_markup_pct) / Decimal('100.00')
        display_price = min_p + markup_val
        total_estimate = display_price * nights * rooms_count

        hotel_results.append({
            'hotel': h,
            'min_price': min_p,
            'display_price': display_price,
            'total_estimate': total_estimate,
            'rooms_available': h.rooms.filter(is_active=True),
        })

    # Sort
    if sort_by == 'price_low':
        hotel_results.sort(key=lambda x: x['display_price'])
    elif sort_by == 'price_high':
        hotel_results.sort(key=lambda x: x['display_price'], reverse=True)
    elif sort_by == 'rating':
        hotel_results.sort(key=lambda x: x['hotel'].user_rating, reverse=True)

    destinations = Destination.objects.all()
    all_amenities = Amenity.objects.all()

    context = {
        'hotels': hotel_results,
        'city_query': city_query,
        'checkin_date': checkin_date.strftime('%Y-%m-%d'),
        'checkout_date': checkout_date.strftime('%Y-%m-%d'),
        'nights': nights,
        'rooms_count': rooms_count,
        'adults_count': adults_count,
        'star_ratings': [int(s) for s in star_ratings],
        'selected_amenities': selected_amenities,
        'all_amenities': all_amenities,
        'destinations': destinations,
        'sort_by': sort_by,
        'agent_markup_pct': agent_markup_pct,
    }
    return render(request, 'customer/hotel_search.html', context)


def hotel_detail_view(request, hotel_id):
    hotel = get_object_or_404(Hotel.objects.prefetch_related('amenities', 'rooms', 'gallery'), id=hotel_id)
    
    checkin_str = request.GET.get('checkin')
    checkout_str = request.GET.get('checkout')
    rooms_count = int(request.GET.get('rooms', 1))
    adults_count = int(request.GET.get('adults', 2))
    
    today = timezone.now().date()
    if checkin_str:
        try:
            checkin_date = datetime.strptime(checkin_str, '%Y-%m-%d').date()
        except ValueError:
            checkin_date = today + timedelta(days=1)
    else:
        checkin_date = today + timedelta(days=1)

    if checkout_str:
        try:
            checkout_date = datetime.strptime(checkout_str, '%Y-%m-%d').date()
        except ValueError:
            checkout_date = checkin_date + timedelta(days=2)
    else:
        checkout_date = checkin_date + timedelta(days=2)

    nights = max(1, (checkout_date - checkin_date).days)

    agent_markup_pct = Decimal('0.00')
    if request.user.is_authenticated and getattr(request.user, 'is_agent', False):
        if hasattr(request.user, 'agent_profile'):
            agent_markup_pct = request.user.agent_profile.markup_hotel_pct

    room_items = []
    for r in hotel.rooms.filter(is_active=True):
        markup_val = (r.base_price_per_night * agent_markup_pct) / Decimal('100.00')
        display_price = r.base_price_per_night + markup_val
        total_price = display_price * nights * rooms_count
        tax_est = (total_price * r.tax_pct) / Decimal('100.00')
        grand_total = total_price + tax_est

        room_items.append({
            'room': r,
            'base_price': r.base_price_per_night,
            'display_price': display_price,
            'total_price': total_price,
            'tax_est': tax_est,
            'grand_total': grand_total
        })

    context = {
        'hotel': hotel,
        'room_items': room_items,
        'checkin_date': checkin_date.strftime('%Y-%m-%d'),
        'checkout_date': checkout_date.strftime('%Y-%m-%d'),
        'nights': nights,
        'rooms_count': rooms_count,
        'adults_count': adults_count,
        'agent_markup_pct': agent_markup_pct,
    }
    return render(request, 'customer/hotel_detail.html', context)
