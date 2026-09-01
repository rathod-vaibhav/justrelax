from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from .models import (
    MasterBooking, BookingType, BookingStatus, PaymentStatus,
    FlightBookingItem, PassengerDetail, HotelBookingItem, PackageBookingItem, PaymentTransaction
)
from apps.flights.models import FlightDailyInstance, FlightSeat
from apps.hotels.models import Hotel, RoomType
from apps.packages.models import HolidayPackage
from apps.promotions.models import Coupon, ApplicableService
from apps.wallet.models import Wallet, TransactionType

@login_required
def checkout_view(request):
    booking_type = request.GET.get('type') # 'FLIGHT', 'HOTEL', 'PACKAGE'
    user = request.user
    is_agent = getattr(user, 'is_agent', False)
    agent_profile = getattr(user, 'agent_profile', None) if is_agent else None
    
    # Check wallet
    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={'balance': Decimal('0.00')})

    context = {
        'booking_type': booking_type,
        'user': user,
        'is_agent': is_agent,
        'agent_profile': agent_profile,
        'wallet_balance': wallet.balance,
    }

    # 1. FLIGHT CHECKOUT CONTEXT
    if booking_type == 'FLIGHT':
        instance_id = request.GET.get('instance_id')
        flight_instance = get_object_or_404(FlightDailyInstance.objects.select_related('schedule', 'schedule__airline', 'schedule__origin', 'schedule__destination'), id=instance_id)
        cabin_class = request.GET.get('cabin_class', 'ECONOMY')
        adults = int(request.GET.get('adults', 1))
        children = int(request.GET.get('children', 0))
        total_pax = adults + children
        
        base_unit_price = flight_instance.business_price if (cabin_class == 'BUSINESS' and flight_instance.business_price) else flight_instance.economy_price
        base_total = base_unit_price * total_pax
        taxes = (base_total * Decimal('0.12')) # 12% GST + Airport fees
        
        agent_markup = Decimal('0.00')
        if is_agent and agent_profile:
            agent_markup = (base_total * agent_profile.markup_flight_pct) / Decimal('100.00')

        total_payable = base_total + taxes + agent_markup

        context.update({
            'flight_instance': flight_instance,
            'cabin_class': cabin_class,
            'adults': adults,
            'children': children,
            'total_pax': total_pax,
            'base_unit_price': base_unit_price,
            'base_total': base_total,
            'taxes': taxes,
            'agent_markup': agent_markup,
            'total_payable': total_payable,
        })

    # 2. HOTEL CHECKOUT CONTEXT
    elif booking_type == 'HOTEL':
        room_id = request.GET.get('room_id')
        room = get_object_or_404(RoomType.objects.select_related('hotel', 'hotel__destination'), id=room_id)
        checkin_str = request.GET.get('checkin')
        checkout_str = request.GET.get('checkout')
        rooms_count = int(request.GET.get('rooms', 1))
        guests_count = int(request.GET.get('guests', 2))

        try:
            checkin_date = datetime.strptime(checkin_str, '%Y-%m-%d').date()
            checkout_date = datetime.strptime(checkout_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            checkin_date = timezone.now().date() + timedelta(days=1)
            checkout_date = checkin_date + timedelta(days=2)

        nights = max(1, (checkout_date - checkin_date).days)
        base_total = room.base_price_per_night * nights * rooms_count
        taxes = (base_total * room.tax_pct) / Decimal('100.00')

        agent_markup = Decimal('0.00')
        if is_agent and agent_profile:
            agent_markup = (base_total * agent_profile.markup_hotel_pct) / Decimal('100.00')

        total_payable = base_total + taxes + agent_markup

        context.update({
            'room': room,
            'hotel': room.hotel,
            'checkin_date': checkin_date.strftime('%Y-%m-%d'),
            'checkout_date': checkout_date.strftime('%Y-%m-%d'),
            'nights': nights,
            'rooms_count': rooms_count,
            'guests_count': guests_count,
            'base_total': base_total,
            'taxes': taxes,
            'agent_markup': agent_markup,
            'total_payable': total_payable,
        })

    # 3. PACKAGE CHECKOUT CONTEXT
    elif booking_type == 'PACKAGE':
        package_id = request.GET.get('package_id')
        package = get_object_or_404(HolidayPackage, id=package_id)
        travel_date_str = request.GET.get('travel_date')
        travelers = int(request.GET.get('travelers', 2))

        try:
            travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            travel_date = timezone.now().date() + timedelta(days=7)

        base_total = package.starting_price * travelers
        taxes = (base_total * Decimal('0.05')) # 5% GST on packages

        agent_markup = Decimal('0.00')
        if is_agent and agent_profile:
            agent_markup = (base_total * agent_profile.markup_package_pct) / Decimal('100.00')

        total_payable = base_total + taxes + agent_markup

        context.update({
            'package': package,
            'travel_date': travel_date.strftime('%Y-%m-%d'),
            'travelers': travelers,
            'base_total': base_total,
            'taxes': taxes,
            'agent_markup': agent_markup,
            'total_payable': total_payable,
        })

    # PROCESS BOOKING SUBMISSION (POST)
    if request.method == 'POST':
        contact_name = request.POST.get('contact_name')
        contact_email = request.POST.get('contact_email')
        contact_phone = request.POST.get('contact_phone')
        special_requests = request.POST.get('special_requests', '')
        payment_method = request.POST.get('payment_method', 'WALLET') # WALLET, CARD, UPI, AGENT_CREDIT
        coupon_code = request.POST.get('coupon_code', '').strip().upper()
        
        # Recalculate and apply coupon discount
        base_amt = Decimal(request.POST.get('post_base_total', '0'))
        tax_amt = Decimal(request.POST.get('post_tax_total', '0'))
        markup_amt = Decimal(request.POST.get('post_markup_total', '0'))
        gross = base_amt + tax_amt + markup_amt
        
        discount_amt = Decimal('0.00')
        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code, is_active=True, valid_until__gte=timezone.now().date()).first()
            if coupon:
                discount_amt = coupon.calculate_discount(gross)

        final_amount = max(Decimal('0.00'), gross - discount_amt)

        # Payment Validation if Wallet
        if payment_method == 'WALLET':
            if wallet.balance < final_amount:
                messages.error(request, f"Insufficient wallet balance. Needed: ₹{final_amount:.2f}, Available: ₹{wallet.balance:.2f}. Please choose UPI/Card or top-up your wallet.")
                return render(request, 'customer/checkout.html', context)
            # Deduct wallet
            wallet.debit(final_amount, f"Booking payment for {booking_type}", ref="BOOKING_PAY")

        # Create Master Booking
        master_booking = MasterBooking.objects.create(
            user=user,
            booking_type=booking_type,
            booking_status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.PAID,
            is_agent_booking=is_agent,
            agent=user if is_agent else None,
            base_amount=base_amt,
            tax_amount=tax_amt,
            agent_markup_amount=markup_amt,
            discount_amount=discount_amt,
            total_amount=final_amount,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            special_requests=special_requests,
            agent_ticket_notes=f"Thank you for booking with {agent_profile.agency_name}!" if agent_profile else ""
        )

        # Create Payment Transaction Record
        PaymentTransaction.objects.create(
            booking=master_booking,
            transaction_id=f"TXN-{uuid.uuid4().hex[:10].upper()}",
            payment_method=payment_method,
            amount=final_amount,
            status=PaymentStatus.PAID
        )

        # Create specific items
        if booking_type == 'FLIGHT':
            flight_inst_id = request.POST.get('post_flight_instance_id')
            flight_inst = FlightDailyInstance.objects.get(id=flight_inst_id)
            c_class = request.POST.get('post_cabin_class', 'ECONOMY')
            pax_count = int(request.POST.get('post_total_pax', 1))

            flight_booking_item = FlightBookingItem.objects.create(
                booking=master_booking,
                flight_instance=flight_inst,
                cabin_class=c_class,
                pnr_number=f"JR-{uuid.uuid4().hex[:6].upper()}",
                passengers_count=pax_count
            )

            # Reduce flight seat inventory
            if flight_inst.economy_seats_available >= pax_count:
                flight_inst.economy_seats_available -= pax_count
                flight_inst.save()

            # Save Passenger Details
            for i in range(1, pax_count + 1):
                p_title = request.POST.get(f'pax_title_{i}', 'Mr')
                p_first = request.POST.get(f'pax_first_{i}', f'Passenger {i}')
                p_last = request.POST.get(f'pax_last_{i}', 'Traveler')
                p_seat = request.POST.get(f'pax_seat_{i}', '')
                p_meal = request.POST.get(f'pax_meal_{i}', 'Standard Meal')
                p_gender = request.POST.get(f'pax_gender_{i}', 'Male')
                p_age = int(request.POST.get(f'pax_age_{i}', 28))

                PassengerDetail.objects.create(
                    flight_item=flight_booking_item,
                    title=p_title,
                    first_name=p_first,
                    last_name=p_last,
                    gender=p_gender,
                    age=p_age,
                    seat_number=p_seat,
                    meal_preference=p_meal,
                    ticket_number=f"TKT-{uuid.uuid4().hex[:8].upper()}"
                )

        elif booking_type == 'HOTEL':
            room_id = request.POST.get('post_room_id')
            room_obj = RoomType.objects.get(id=room_id)
            checkin_d = datetime.strptime(request.POST.get('post_checkin'), '%Y-%m-%d').date()
            checkout_d = datetime.strptime(request.POST.get('post_checkout'), '%Y-%m-%d').date()
            r_count = int(request.POST.get('post_rooms_count', 1))
            g_count = int(request.POST.get('post_guests_count', 2))
            n_count = int(request.POST.get('post_nights', 1))

            HotelBookingItem.objects.create(
                booking=master_booking,
                hotel=room_obj.hotel,
                room_type=room_obj,
                check_in_date=checkin_d,
                check_out_date=checkout_d,
                num_rooms=r_count,
                num_nights=n_count,
                num_guests=g_count
            )

        elif booking_type == 'PACKAGE':
            pkg_id = request.POST.get('post_package_id')
            pkg_obj = HolidayPackage.objects.get(id=pkg_id)
            t_date = datetime.strptime(request.POST.get('post_travel_date'), '%Y-%m-%d').date()
            travs = int(request.POST.get('post_travelers', 2))

            PackageBookingItem.objects.create(
                booking=master_booking,
                package=pkg_obj,
                travel_date=t_date,
                num_travelers=travs
            )

        messages.success(request, f"Booking #{master_booking.booking_reference} confirmed successfully!")
        return redirect('booking_confirmation', ref=master_booking.booking_reference)

    return render(request, 'customer/checkout.html', context)


@login_required
def booking_confirmation_view(request, ref):
    booking = get_object_or_404(MasterBooking.objects.select_related('user', 'agent'), booking_reference=ref)
    return render(request, 'customer/booking_confirmation.html', {'booking': booking})


@login_required
def booking_voucher_view(request, ref):
    booking = get_object_or_404(MasterBooking.objects.select_related('user', 'agent'), booking_reference=ref)
    agent_profile = None
    if booking.is_agent_booking and booking.agent and hasattr(booking.agent, 'agent_profile'):
        agent_profile = booking.agent.agent_profile

    return render(request, 'vouchers/e_ticket.html', {
        'booking': booking,
        'agent_profile': agent_profile,
    })


@login_required
def my_bookings_view(request):
    user = request.user
    if getattr(user, 'is_agent', False):
        bookings_qs = MasterBooking.objects.filter(agent=user).select_related('user')
    else:
        bookings_qs = MasterBooking.objects.filter(user=user)

    filter_status = request.GET.get('status')
    if filter_status:
        bookings_qs = bookings_qs.filter(booking_status=filter_status)

    context = {
        'bookings': bookings_qs,
        'filter_status': filter_status,
        'is_agent': getattr(user, 'is_agent', False),
    }
    return render(request, 'customer/my_bookings.html', context)


@login_required
def cancel_booking_view(request, ref):
    booking = get_object_or_404(MasterBooking, booking_reference=ref)
    
    # Security check: only the booking owner, booking agent, or admin can cancel
    if booking.user != request.user and booking.agent != request.user and not request.user.is_admin_or_staff:
        messages.error(request, "Unauthorized action.")
        return redirect('my_bookings')

    if booking.booking_status == BookingStatus.CANCELLED:
        messages.warning(request, "This booking is already cancelled.")
        return redirect('my_bookings')

    if request.method == 'POST':
        reason = request.POST.get('cancellation_reason', 'User requested cancellation')
        
        # Calculate refund (e.g. 85% refund, 15% cancellation fee)
        cancellation_fee = (booking.total_amount * Decimal('0.15'))
        refund_amount = max(Decimal('0.00'), booking.total_amount - cancellation_fee)

        booking.booking_status = BookingStatus.CANCELLED
        booking.payment_status = PaymentStatus.REFUNDED
        booking.save()

        # Refund to user or agent wallet
        refund_target_user = booking.agent if booking.is_agent_booking and booking.agent else booking.user
        wallet, _ = Wallet.objects.get_or_create(user=refund_target_user)
        wallet.credit(refund_amount, f"Refund for cancelled booking #{booking.booking_reference} (Less ₹{cancellation_fee:.2f} fee)", ref="REFUND")

        messages.success(request, f"Booking #{booking.booking_reference} has been cancelled. ₹{refund_amount:.2f} refunded to wallet.")
        return redirect('my_bookings')

    return render(request, 'customer/cancel_booking.html', {'booking': booking})


def validate_coupon_api(request):
    code = request.GET.get('code', '').strip().upper()
    amount_str = request.GET.get('amount', '0')
    service_type = request.GET.get('service', 'ALL')

    try:
        amount = Decimal(amount_str)
    except:
        amount = Decimal('0.00')

    coupon = Coupon.objects.filter(code=code, is_active=True, valid_until__gte=timezone.now().date()).first()
    if not coupon:
        return JsonResponse({'valid': False, 'message': 'Invalid or expired coupon code.'})

    if coupon.applicable_to != ApplicableService.ALL and coupon.applicable_to != service_type:
        return JsonResponse({'valid': False, 'message': f'This coupon is only applicable for {coupon.get_applicable_to_display()}.'})

    if amount < coupon.min_spend:
        return JsonResponse({'valid': False, 'message': f'Minimum booking amount of ₹{coupon.min_spend:.2f} required.'})

    discount = coupon.calculate_discount(amount)
    return JsonResponse({
        'valid': True,
        'code': coupon.code,
        'title': coupon.title,
        'discount_amount': float(discount),
        'final_amount': float(max(Decimal('0.00'), amount - discount)),
        'message': f'Promo code applied! You save ₹{discount:.2f}'
    })
