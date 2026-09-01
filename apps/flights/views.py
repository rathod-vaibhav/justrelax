from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q
from decimal import Decimal
from .models import Airport, Airline, FlightSchedule, FlightDailyInstance, FlightSeat, CabinClass

def flight_search_view(request):
    origin_code = request.GET.get('origin', 'DEL').upper()
    dest_code = request.GET.get('destination', 'BOM').upper()
    depart_str = request.GET.get('depart_date')
    trip_type = request.GET.get('trip_type', 'oneway')
    adults = int(request.GET.get('adults', 1))
    children = int(request.GET.get('children', 0))
    cabin_class = request.GET.get('cabin_class', 'ECONOMY')

    # Selected airline & filters
    selected_airlines = request.GET.getlist('airline')
    stops_filter = request.GET.get('stops')
    max_price = request.GET.get('max_price')
    time_filter = request.GET.get('time_slot') # 'morning', 'afternoon', 'evening', 'night'
    sort_by = request.GET.get('sort', 'cheapest')

    # Parse date
    if depart_str:
        try:
            depart_date = datetime.strptime(depart_str, '%Y-%m-%d').date()
        except ValueError:
            depart_date = timezone.now().date()
    else:
        depart_date = timezone.now().date()

    # Query flight daily instances
    instances_qs = FlightDailyInstance.objects.filter(
        schedule__origin__code=origin_code,
        schedule__destination__code=dest_code,
        departure_datetime__date=depart_date,
        schedule__is_active=True
    ).select_related('schedule', 'schedule__airline', 'schedule__origin', 'schedule__destination')

    # If no flights found on that exact day, fallback to next available dates for UX
    if not instances_qs.exists():
        instances_qs = FlightDailyInstance.objects.filter(
            schedule__origin__code=origin_code,
            schedule__destination__code=dest_code,
            schedule__is_active=True
        ).select_related('schedule', 'schedule__airline', 'schedule__origin', 'schedule__destination')

    # Filters
    if selected_airlines:
        instances_qs = instances_qs.filter(schedule__airline__code__in=selected_airlines)
    
    if stops_filter == 'direct':
        instances_qs = instances_qs.filter(schedule__is_direct=True)
    elif stops_filter == '1stop':
        instances_qs = instances_qs.filter(schedule__stops_count=1)

    if max_price:
        try:
            instances_qs = instances_qs.filter(economy_price__lte=Decimal(max_price))
        except:
            pass

    if time_filter == 'early_morning': # Before 6 AM
        instances_qs = instances_qs.filter(schedule__departure_time__lt=datetime.strptime('06:00', '%H:%M').time())
    elif time_filter == 'morning': # 6 AM to 12 PM
        instances_qs = instances_qs.filter(
            schedule__departure_time__gte=datetime.strptime('06:00', '%H:%M').time(),
            schedule__departure_time__lt=datetime.strptime('12:00', '%H:%M').time()
        )
    elif time_filter == 'afternoon': # 12 PM to 6 PM
        instances_qs = instances_qs.filter(
            schedule__departure_time__gte=datetime.strptime('12:00', '%H:%M').time(),
            schedule__departure_time__lt=datetime.strptime('18:00', '%H:%M').time()
        )
    elif time_filter == 'evening': # After 6 PM
        instances_qs = instances_qs.filter(schedule__departure_time__gte=datetime.strptime('18:00', '%H:%M').time())

    # Sorting
    if sort_by == 'cheapest':
        instances_qs = instances_qs.order_by('economy_price')
    elif sort_by == 'fastest':
        instances_qs = instances_qs.order_by('schedule__duration_minutes')
    elif sort_by == 'earliest':
        instances_qs = instances_qs.order_by('schedule__departure_time')

    # Agent Markup consideration if logged-in agent
    agent_markup_pct = Decimal('0.00')
    if request.user.is_authenticated and getattr(request.user, 'is_agent', False):
        if hasattr(request.user, 'agent_profile'):
            agent_markup_pct = request.user.agent_profile.markup_flight_pct

    # Enrich instances with agent markup price
    flight_results = []
    for inst in instances_qs:
        base = inst.business_price if (cabin_class == 'BUSINESS' and inst.business_price) else inst.economy_price
        markup_val = (base * agent_markup_pct) / Decimal('100.00')
        display_price = base + markup_val
        flight_results.append({
            'instance': inst,
            'base_price': base,
            'markup_val': markup_val,
            'display_price': display_price,
            'is_business': (cabin_class == 'BUSINESS' and inst.business_price is not None)
        })

    airports = Airport.objects.all()
    airlines = Airline.objects.all()
    origin_airport = Airport.objects.filter(code=origin_code).first()
    dest_airport = Airport.objects.filter(code=dest_code).first()

    context = {
        'flights': flight_results,
        'origin_code': origin_code,
        'dest_code': dest_code,
        'origin_airport': origin_airport,
        'dest_airport': dest_airport,
        'depart_date': depart_date.strftime('%Y-%m-%d'),
        'depart_date_obj': depart_date,
        'trip_type': trip_type,
        'adults': adults,
        'children': children,
        'total_passengers': adults + children,
        'cabin_class': cabin_class,
        'airports': airports,
        'airlines': airlines,
        'selected_airlines': selected_airlines,
        'stops_filter': stops_filter,
        'time_filter': time_filter,
        'sort_by': sort_by,
        'agent_markup_pct': agent_markup_pct,
    }
    return render(request, 'customer/flight_search.html', context)


def flight_seat_map_api(request, instance_id):
    instance = get_object_or_404(FlightDailyInstance, id=instance_id)
    seats = instance.seats.all().order_by('row', 'column')
    
    # Group by rows
    rows_data = {}
    for s in seats:
        if s.row not in rows_data:
            rows_data[s.row] = []
        rows_data[s.row].append({
            'seat_number': s.seat_number,
            'column': s.column,
            'cabin_class': s.cabin_class,
            'is_window': s.is_window,
            'is_aisle': s.is_aisle,
            'is_extra_legroom': s.is_extra_legroom,
            'seat_fee': float(s.seat_fee),
            'is_booked': s.is_booked
        })

    return JsonResponse({
        'status': 'success',
        'flight_number': instance.schedule.flight_number,
        'airline': instance.schedule.airline.name,
        'rows': [{'row_number': r, 'seats': seats_list} for r, seats_list in sorted(rows_data.items())]
    })
