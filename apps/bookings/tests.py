from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import UserRole, AgentProfile, KycStatus
from apps.flights.models import Airport, Airline, FlightSchedule, FlightDailyInstance, FlightSeat
from apps.hotels.models import Destination, Hotel, RoomType
from apps.packages.models import PackageCategory, HolidayPackage, PackageItineraryDay
from apps.bookings.models import MasterBooking, BookingStatus, BookingType
from apps.wallet.models import Wallet
from apps.promotions.models import Coupon, DiscountType, ApplicableService

User = get_user_model()

class JustRelaxPlatformTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.customer = User.objects.create_user(
            username='test_cust', password='password123',
            email='cust@test.com', role=UserRole.CUSTOMER, first_name='John', last_name='Doe'
        )
        self.cust_wallet = Wallet.objects.create(user=self.customer, balance=Decimal('50000.00'))

        self.agent_user = User.objects.create_user(
            username='test_agent', password='password123',
            email='agent@test.com', role=UserRole.AGENT, first_name='Agent', last_name='Smith'
        )
        self.agent_profile = AgentProfile.objects.create(
            user=self.agent_user, agency_name='Smith Travels Pvt Ltd',
            kyc_status=KycStatus.APPROVED, markup_flight_pct=Decimal('10.00'),
            markup_hotel_pct=Decimal('10.00'), markup_package_pct=Decimal('10.00')
        )
        self.agent_wallet = Wallet.objects.create(user=self.agent_user, balance=Decimal('100000.00'))

        self.admin_user = User.objects.create_user(
            username='test_admin', password='password123',
            email='admin@test.com', role=UserRole.ADMIN, is_staff=True, is_superuser=True
        )

        # Flights Setup
        self.del_ap = Airport.objects.create(code='DEL', name='Indira Gandhi Intl', city='New Delhi')
        self.bom_ap = Airport.objects.create(code='BOM', name='CSM Intl Airport', city='Mumbai')
        self.airline = Airline.objects.create(code='6E', name='IndiGo')
        
        self.schedule = FlightSchedule.objects.create(
            flight_number='6E-555', airline=self.airline, origin=self.del_ap, destination=self.bom_ap,
            departure_time='08:00', arrival_time='10:15', duration_minutes=135, is_direct=True
        )
        
        dep_dt = timezone.now() + timedelta(days=2)
        self.flight_inst = FlightDailyInstance.objects.create(
            schedule=self.schedule, departure_datetime=dep_dt,
            arrival_datetime=dep_dt + timedelta(minutes=135),
            economy_price=Decimal('5000.00'), economy_seats_available=100
        )
        self.seat = FlightSeat.objects.create(
            flight_instance=self.flight_inst, seat_number='12A',
            is_window=True, seat_fee=Decimal('150.00')
        )

        # Hotels Setup
        self.dest = Destination.objects.create(city='Goa', country='India')
        self.hotel = Hotel.objects.create(name='Goa Beachfront Resort', destination=self.dest, star_rating=5, address='Calangute')
        self.room = RoomType.objects.create(hotel=self.hotel, name='Deluxe Ocean View', base_price_per_night=Decimal('6000.00'), tax_pct=Decimal('12.00'))

        # Packages Setup
        self.cat = PackageCategory.objects.create(name='Honeymoon Special')
        self.package = HolidayPackage.objects.create(
            title='Romantic Goa Getaway', category=self.cat, destination_city='Goa',
            duration_days=4, duration_nights=3, starting_price=Decimal('15000.00'), overview='Sample package'
        )

        # Coupon
        self.coupon = Coupon.objects.create(
            code='SAVE500', title='Save 500', discount_type=DiscountType.FIXED,
            discount_value=Decimal('500.00'), min_spend=Decimal('2000.00'),
            valid_until=timezone.now().date() + timedelta(days=30), is_active=True
        )

    def test_homepage_loads(self):
        res = self.client.get(reverse('home'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Just')
        self.assertContains(res, 'Relax')

    def test_flight_search(self):
        res = self.client.get(reverse('flight_search'), {'origin': 'DEL', 'destination': 'BOM'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '6E-555')

    def test_coupon_api_validation(self):
        res = self.client.get(reverse('validate_coupon_api'), {'code': 'SAVE500', 'amount': '5000', 'service': 'FLIGHT'})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['discount_amount'], 500.0)

    def test_customer_flight_booking_flow(self):
        self.client.login(username='test_cust', password='password123')
        
        post_data = {
            'post_base_total': '5000.00',
            'post_tax_total': '600.00',
            'post_markup_total': '0.00',
            'post_flight_instance_id': str(self.flight_inst.id),
            'post_cabin_class': 'ECONOMY',
            'post_total_pax': '1',
            'contact_name': 'John Doe',
            'contact_email': 'john@example.com',
            'contact_phone': '+91 9876543210',
            'payment_method': 'WALLET',
            'coupon_code': 'SAVE500',
            'pax_title_1': 'Mr',
            'pax_first_1': 'John',
            'pax_last_1': 'Doe',
            'pax_seat_1': '12A'
        }
        res = self.client.post(f"{reverse('checkout')}?type=FLIGHT&instance_id={self.flight_inst.id}", post_data)
        self.assertEqual(res.status_code, 302)
        
        booking = MasterBooking.objects.filter(user=self.customer).first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.booking_status, BookingStatus.CONFIRMED)
        self.assertEqual(booking.discount_amount, Decimal('500.00'))
        self.assertEqual(booking.total_amount, Decimal('5100.00')) # (5000 + 600 - 500)

        # Verify Voucher view renders
        v_res = self.client.get(reverse('booking_voucher', args=[booking.booking_reference]))
        self.assertEqual(v_res.status_code, 200)
        self.assertContains(v_res, booking.booking_reference)

    def test_agent_markup_and_voucher(self):
        self.client.login(username='test_agent', password='password123')
        
        # Verify Agent Dashboard loads
        res = self.client.get(reverse('agent_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Smith Travels Pvt Ltd')

        # Agent books a holiday package for client
        post_data = {
            'post_base_total': '15000.00',
            'post_tax_total': '750.00',
            'post_markup_total': '1500.00', # 10% agent markup
            'post_package_id': str(self.package.id),
            'post_travel_date': (timezone.now().date() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'post_travelers': '1',
            'contact_name': 'Client Sharma',
            'contact_email': 'client@example.com',
            'contact_phone': '+91 9999999999',
            'payment_method': 'WALLET',
        }
        res = self.client.post(f"{reverse('checkout')}?type=PACKAGE&package_id={self.package.id}", post_data)
        self.assertEqual(res.status_code, 302)

        agent_booking = MasterBooking.objects.filter(agent=self.agent_user).first()
        self.assertIsNotNone(agent_booking)
        self.assertTrue(agent_booking.is_agent_booking)
        self.assertEqual(agent_booking.agent_markup_amount, Decimal('1500.00'))

        # Check white-label agency branding on voucher
        v_res = self.client.get(reverse('booking_voucher', args=[agent_booking.booking_reference]))
        self.assertEqual(v_res.status_code, 200)
        self.assertContains(v_res, 'Smith Travels Pvt Ltd')

    def test_admin_dashboard(self):
        self.client.login(username='test_admin', password='password123')
        res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'System Administration')
