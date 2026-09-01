from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from decimal import Decimal
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse

from apps.accounts.models import CustomUser, AgentProfile, KycStatus, UserRole
from apps.bookings.models import MasterBooking, BookingStatus, BookingType, PaymentStatus
from apps.flights.models import FlightSchedule, FlightDailyInstance, Airport, Airline
from apps.hotels.models import Hotel, RoomType, Destination, HotelImage
from apps.packages.models import HolidayPackage, PackageCategory, PackageImage
from apps.promotions.models import Coupon, DiscountType, ApplicableService

def admin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin_or_staff:
            messages.error(request, "Access denied. Administrator ERP privileges required.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
@admin_required
def admin_dashboard_view(request):
    total_bookings = MasterBooking.objects.count()
    confirmed_bookings = MasterBooking.objects.filter(booking_status=BookingStatus.CONFIRMED).count()
    
    total_gmv = MasterBooking.objects.filter(booking_status=BookingStatus.CONFIRMED).aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    total_tax_collected = MasterBooking.objects.filter(booking_status=BookingStatus.CONFIRMED).aggregate(t=Sum('tax_amount'))['t'] or Decimal('0.00')

    total_agents = AgentProfile.objects.count()
    pending_kyc = AgentProfile.objects.filter(kyc_status=KycStatus.PENDING).count()
    total_customers = CustomUser.objects.filter(role=UserRole.CUSTOMER).count()

    total_flights = FlightSchedule.objects.count()
    total_hotels = Hotel.objects.count()
    total_packages = HolidayPackage.objects.count()
    total_coupons = Coupon.objects.count()

    flights_count = MasterBooking.objects.filter(booking_type=BookingType.FLIGHT).count()
    hotels_count = MasterBooking.objects.filter(booking_type=BookingType.HOTEL).count()
    packages_count = MasterBooking.objects.filter(booking_type=BookingType.PACKAGE).count()

    recent_bookings = MasterBooking.objects.select_related('user', 'agent').order_by('-created_at')[:10]
    recent_agents = AgentProfile.objects.select_related('user').order_by('-created_at')[:5]

    context = {
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'total_gmv': total_gmv,
        'total_tax_collected': total_tax_collected,
        'total_agents': total_agents,
        'pending_kyc': pending_kyc,
        'total_customers': total_customers,
        'total_flights': total_flights,
        'total_hotels': total_hotels,
        'total_packages': total_packages,
        'total_coupons': total_coupons,
        'flights_count': flights_count,
        'hotels_count': hotels_count,
        'packages_count': packages_count,
        'recent_bookings': recent_bookings,
        'recent_agents': recent_agents,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@login_required
@admin_required
def admin_agents_view(request):
    agents = AgentProfile.objects.select_related('user').order_by('-created_at')
    status_filter = request.GET.get('status')
    q = request.GET.get('q')

    if status_filter:
        agents = agents.filter(kyc_status=status_filter)
    if q:
        agents = agents.filter(Q(agency_name__icontains=q) | Q(user__username__icontains=q) | Q(city__icontains=q))

    if request.method == 'POST':
        action = request.POST.get('action')
        agent_id = request.POST.get('agent_id')
        ag = get_object_or_404(AgentProfile, id=agent_id)
        if action == 'EDIT':
            ag.agency_name = request.POST.get('agency_name', ag.agency_name)
            ag.credit_limit = Decimal(request.POST.get('credit_limit', ag.credit_limit))
            ag.markup_flight_pct = Decimal(request.POST.get('markup_flight_pct', ag.markup_flight_pct))
            ag.markup_hotel_pct = Decimal(request.POST.get('markup_hotel_pct', ag.markup_hotel_pct))
            ag.markup_package_pct = Decimal(request.POST.get('markup_package_pct', ag.markup_package_pct))
            ag.kyc_status = request.POST.get('kyc_status', ag.kyc_status)
            if 'agency_logo' in request.FILES:
                ag.agency_logo = request.FILES['agency_logo']
            ag.save()
            messages.success(request, f"Agent record '{ag.agency_name}' updated successfully.")
            return redirect('admin_agents')

    pending_kyc = AgentProfile.objects.filter(kyc_status=KycStatus.PENDING).count()

    return render(request, 'admin_panel/agents.html', {
        'agents': agents,
        'status_filter': status_filter,
        'q': q,
        'pending_kyc': pending_kyc
    })


@login_required
@admin_required
def admin_agent_action_view(request, agent_id):
    agent_profile = get_object_or_404(AgentProfile, id=agent_id)
    action = request.POST.get('action')

    if action == 'APPROVE':
        agent_profile.kyc_status = KycStatus.APPROVED
        agent_profile.save()
        messages.success(request, f"Agent '{agent_profile.agency_name}' verified and approved.")
    elif action == 'REJECT':
        agent_profile.kyc_status = KycStatus.REJECTED
        agent_profile.kyc_notes = request.POST.get('reason', 'KYC documentation incomplete')
        agent_profile.save()
        messages.warning(request, f"Agent '{agent_profile.agency_name}' KYC rejected.")
    elif action == 'SET_CREDIT':
        try:
            new_credit = Decimal(request.POST.get('credit_limit', '0'))
            agent_profile.credit_limit = new_credit
            agent_profile.save()
            messages.success(request, f"Credit limit for {agent_profile.agency_name} set to ₹{new_credit:.2f}.")
        except Exception:
            messages.error(request, "Invalid credit limit format.")

    return redirect('admin_agents')


@login_required
@admin_required
def admin_users_view(request):
    users = CustomUser.objects.all().order_by('-created_at')
    role_filter = request.GET.get('role')
    q = request.GET.get('q')

    if role_filter:
        users = users.filter(role=role_filter)
    if q:
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(phone_number__icontains=q))

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        u = get_object_or_404(CustomUser, id=user_id)
        if action == 'EDIT':
            u.email = request.POST.get('email', u.email)
            u.phone_number = request.POST.get('phone_number', u.phone_number)
            u.role = request.POST.get('role', u.role)
            u.is_active = request.POST.get('is_active') == 'true'
            if u.role in [UserRole.ADMIN, UserRole.STAFF]:
                u.is_staff = True
            u.save()
            messages.success(request, f"User record '{u.username}' updated.")
        elif action == 'TOGGLE_ACTIVE':
            u.is_active = not u.is_active
            u.save()
            messages.success(request, f"User {u.username} status toggled.")
        return redirect('admin_users')

    return render(request, 'admin_panel/users.html', {
        'users': users,
        'role_filter': role_filter,
        'q': q,
        'roles': UserRole.choices
    })


@login_required
@admin_required
def admin_bookings_view(request):
    bookings_qs = MasterBooking.objects.select_related('user', 'agent').order_by('-created_at')
    
    b_type = request.GET.get('type')
    b_status = request.GET.get('status')
    q = request.GET.get('q')

    if b_type:
        bookings_qs = bookings_qs.filter(booking_type=b_type)
    if b_status:
        bookings_qs = bookings_qs.filter(booking_status=b_status)
    if q:
        bookings_qs = bookings_qs.filter(Q(booking_reference__icontains=q) | Q(contact_name__icontains=q) | Q(contact_email__icontains=q))

    if request.method == 'POST':
        b_id = request.POST.get('booking_id')
        action = request.POST.get('action')
        bk = get_object_or_404(MasterBooking, id=b_id)
        if action == 'EDIT' or request.POST.get('status'):
            new_status = request.POST.get('status', bk.booking_status)
            bk.booking_status = new_status
            if request.POST.get('contact_name'):
                bk.contact_name = request.POST.get('contact_name')
            if request.POST.get('contact_email'):
                bk.contact_email = request.POST.get('contact_email')
            bk.save()
            messages.success(request, f"Booking {bk.booking_reference} updated.")
        return redirect('admin_bookings')

    return render(request, 'admin_panel/bookings.html', {
        'bookings': bookings_qs,
        'b_type': b_type,
        'b_status': b_status,
        'q': q
    })


@login_required
@admin_required
def admin_flights_view(request):
    schedules = FlightSchedule.objects.select_related('airline', 'origin', 'destination').order_by('airline__name')
    airports = Airport.objects.all()
    airlines = Airline.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'EDIT':
            sched_id = request.POST.get('schedule_id')
            sched = get_object_or_404(FlightSchedule, id=sched_id)
            sched.flight_number = request.POST.get('flight_number', sched.flight_number)
            sched.airline_id = request.POST.get('airline_id', sched.airline_id)
            sched.origin_id = request.POST.get('origin_id', sched.origin_id)
            sched.destination_id = request.POST.get('dest_id', sched.destination_id)
            sched.departure_time = request.POST.get('dep_time', sched.departure_time)
            sched.arrival_time = request.POST.get('arr_time', sched.arrival_time)
            sched.duration_minutes = int(request.POST.get('duration_minutes', sched.duration_minutes))
            sched.is_active = request.POST.get('is_active') == 'true'
            sched.save()

            eco_price = Decimal(request.POST.get('economy_price', '4500'))
            FlightDailyInstance.objects.filter(schedule=sched).update(economy_price=eco_price)
            messages.success(request, f"Flight Schedule {sched.flight_number} updated.")
            return redirect('admin_flights')

        # CREATE NEW FLIGHT
        fnum = request.POST.get('flight_number')
        al_id = request.POST.get('airline_id')
        orig_id = request.POST.get('origin_id')
        dest_id = request.POST.get('dest_id')
        dep_time = request.POST.get('dep_time')
        arr_time = request.POST.get('arr_time')
        dur = int(request.POST.get('duration_minutes', 120))
        eco_price = Decimal(request.POST.get('economy_price', 4500))

        sched = FlightSchedule.objects.create(
            flight_number=fnum,
            airline_id=al_id,
            origin_id=orig_id,
            destination_id=dest_id,
            departure_time=dep_time,
            arrival_time=arr_time,
            duration_minutes=dur,
            is_direct=True,
            is_active=True
        )

        today = timezone.now().date()
        for i in range(14):
            t_date = today + timedelta(days=i)
            dep_dt = timezone.make_aware(datetime.combine(t_date, datetime.strptime(dep_time, '%H:%M').time()))
            arr_dt = dep_dt + timedelta(minutes=dur)
            FlightDailyInstance.objects.create(
                schedule=sched,
                departure_datetime=dep_dt,
                arrival_datetime=arr_dt,
                economy_price=eco_price,
                economy_seats_available=120
            )

        messages.success(request, f"Flight Schedule {fnum} and 14 days instances created!")
        return redirect('admin_flights')

    return render(request, 'admin_panel/flights.html', {
        'schedules': schedules,
        'airports': airports,
        'airlines': airlines,
    })


@login_required
@admin_required
def admin_hotels_view(request):
    hotels = Hotel.objects.select_related('destination').prefetch_related('rooms', 'gallery').order_by('name')
    destinations = Destination.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'EDIT':
            hotel_id = request.POST.get('hotel_id')
            hotel = get_object_or_404(Hotel, id=hotel_id)
            hotel.name = request.POST.get('name', hotel.name)
            hotel.destination_id = request.POST.get('destination_id', hotel.destination_id)
            hotel.star_rating = int(request.POST.get('star_rating', hotel.star_rating))
            hotel.address = request.POST.get('address', hotel.address)
            hotel.is_active = request.POST.get('is_active') == 'true'
            
            if 'hero_image' in request.FILES:
                hotel.hero_image = request.FILES['hero_image']

            # Option to set an existing gallery image as cover
            cover_img_id = request.POST.get('set_cover_image_id')
            if cover_img_id and str(cover_img_id).isdigit():
                g_img = HotelImage.objects.filter(id=int(cover_img_id), hotel=hotel).first()
                if g_img:
                    hotel.hero_image = g_img.image

            hotel.save()

            # Multiple Gallery Uploads
            for img_file in request.FILES.getlist('gallery_images'):
                HotelImage.objects.create(hotel=hotel, image=img_file)

            base_price = Decimal(request.POST.get('base_price', '5500'))
            room = hotel.rooms.first()
            if room:
                room.base_price_per_night = base_price
                room.save()

            messages.success(request, f"Hotel property '{hotel.name}' updated successfully!")
            return redirect('admin_hotels')

        # CREATE NEW HOTEL
        name = request.POST.get('name')
        dest_id = request.POST.get('destination_id')
        stars = int(request.POST.get('star_rating', 4))
        address = request.POST.get('address', '')
        desc = request.POST.get('description', '')
        
        hotel = Hotel.objects.create(
            name=name,
            destination_id=dest_id,
            star_rating=stars,
            address=address,
            description=desc,
            is_active=True
        )
        if 'hero_image' in request.FILES:
            hotel.hero_image = request.FILES['hero_image']
            hotel.save()

        # Multiple Gallery Uploads
        for img_file in request.FILES.getlist('gallery_images'):
            HotelImage.objects.create(hotel=hotel, image=img_file)

        # Create default Deluxe Room
        RoomType.objects.create(
            hotel=hotel,
            name="Deluxe King Room",
            base_price_per_night=Decimal(request.POST.get('base_price', '5500.00')),
            max_adults=2,
            total_inventory=10
        )
        messages.success(request, f"Hotel '{name}' added successfully!")
        return redirect('admin_hotels')

    return render(request, 'admin_panel/hotels.html', {
        'hotels': hotels,
        'destinations': destinations,
    })


@login_required
@admin_required
def admin_packages_view(request):
    packages = HolidayPackage.objects.select_related('category').prefetch_related('itinerary_days', 'gallery').order_by('title')
    categories = PackageCategory.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'EDIT':
            pkg_id = request.POST.get('package_id')
            pkg = get_object_or_404(HolidayPackage, id=pkg_id)
            pkg.title = request.POST.get('title', pkg.title)
            pkg.category_id = request.POST.get('category_id', pkg.category_id)
            pkg.destination_city = request.POST.get('destination_city', pkg.destination_city)
            pkg.duration_days = int(request.POST.get('duration_days', pkg.duration_days))
            pkg.duration_nights = int(request.POST.get('duration_nights', pkg.duration_nights))
            pkg.starting_price = Decimal(request.POST.get('starting_price', pkg.starting_price))
            pkg.is_active = request.POST.get('is_active') == 'true'

            if 'hero_image' in request.FILES:
                pkg.hero_image = request.FILES['hero_image']

            cover_img_id = request.POST.get('set_cover_image_id')
            if cover_img_id and str(cover_img_id).isdigit():
                g_img = PackageImage.objects.filter(id=int(cover_img_id), package=pkg).first()
                if g_img:
                    pkg.hero_image = g_img.image

            pkg.save()

            # Multiple Gallery Uploads
            for img_file in request.FILES.getlist('gallery_images'):
                PackageImage.objects.create(package=pkg, image=img_file)

            messages.success(request, f"Tour package '{pkg.title}' updated.")
            return redirect('admin_packages')

        # CREATE NEW PACKAGE
        title = request.POST.get('title')
        cat_id = request.POST.get('category_id')
        dest = request.POST.get('destination_city')
        days = int(request.POST.get('duration_days', 4))
        nights = int(request.POST.get('duration_nights', 3))
        price = Decimal(request.POST.get('starting_price', '18500.00'))

        pkg = HolidayPackage.objects.create(
            title=title,
            category_id=cat_id,
            destination_city=dest,
            duration_days=days,
            duration_nights=nights,
            starting_price=price,
            is_featured=True
        )
        if 'hero_image' in request.FILES:
            pkg.hero_image = request.FILES['hero_image']
            pkg.save()

        for img_file in request.FILES.getlist('gallery_images'):
            PackageImage.objects.create(package=pkg, image=img_file)

        messages.success(request, f"Holiday Package '{title}' created successfully!")
        return redirect('admin_packages')

    return render(request, 'admin_panel/packages.html', {
        'packages': packages,
        'categories': categories,
    })


@login_required
@admin_required
def admin_delete_gallery_image_view(request, img_type, img_id):
    """AJAX handler to delete a single gallery image box from edit modal"""
    if str(img_id).isdigit():
        if img_type == 'hotel':
            img_obj = get_object_or_404(HotelImage, id=int(img_id))
            img_obj.delete()
        elif img_type == 'package':
            img_obj = get_object_or_404(PackageImage, id=int(img_id))
            img_obj.delete()
        return JsonResponse({'status': 'ok', 'message': 'Gallery photo removed successfully.'})
    elif str(img_id) == 'hero':
        master_id = request.GET.get('master_id')
        if master_id and str(master_id).isdigit():
            if img_type == 'hotel':
                hotel = Hotel.objects.filter(id=int(master_id)).first()
                if hotel and hotel.hero_image:
                    hotel.hero_image = None
                    hotel.save()
            elif img_type == 'package':
                pkg = HolidayPackage.objects.filter(id=int(master_id)).first()
                if pkg and pkg.hero_image:
                    pkg.hero_image = None
                    pkg.save()
            return JsonResponse({'status': 'ok', 'message': 'Cover photo removed successfully.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid image ID.'}, status=400)


@login_required
@admin_required
def admin_coupons_view(request):
    coupons = Coupon.objects.all().order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'EDIT':
            cid = request.POST.get('coupon_id')
            cp = get_object_or_404(Coupon, id=cid)
            cp.code = request.POST.get('code', cp.code).strip().upper()
            cp.title = request.POST.get('title', cp.title)
            cp.discount_type = request.POST.get('discount_type', cp.discount_type)
            cp.discount_value = Decimal(request.POST.get('discount_value', cp.discount_value))
            cp.min_spend = Decimal(request.POST.get('min_spend', cp.min_spend))
            cp.max_discount_cap = Decimal(request.POST.get('max_discount_cap', cp.max_discount_cap))
            cp.applicable_to = request.POST.get('applicable_to', cp.applicable_to)
            cp.is_active = request.POST.get('is_active') == 'true'
            cp.save()
            messages.success(request, f"Coupon '{cp.code}' updated successfully.")
            return redirect('admin_coupons')

        # CREATE NEW COUPON
        code = request.POST.get('code', '').strip().upper()
        title = request.POST.get('title')
        dtype = request.POST.get('discount_type', 'FIXED')
        dval = Decimal(request.POST.get('discount_value', '500'))
        min_spend = Decimal(request.POST.get('min_spend', '0'))
        cap = Decimal(request.POST.get('max_discount_cap', '5000'))
        app_to = request.POST.get('applicable_to', 'ALL')
        valid_until = request.POST.get('valid_until')

        Coupon.objects.create(
            code=code,
            title=title,
            discount_type=dtype,
            discount_value=dval,
            min_spend=min_spend,
            max_discount_cap=cap,
            applicable_to=app_to,
            valid_until=valid_until,
            is_active=True
        )
        messages.success(request, f"Coupon code {code} created successfully!")
        return redirect('admin_coupons')

    return render(request, 'admin_panel/coupons.html', {'coupons': coupons})


@login_required
@admin_required
def admin_delete_master_view(request, master_type, item_id):
    if request.method == 'POST':
        if master_type == 'flight':
            obj = get_object_or_404(FlightSchedule, id=item_id)
            name = f"Flight {obj.flight_number}"
            obj.delete()
        elif master_type == 'hotel':
            obj = get_object_or_404(Hotel, id=item_id)
            name = f"Hotel {obj.name}"
            obj.delete()
        elif master_type == 'package':
            obj = get_object_or_404(HolidayPackage, id=item_id)
            name = f"Package {obj.title}"
            obj.delete()
        elif master_type == 'coupon':
            obj = get_object_or_404(Coupon, id=item_id)
            name = f"Coupon {obj.code}"
            obj.delete()
        elif master_type == 'user':
            obj = get_object_or_404(CustomUser, id=item_id)
            name = f"User {obj.username}"
            obj.delete()
        messages.warning(request, f"{name} deleted successfully from master database.")
    
    referrer = request.META.get('HTTP_REFERER')
    return redirect(referrer or 'admin_dashboard')


@login_required
@admin_required
def admin_logs_view(request):
    bookings = MasterBooking.objects.select_related('user', 'agent').order_by('-created_at')[:50]
    return render(request, 'admin_panel/logs.html', {'bookings': bookings})


@login_required
@admin_required
def admin_item_history_view(request, master_type, item_id):
    history_entries = []
    item_title = ""

    if master_type == 'hotel':
        obj = get_object_or_404(Hotel, id=item_id)
        item_title = f"Hotel Property: {obj.name}"
        history_entries.append({
            'timestamp': obj.created_at.strftime("%Y-%m-%d %H:%M"),
            'event': 'RECORD_CREATED',
            'details': f"Hotel Property created in Destination: {obj.destination.city}"
        })
        bks = MasterBooking.objects.filter(booking_type=BookingType.HOTEL).order_by('-created_at')[:10]
        for b in bks:
            history_entries.append({
                'timestamp': b.created_at.strftime("%Y-%m-%d %H:%M"),
                'event': f"BOOKING_{b.booking_status}",
                'details': f"Booking Ref #{b.booking_reference} - {b.contact_name} (₹{b.total_amount})"
            })
    elif master_type == 'package':
        obj = get_object_or_404(HolidayPackage, id=item_id)
        item_title = f"Tour Package: {obj.title}"
        history_entries.append({
            'timestamp': obj.created_at.strftime("%Y-%m-%d %H:%M"),
            'event': 'RECORD_CREATED',
            'details': f"Holiday Package published ({obj.duration_days}D/{obj.duration_nights}N)"
        })
        bks = MasterBooking.objects.filter(booking_type=BookingType.PACKAGE).order_by('-created_at')[:10]
        for b in bks:
            history_entries.append({
                'timestamp': b.created_at.strftime("%Y-%m-%d %H:%M"),
                'event': f"BOOKING_{b.booking_status}",
                'details': f"Booking Ref #{b.booking_reference} - {b.contact_name} (₹{b.total_amount})"
            })
    elif master_type == 'flight':
        obj = get_object_or_404(FlightSchedule, id=item_id)
        item_title = f"Flight Route: {obj.flight_number}"
        history_entries.append({
            'timestamp': timezone.now().strftime("%Y-%m-%d %H:%M"),
            'event': 'SCHEDULE_CREATED',
            'details': f"Route: {obj.origin.code} -> {obj.destination.code} ({obj.airline.name})"
        })
    elif master_type == 'agent':
        obj = get_object_or_404(AgentProfile, id=item_id)
        item_title = f"Agent Agency: {obj.agency_name}"
        history_entries.append({
            'timestamp': obj.created_at.strftime("%Y-%m-%d %H:%M"),
            'event': 'ACCOUNT_REGISTERED',
            'details': f"KYC Status: {obj.kyc_status} | Credit Limit: ₹{obj.credit_limit}"
        })
    elif master_type == 'user':
        obj = get_object_or_404(CustomUser, id=item_id)
        item_title = f"User Account: {obj.username}"
        history_entries.append({
            'timestamp': obj.created_at.strftime("%Y-%m-%d %H:%M"),
            'event': 'USER_REGISTERED',
            'details': f"Role: {obj.role} | Active: {obj.is_active}"
        })

    return JsonResponse({
        'title': item_title,
        'history': history_entries
    })
