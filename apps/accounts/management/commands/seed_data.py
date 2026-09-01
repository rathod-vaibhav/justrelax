import os
import random
from datetime import datetime, timedelta, time
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.accounts.models import AgentProfile, KycStatus, UserRole
from apps.flights.models import Airport, Airline, FlightSchedule, FlightDailyInstance, FlightSeat, CabinClass
from apps.hotels.models import Destination, Amenity, Hotel, RoomType
from apps.packages.models import PackageCategory, HolidayPackage, PackageItineraryDay
from apps.wallet.models import Wallet, TransactionType
from apps.promotions.models import Coupon, PromoBanner, ApplicableService, DiscountType, CustomerReview

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds realistic MakeMyTrip-style demo data for JustRelax'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Seeding JustRelax Database...'))

        # 1. Users
        # Admin
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@justrelax.com',
                'first_name': 'Super',
                'last_name': 'Admin',
                'role': UserRole.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_verified': True
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()
        Wallet.objects.get_or_create(user=admin_user, defaults={'balance': Decimal('100000.00')})

        # Agent
        agent_user, _ = User.objects.get_or_create(
            username='agent_roy',
            defaults={
                'email': 'roy@roytravels.com',
                'first_name': 'Rajesh',
                'last_name': 'Roy',
                'role': UserRole.AGENT,
                'phone_number': '+91 98765 43210',
                'is_verified': True
            }
        )
        agent_user.set_password('agent123')
        agent_user.save()
        agent_wallet, _ = Wallet.objects.get_or_create(user=agent_user, defaults={'balance': Decimal('75000.00')})
        if agent_wallet.balance < Decimal('75000.00'):
            agent_wallet.balance = Decimal('75000.00')
            agent_wallet.save()

        AgentProfile.objects.get_or_create(
            user=agent_user,
            defaults={
                'agency_name': 'Roy World Travels & Holidays Pvt Ltd',
                'agency_license_no': 'IATA-IND-882910',
                'tax_or_pan': 'AAACR7829K',
                'gstin': '27AAACR7829K1Z5',
                'agency_phone': '+91 22 2847 9900',
                'agency_email': 'bookings@roytravels.com',
                'agency_address': 'Suite 402, Nariman Point, Marine Drive',
                'city': 'Mumbai',
                'country': 'India',
                'kyc_status': KycStatus.APPROVED,
                'credit_limit': Decimal('100000.00'),
                'markup_flight_pct': Decimal('5.00'),
                'markup_hotel_pct': Decimal('8.00'),
                'markup_package_pct': Decimal('10.00')
            }
        )

        # Customer
        customer_user, _ = User.objects.get_or_create(
            username='customer_alex',
            defaults={
                'email': 'alex@example.com',
                'first_name': 'Alex',
                'last_name': 'Sharma',
                'role': UserRole.CUSTOMER,
                'phone_number': '+91 91234 56789',
                'is_verified': True
            }
        )
        customer_user.set_password('pass123')
        customer_user.save()
        cust_wallet, _ = Wallet.objects.get_or_create(user=customer_user, defaults={'balance': Decimal('8500.00')})
        if cust_wallet.balance < Decimal('8500.00'):
            cust_wallet.balance = Decimal('8500.00')
            cust_wallet.save()

        self.stdout.write(self.style.SUCCESS('-> Users & Profiles created.'))

        # 2. Airports
        airports_data = [
            ('DEL', 'Indira Gandhi International Airport', 'New Delhi', 'India', 'T3 (Intl & Dom), T1/T2 (Domestic)'),
            ('BOM', 'Chhatrapati Shivaji Maharaj Intl Airport', 'Mumbai', 'India', 'T2 (Intl & Dom), T1 (Domestic)'),
            ('BLR', 'Kempegowda International Airport', 'Bengaluru', 'India', 'Terminal 1 & Terminal 2'),
            ('GOI', 'Dabolim Airport / MOPA (GOX)', 'Goa', 'India', 'Integrated Terminal'),
            ('DXB', 'Dubai International Airport', 'Dubai', 'United Arab Emirates', 'Terminal 1, 2 & 3 (Emirates)'),
            ('SIN', 'Singapore Changi Airport', 'Singapore', 'Singapore', 'Terminal 1, 2, 3 & Jewel'),
            ('MLE', 'Velana International Airport', 'Male (Maldives)', 'Maldives', 'Main Atoll Terminal'),
            ('BKK', 'Suvarnabhumi Airport', 'Bangkok', 'Thailand', 'Main Concourse'),
            ('HYD', 'Rajiv Gandhi International Airport', 'Hyderabad', 'India', 'Terminal 1'),
            ('CCU', 'Netaji Subhash Chandra Bose Intl Airport', 'Kolkata', 'India', 'Terminal 2'),
        ]
        airports_dict = {}
        for code, name, city, country, term in airports_data:
            ap, _ = Airport.objects.get_or_create(
                code=code,
                defaults={'name': name, 'city': city, 'country': country, 'terminal_info': term}
            )
            airports_dict[code] = ap

        # 3. Airlines
        airlines_data = [
            ('6E', 'IndiGo Airlines', 'Cabin: 7kg | Check-in: 15kg'),
            ('AI', 'Air India', 'Cabin: 7kg | Check-in: 25kg (Complimentary hot meals)'),
            ('UK', 'Vistara Airlines', 'Cabin: 7kg | Check-in: 15kg (Complimentary gourmet meals)'),
            ('EK', 'Emirates', 'Cabin: 7kg | Check-in: 30kg (World class in-flight entertainment)'),
            ('SQ', 'Singapore Airlines', 'Cabin: 7kg | Check-in: 30kg (KrisFlyer gourmet dining)'),
            ('QP', 'Akasa Air', 'Cabin: 7kg | Check-in: 15kg (Modern Boeing 737 MAX fleet)'),
        ]
        airlines_dict = {}
        for code, name, baggage in airlines_data:
            al, _ = Airline.objects.get_or_create(
                code=code,
                defaults={'name': name, 'baggage_policy': baggage}
            )
            airlines_dict[code] = al

        # 4. Flight Schedules & Instances
        routes = [
            # DEL -> BOM
            ('6E-2041', '6E', 'DEL', 'BOM', time(6, 15), time(8, 30), 135, True, 0, '', 'Airbus A320neo', Decimal('4299.00'), Decimal('12500.00')),
            ('AI-865', 'AI', 'DEL', 'BOM', time(10, 0), time(12, 15), 135, True, 0, '', 'Boeing 787 Dreamliner', Decimal('4899.00'), Decimal('15999.00')),
            ('UK-975', 'UK', 'DEL', 'BOM', time(17, 45), time(20, 0), 135, True, 0, '', 'Airbus A321neo', Decimal('5400.00'), Decimal('16500.00')),
            ('6E-512', '6E', 'DEL', 'BOM', time(21, 30), time(23, 45), 135, True, 0, '', 'Airbus A320', Decimal('3899.00'), None),

            # BOM -> DEL
            ('6E-2042', '6E', 'BOM', 'DEL', time(7, 0), time(9, 15), 135, True, 0, '', 'Airbus A320neo', Decimal('4350.00'), Decimal('12900.00')),
            ('UK-992', 'UK', 'BOM', 'DEL', time(14, 30), time(16, 45), 135, True, 0, '', 'Airbus A321neo', Decimal('5200.00'), Decimal('15800.00')),
            ('AI-678', 'AI', 'BOM', 'DEL', time(19, 0), time(21, 15), 135, True, 0, '', 'Boeing 777-300ER', Decimal('4750.00'), Decimal('14999.00')),

            # DEL -> BLR
            ('6E-2134', '6E', 'DEL', 'BLR', time(8, 20), time(11, 10), 170, True, 0, '', 'Airbus A321neo', Decimal('5299.00'), Decimal('14500.00')),
            ('AI-506', 'AI', 'DEL', 'BLR', time(15, 10), time(18, 0), 170, True, 0, '', 'Airbus A320neo', Decimal('5600.00'), Decimal('16000.00')),

            # BOM -> GOI
            ('6E-451', '6E', 'BOM', 'GOI', time(11, 30), time(12, 45), 75, True, 0, '', 'Airbus A320neo', Decimal('2999.00'), None),
            ('QP-1321', 'QP', 'BOM', 'GOI', time(16, 20), time(17, 35), 75, True, 0, '', 'Boeing 737 MAX', Decimal('2750.00'), None),

            # DEL -> DXB (International)
            ('EK-511', 'EK', 'DEL', 'DXB', time(11, 0), time(13, 25), 235, True, 0, '', 'Boeing 777-300ER', Decimal('18999.00'), Decimal('48999.00')),
            ('AI-995', 'AI', 'DEL', 'DXB', time(20, 15), time(22, 45), 240, True, 0, '', 'Airbus A321LR', Decimal('14500.00'), Decimal('36000.00')),

            # BOM -> MLE (Maldives)
            ('6E-1785', '6E', 'BOM', 'MLE', time(9, 45), time(12, 30), 165, True, 0, '', 'Airbus A320neo', Decimal('11999.00'), None),
            ('AI-267', 'AI', 'BOM', 'MLE', time(13, 0), time(15, 50), 170, True, 0, '', 'Airbus A320neo', Decimal('13500.00'), Decimal('29000.00')),

            # DEL -> SIN (Singapore)
            ('SQ-401', 'SQ', 'DEL', 'SIN', time(9, 55), time(18, 10), 345, True, 0, '', 'Airbus A350-900', Decimal('22500.00'), Decimal('64000.00')),
        ]

        now_date = timezone.now().date()
        for fnum, al_code, orig, dest, dep_t, arr_t, dur, is_dir, stp_cnt, stp_det, ac_type, eco_p, bus_p in routes:
            sched, _ = FlightSchedule.objects.get_or_create(
                flight_number=fnum,
                defaults={
                    'airline': airlines_dict[al_code],
                    'origin': airports_dict[orig],
                    'destination': airports_dict[dest],
                    'departure_time': dep_t,
                    'arrival_time': arr_t,
                    'duration_minutes': dur,
                    'is_direct': is_dir,
                    'stops_count': stp_cnt,
                    'stop_details': stp_det,
                    'aircraft_type': ac_type,
                    'is_active': True
                }
            )

            # Generate flight instances for the next 30 days
            for d in range(0, 30):
                target_date = now_date + timedelta(days=d)
                dep_dt = datetime.combine(target_date, dep_t)
                arr_dt = dep_dt + timedelta(minutes=dur)
                if timezone.is_naive(dep_dt):
                    dep_dt = timezone.make_aware(dep_dt)
                    arr_dt = timezone.make_aware(arr_dt)

                inst, created = FlightDailyInstance.objects.get_or_create(
                    schedule=sched,
                    departure_datetime=dep_dt,
                    defaults={
                        'arrival_datetime': arr_dt,
                        'economy_price': eco_p + Decimal(random.randint(0, 300)),
                        'business_price': bus_p,
                        'economy_seats_available': random.randint(35, 140),
                        'business_seats_available': 10 if bus_p else 0,
                        'refundable': True,
                        'cancellation_fee': Decimal('1500.00'),
                        'free_meal': (al_code in ['AI', 'UK', 'EK', 'SQ'])
                    }
                )

                # Generate seats for the first 3 days for demo seat selector
                if d < 3 and created:
                    for row in range(1, 15):
                        for col in ['A', 'B', 'C', 'D', 'E', 'F']:
                            seat_no = f"{row}{col}"
                            is_win = col in ['A', 'F']
                            is_aisle = col in ['C', 'D']
                            is_legroom = row in [1, 11]
                            fee = Decimal('350.00') if is_legroom else (Decimal('150.00') if is_win else Decimal('0.00'))
                            is_bk = random.random() < 0.25
                            FlightSeat.objects.create(
                                flight_instance=inst,
                                seat_number=seat_no,
                                row=row,
                                column=col,
                                cabin_class=CabinClass.BUSINESS if row <= 2 and bus_p else CabinClass.ECONOMY,
                                is_window=is_win,
                                is_aisle=is_aisle,
                                is_extra_legroom=is_legroom,
                                seat_fee=fee,
                                is_booked=is_bk
                            )

        self.stdout.write(self.style.SUCCESS('-> Flights, Schedules, and Seat Maps created.'))

        # 5. Amenities
        amenities_data = [
            ('Free High-Speed Wi-Fi', 'ph-wifi-high'),
            ('Swimming Pool', 'ph-swimming-pool'),
            ('Complimentary Breakfast', 'ph-fork-knife'),
            ('Spa & Wellness Center', 'ph-flower-lotus'),
            ('Fitness Center / Gym', 'ph-barbell'),
            ('Airport Shuttle / Transfers', 'ph-car'),
            ('24/7 Room Service', 'ph-bell-ringing'),
            ('Beachfront / Sea View', 'ph-waves'),
            ('Bar & Lounge', 'ph-wine'),
            ('Kids Play Zone', 'ph-smiley'),
        ]
        amenities_objs = []
        for a_name, a_icon in amenities_data:
            am, _ = Amenity.objects.get_or_create(name=a_name, defaults={'icon_code': a_icon})
            amenities_objs.append(am)

        # 6. Destinations
        dest_data = [
            ('Goa', 'Goa', 'India', 'Sun, Sand, Shacks & Portuguese heritage beaches'),
            ('Mumbai', 'Maharashtra', 'India', 'The Financial Capital with iconic seafront & nightlife'),
            ('New Delhi', 'Delhi NCR', 'India', 'Historic monuments, culinary delights & luxury shopping'),
            ('Srinagar & Gulmarg', 'Kashmir', 'India', 'Paradise on Earth with snow peaks, Shikaras & pine valleys'),
            ('Munnar & Alleppey', 'Kerala', 'India', "God's Own Country with lush tea gardens & tranquil backwaters"),
            ('Dubai', 'Dubai', 'United Arab Emirates', 'Futuristic skyline, Burj Khalifa & luxury desert safaris'),
            ('Bali', 'Bali', 'Indonesia', 'Tropical beaches, ancient temples & serene jungle villas'),
            ('Udaipur & Jaipur', 'Rajasthan', 'India', 'Land of Maharajas with royal palaces & vibrant bazaars'),
        ]
        dest_dict = {}
        for city, state, country, tag in dest_data:
            d_obj, _ = Destination.objects.get_or_create(
                city=city,
                defaults={'state': state, 'country': country, 'tagline': tag, 'is_popular': True}
            )
            dest_dict[city] = d_obj

        # 7. Hotels & Rooms
        hotels_seed = [
            {
                'name': 'The Taj Mahal Palace & Tower',
                'dest': 'Mumbai',
                'address': 'Apollo Bunder, Colaba, Mumbai 400001',
                'star': 5,
                'user_rating': Decimal('4.9'),
                'reviews_count': 1420,
                'desc': 'An architectural landmark facing the Gateway of India, offering royal hospitality, bespoke dining, and opulent heritage suites.',
                'featured': True,
                'rooms': [
                    ('Tower Superior City View', '1 King Bed', 2, 1, 350, Decimal('16500.00'), True, True),
                    ('Palace Luxury Sea View', '1 Heritage King Bed', 2, 1, 480, Decimal('28000.00'), True, True),
                    ('Signature Heritage Suite', '1 Grand King + Living Room', 3, 2, 750, Decimal('55000.00'), True, True),
                ]
            },
            {
                'name': 'Grand Hyatt Goa Resort & Spa',
                'dest': 'Goa',
                'address': 'Bambolim Bay, Goa 403201',
                'star': 5,
                'user_rating': Decimal('4.8'),
                'reviews_count': 980,
                'desc': 'Set along the calm waters of Bambolim Bay, featuring 28 acres of tropical landscaped gardens, lagoon pools, and authentic Goan seafood.',
                'featured': True,
                'rooms': [
                    ('Standard Garden View Room', '1 King or Twin Beds', 2, 1, 380, Decimal('9500.00'), True, True),
                    ('Club Sea View with Balcony', '1 King Bed', 2, 1, 440, Decimal('14500.00'), True, True),
                    ('Grand Suite with Private Jacuzzi', '1 Royal King Bed', 3, 2, 820, Decimal('32000.00'), True, True),
                ]
            },
            {
                'name': 'The Khyber Himalayan Resort & Spa',
                'dest': 'Srinagar & Gulmarg',
                'address': 'Near Gondola Base, Gulmarg, Kashmir 193403',
                'star': 5,
                'user_rating': Decimal('4.9'),
                'reviews_count': 640,
                'desc': 'Located 8,825 feet above sea level in the Pir Panjal range, offering breathtaking snow-covered pine vistas, heated indoor pool, and world-class ski access.',
                'featured': True,
                'rooms': [
                    ('Premier Pine View Room', '1 King Bed', 2, 1, 410, Decimal('18500.00'), True, True),
                    ('Luxury Gulmarg Mountain View', '1 King Bed', 2, 1, 460, Decimal('24000.00'), True, True),
                    ('Presidential Himalayan Cottage', '2 Bedroom Chalet', 5, 2, 1100, Decimal('68000.00'), True, True),
                ]
            },
            {
                'name': 'Kumarakom Lake Resort',
                'dest': 'Munnar & Alleppey',
                'address': 'Kumarakom North Post, Kottayam, Kerala 686563',
                'star': 5,
                'user_rating': Decimal('4.8'),
                'reviews_count': 810,
                'desc': 'Acclaimed luxury heritage retreat nestled along the serene banks of Lake Vembanad, featuring traditional Keralite courtyard villas and private plunge pools.',
                'featured': True,
                'rooms': [
                    ('Heritage Courtyard Villa', '1 Teakwood King Bed', 2, 1, 420, Decimal('13500.00'), True, True),
                    ('Meandering Pool Villa', 'Direct Pool Access King Bed', 2, 1, 490, Decimal('19500.00'), True, True),
                    ('Luxury Houseboat Suite (Cruising)', '1 Air-Conditioned Bedroom', 2, 1, 550, Decimal('26000.00'), True, True),
                ]
            },
            {
                'name': 'Atlantis, The Palm Dubai',
                'dest': 'Dubai',
                'address': 'Crescent Road, Palm Jumeirah, Dubai',
                'star': 5,
                'user_rating': Decimal('4.9'),
                'reviews_count': 3200,
                'desc': 'Iconic ocean-themed destination resort situated on the crest of the Palm Island with Aquaventure Waterpark, underwater aquarium, and celebrity chef restaurants.',
                'featured': True,
                'rooms': [
                    ('Ocean King Room', '1 King Bed with Arabian Sea View', 2, 1, 475, Decimal('34000.00'), True, True),
                    ('Imperial Club Suite', '1 King Bed + Lounge Access', 3, 2, 720, Decimal('58000.00'), True, True),
                    ('Underwater Neptune Suite', 'Floor-to-ceiling Aquarium bedroom', 2, 0, 950, Decimal('185000.00'), True, True),
                ]
            },
            {
                'name': 'The Leela Palace New Delhi',
                'dest': 'New Delhi',
                'address': 'Diplomatic Enclave, Chanakyapuri, New Delhi 110023',
                'star': 5,
                'user_rating': Decimal('4.9'),
                'reviews_count': 1150,
                'desc': 'Palatial elegance blending Lutyens architectural grandeur with Indian royal heritage, featuring a temperature-controlled rooftop infinity pool.',
                'featured': True,
                'rooms': [
                    ('Grande Deluxe Room', '1 King Bed', 2, 1, 550, Decimal('15000.00'), True, True),
                    ('Royal Premiere Room', '1 King Bed', 2, 1, 620, Decimal('21000.00'), True, True),
                    ('Executive Suite', '1 Master Bedroom + Lounge', 3, 1, 950, Decimal('42000.00'), True, True),
                ]
            },
        ]

        for h_info in hotels_seed:
            h_obj, _ = Hotel.objects.get_or_create(
                name=h_info['name'],
                defaults={
                    'destination': dest_dict[h_info['dest']],
                    'address': h_info['address'],
                    'star_rating': h_info['star'],
                    'user_rating': h_info['user_rating'],
                    'reviews_count': h_info['reviews_count'],
                    'description': h_info['desc'],
                    'is_featured': h_info['featured'],
                    'free_cancellation': True,
                    'breakfast_included_default': True,
                }
            )
            h_obj.amenities.set(amenities_objs[:6])

            for r_name, r_bed, r_ad, r_ch, r_sz, r_pr, r_bf, r_cn in h_info['rooms']:
                RoomType.objects.get_or_create(
                    hotel=h_obj,
                    name=r_name,
                    defaults={
                        'bed_type': r_bed,
                        'max_adults': r_ad,
                        'max_children': r_ch,
                        'room_size_sqft': r_sz,
                        'base_price_per_night': r_pr,
                        'free_breakfast': r_bf,
                        'free_cancellation': r_cn,
                        'total_inventory': 12
                    }
                )

        self.stdout.write(self.style.SUCCESS('-> Destinations, Hotels, and Room Types created.'))

        # 8. Package Categories
        cat_data = [
            ('Honeymoon Special', 'ph-heart-straight'),
            ('Family Holidays', 'ph-users-three'),
            ('Adventure & Trekking', 'ph-mountains'),
            ('Luxury & Wellness', 'ph-crown'),
            ('Beach Escapes', 'ph-sun-dim'),
            ('Heritage & Culture', 'ph-bank'),
        ]
        cat_dict = {}
        for c_name, c_icon in cat_data:
            c_obj, _ = PackageCategory.objects.get_or_create(name=c_name, defaults={'icon_code': c_icon})
            cat_dict[c_name] = c_obj

        # 9. Holiday Tour Packages with Detailed Itineraries
        packages_seed = [
            {
                'title': 'Kashmir Paradise: Srinagar, Gulmarg & Pahalgam Valley',
                'category': 'Honeymoon Special',
                'dest': 'Srinagar & Gulmarg',
                'days': 6,
                'nights': 5,
                'price': Decimal('28999.00'),
                'orig_price': Decimal('36000.00'),
                'overview': 'Immerse yourself in scenic alpine meadows, romantic Dal Lake Shikara rides, snow peaks of Gulmarg Apharwat, and the enchanting pine forests of Betaab Valley in Pahalgam.',
                'highlights': 'Complimentary 1-hour Dal Lake Shikara Sunset Cruise\nStay 1 Night in a Luxury Heritage Cedar Houseboat\nVisit Apharwat Peak via Gulmarg Gondola Phase 1 & 2\nPrivate AC Sedan for all transfers & excursions\nDaily Buffet Breakfast & 4-Course Gourmet Dinners',
                'itinerary': [
                    (1, 'Arrival in Srinagar & Dal Lake Shikara Ride', 'Arrive at Srinagar Airport. Traditional Kashmiri Kahwa welcome. Check-in to luxury Cedar Houseboat on Nigeen/Dal Lake. Evening romantic Shikara ride covering Floating Gardens and Char Chinar.', 'Luxury Houseboat at Dal Lake', 'Dinner Included'),
                    (2, 'Srinagar to Gulmarg Meadow of Flowers', 'Scenic 2-hour drive through apple orchards to Gulmarg (8,825 ft). Board the world famous Gulmarg Gondola to Kongdoori and Apharwat Peak for snow activities and alpine panorama.', '4-Star Resort in Gulmarg', 'Breakfast & Dinner'),
                    (3, 'Gulmarg to Pahalgam (Valley of Shepherds)', 'Drive to picturesque Pahalgam along the Lidder River. En route stop at the historic saffron fields of Pampore and Awantipora ruins. Evening leisure by the riverbank.', 'Riverside Deluxe Hotel in Pahalgam', 'Breakfast & Dinner'),
                    (4, 'Pahalgam Exploration - Betaab Valley & Aru Valley', 'Full day excursion to Chandanwari, Betaab Valley (famed in Bollywood), and serene Aru Valley by local union vehicle. Enjoy pony trekking and pine trail walks.', 'Riverside Deluxe Hotel in Pahalgam', 'Breakfast & Dinner'),
                    (5, 'Pahalgam to Srinagar & Mughal Gardens Tour', 'Return drive to Srinagar. Afternoon guided tour of the imperial Mughal Gardens: Shalimar Bagh, Nishat Bagh, and Chashme Shahi. Shopping for authentic Pashmina & saffron in Lal Chowk.', '5-Star Hotel in Srinagar', 'Breakfast & Dinner'),
                    (6, 'Departure from Srinagar', 'After breakfast, leisurely transfer to Srinagar Airport for your onward flight with golden memories of Paradise on Earth.', 'Departure', 'Breakfast Included'),
                ]
            },
            {
                'title': 'Enchanting Kerala Backwaters, Munnar Tea Hills & Alleppey Cruise',
                'category': 'Family Holidays',
                'dest': 'Munnar & Alleppey',
                'days': 5,
                'nights': 4,
                'price': Decimal('21999.00'),
                'orig_price': Decimal('27500.00'),
                'overview': 'Experience the emerald green tea slopes of Munnar, aromatic spice plantations of Thekkady, and a private luxury houseboat cruise on Alleppey backwaters with traditional Keralite feasts.',
                'highlights': 'Stay in an Authentic Air-Conditioned Alleppey Houseboat\nTour Mattupetty Dam, Echo Point & Tata Tea Museum in Munnar\nSpice Plantation Safari & Traditional Kathakali / Kalaripayattu Show\nAll Transfers in AC SUV / Sedan with English/Hindi Speaking Chauffeur\nTraditional Kerala Sadya Lunch on Banana Leaf',
                'itinerary': [
                    (1, 'Cochin Arrival & Scenic Drive to Munnar', 'Pick-up from Cochin Airport / Ernakulam Station. Drive through cascading Cheeyappara and Valara waterfalls to misty Munnar hill station. Check-in and relax.', 'Munnar Hill Resort', 'Dinner Included'),
                    (2, 'Full Day Munnar Tea Country Sightseeing', 'Visit Eravikulam National Park (home to endangered Nilgiri Tahr), Tata Tea Museum, Mattupetty Dam, and Echo Point. Evening spice market stroll.', 'Munnar Hill Resort', 'Breakfast & Dinner'),
                    (3, 'Munnar to Thekkady Periyar Wildlife Sanctuary', 'Drive through cardamom hills to Thekkady. Enjoy boat safari on Periyar Lake to spot wild elephants and sambar deer. Evening Kathakali dance performance.', 'Thekkady Jungle Lodge', 'Breakfast & Dinner'),
                    (4, 'Thekkady to Alleppey Backwater Houseboat Cruise', 'Board your private AC Deluxe Houseboat at 12:00 PM. Cruise through tranquil canals, paddy fields, and coconut lagoons. All meals freshly prepared on-board.', 'Private Alleppey Houseboat', 'Lunch, Dinner & Breakfast'),
                    (5, 'Alleppey to Cochin Departure', 'Enjoy breakfast on backwaters. Check-out at 9:00 AM and drive to Cochin. Brief visit to Fort Kochi & Chinese Fishing Nets before airport drop.', 'Departure', 'Breakfast Included'),
                ]
            },
            {
                'title': 'Dubai Extravaganza: Burj Khalifa, Desert Safari & Marina Cruise',
                'category': 'Luxury & Wellness',
                'dest': 'Dubai',
                'days': 5,
                'nights': 4,
                'price': Decimal('42500.00'),
                'orig_price': Decimal('52000.00'),
                'overview': 'Discover the glitz and glamour of Dubai. Marvel at the views from Burj Khalifa 124th floor, thrill with 4x4 dune bashing in red desert dunes, and dine under the stars aboard a Marina Dhow Cruise.',
                'highlights': 'Burj Khalifa At the Top (124th & 125th Floor) Observation Deck Tickets\nPremium Red Dunes Desert Safari with 4x4 Dune Bashing, BBQ & Belly Dance\nLuxury Dubai Marina Mega Yacht / Glass Dhow Dinner Cruise\nHalf-Day Dubai City Tour covering Dubai Frame, Palm Jumeirah & Gold Souk\nUAE Tourist Visa & Airport Pick/Drop Included',
                'itinerary': [
                    (1, 'Arrival in Dubai & Marina Dhow Cruise', 'Arrival at Dubai International Airport (DXB). VIP airport transfer to your 4-Star Downtown Hotel. Evening 2-hour Marina Dhow Cruise with international buffet and live Tanoura dance.', '4-Star Downtown Hotel', 'Dinner on Cruise'),
                    (2, 'Dubai City Tour & Burj Khalifa At The Top', 'Morning guided city tour: Dubai Frame photo-stop, Jumeirah Mosque, Burj Al Arab view, and Atlantis The Palm. Afternoon at Dubai Mall; ascend to the 124th floor of Burj Khalifa for 360-degree city views.', '4-Star Downtown Hotel', 'Breakfast Included'),
                    (3, 'Thrilling Desert Safari with BBQ Dinner', 'Morning free for shopping at Gold & Spice Souk. At 3:00 PM, 4x4 Land Cruiser pick-up for red dunes safari. Enjoy sandboarding, camel rides, quad biking, and lavish BBQ buffet with fire show.', '4-Star Downtown Hotel', 'Breakfast & BBQ Dinner'),
                    (4, 'Aquaventure Waterpark & Miracle Garden', 'Spend the morning amidst millions of blooming floral sculptures at Dubai Miracle Garden. Afternoon thrilling water coaster rides at Atlantis Aquaventure.', '4-Star Downtown Hotel', 'Breakfast Included'),
                    (5, 'Departure from Dubai', 'Breakfast at hotel. Free time for last minute duty-free shopping. Transfer to DXB Airport for your flight back home.', 'Departure', 'Breakfast Included'),
                ]
            },
            {
                'title': 'Tropical Bliss Bali: Temples, Waterfalls, Ubud & Nusa Penida',
                'category': 'Beach Escapes',
                'dest': 'Bali',
                'days': 6,
                'nights': 5,
                'price': Decimal('38999.00'),
                'orig_price': Decimal('47000.00'),
                'overview': 'A dream tropical getaway combining spiritual Ubud culture, cascading waterfalls, world-famous jungle swings, and the breathtaking cliffs of Nusa Penida Island.',
                'highlights': 'Full Day Speedboat Excursion to Nusa Penida (Kelingking T-Rex Beach & Broken Beach)\nIconic Bali Jungle Swing & Tegallalang Rice Terrace experience\nStay in Private Pool Villa in Seminyak / Ubud\nSunset at Uluwatu Cliff Temple with Kecak Fire Dance\nDaily Breakfast & Private Car with Driver for all days',
                'itinerary': [
                    (1, 'Denpasar Arrival & Transfer to Ubud', 'Arrival at Ngurah Rai Airport (DPS). Flower garland welcome and scenic transfer to Ubud cultural center. Check-in to private pool villa.', 'Ubud Jungle Villa with Private Pool', 'Dinner Included'),
                    (2, 'Ubud Highlights - Rice Terraces & Jungle Swing', 'Visit Tegenungan Waterfall, Sacred Monkey Forest Sanctuary, and Tegallalang Rice Terraces. Experience the famous high-altitude Bali swing overlooking palm valleys.', 'Ubud Jungle Villa with Private Pool', 'Breakfast Included'),
                    (3, 'Kintamani Volcano, Coffee Plantation & Seminyak Transfer', 'Tour Mount Batur active volcano viewpoint and organic Luwak coffee farm. Drive to Seminyak beachfront. Relax at Potato Head or Ku De Ta beach club.', 'Seminyak Luxury Beach Resort', 'Breakfast Included'),
                    (4, 'Nusa Penida Island Tour by Fast Boat', 'Early morning speed boat to Nusa Penida. Visit iconic Kelingking Secret Beach (T-Rex cliff), Angel Billabong, Broken Beach, and Crystal Bay for snorkeling.', 'Seminyak Luxury Beach Resort', 'Breakfast & Local Lunch'),
                    (5, 'Watersports at Tanjung Benoa & Uluwatu Sunset', 'Thrilling banana boat & parasailing at Tanjung Benoa beach. Afternoon drive to Uluwatu Temple perched on a 70m sheer cliff. Watch the dramatic sunset Kecak fire dance.', 'Seminyak Luxury Beach Resort', 'Breakfast & Seafood Dinner at Jimbaran'),
                    (6, 'Departure from Bali', 'After breakfast, enjoy a relaxing Balinese massage before transfer to DPS Airport for your departure.', 'Departure', 'Breakfast Included'),
                ]
            }
        ]

        for pkg in packages_seed:
            hp, created = HolidayPackage.objects.get_or_create(
                title=pkg['title'],
                defaults={
                    'category': cat_dict[pkg['category']],
                    'destination_city': pkg['dest'],
                    'duration_days': pkg['days'],
                    'duration_nights': pkg['nights'],
                    'starting_price': pkg['price'],
                    'original_price': pkg['orig_price'],
                    'overview': pkg['overview'],
                    'highlights': pkg['highlights'],
                    'is_featured': True,
                    'user_rating': Decimal('4.9'),
                    'reviews_count': random.randint(45, 120),
                    'flights_included': False,
                    'hotels_included': True,
                    'transfers_included': True,
                    'meals_included': True
                }
            )

            if created:
                for day_no, d_title, d_desc, d_stay, d_meals in pkg['itinerary']:
                    PackageItineraryDay.objects.create(
                        package=hp,
                        day_number=day_no,
                        title=d_title,
                        description=d_desc,
                        stay_info=d_stay,
                        meals_info=d_meals
                    )

        self.stdout.write(self.style.SUCCESS('-> Holiday Packages & Day-by-Day Itineraries created.'))

        # 10. Coupons & Promos
        coupons_data = [
            ('JUSTRELAX500', 'Flat ₹500 Off on First Booking', DiscountType.FIXED, Decimal('500.00'), Decimal('2500.00'), Decimal('500.00'), ApplicableService.ALL),
            ('FLYHIGH1000', '₹1,000 Off on Domestic & Intl Flights', DiscountType.FIXED, Decimal('1000.00'), Decimal('5000.00'), Decimal('1000.00'), ApplicableService.FLIGHT),
            ('STAYLUXE15', '15% Off on 5-Star Luxury Hotels', DiscountType.PERCENTAGE, Decimal('15.00'), Decimal('8000.00'), Decimal('3500.00'), ApplicableService.HOTEL),
            ('HOLIDAY3000', 'Flat ₹3,000 Off on Holiday Packages', DiscountType.FIXED, Decimal('3000.00'), Decimal('20000.00'), Decimal('3000.00'), ApplicableService.PACKAGE),
        ]
        valid_date = now_date + timedelta(days=365)
        for code, title, dtype, dval, min_sp, cap, app_to in coupons_data:
            Coupon.objects.get_or_create(
                code=code,
                defaults={
                    'title': title,
                    'discount_type': dtype,
                    'discount_value': dval,
                    'min_spend': min_sp,
                    'max_discount_cap': cap,
                    'applicable_to': app_to,
                    'valid_until': valid_date,
                    'is_active': True
                }
            )

        # 11. Customer Reviews
        reviews_data = [
            (customer_user, ApplicableService.FLIGHT, 5, 'Super fast booking & instant seat confirmation!', 'Booked Delhi to Mumbai on IndiGo via JustRelax. The seat map widget and live pricing made checkout effortless. Received PNR & WhatsApp ticket instantly.'),
            (customer_user, ApplicableService.HOTEL, 5, 'Unforgettable stay at Taj Mahal Palace Mumbai', 'Got free breakfast upgrade and early check-in. The photos and room details on JustRelax were 100% accurate.'),
            (customer_user, ApplicableService.PACKAGE, 5, 'Mesmerizing Kashmir Holiday Tour!', 'Everything from the houseboat in Dal Lake to the Gondola tickets in Gulmarg was meticulously arranged. 10/10 service.'),
        ]
        for r_user, r_serv, r_star, r_title, r_comm in reviews_data:
            CustomerReview.objects.get_or_create(
                user=r_user,
                title=r_title,
                defaults={
                    'service_type': r_serv,
                    'rating': r_star,
                    'comment': r_comm,
                    'is_approved': True
                }
            )

        self.stdout.write(self.style.SUCCESS('\n========================================='))
        self.stdout.write(self.style.SUCCESS(' JustRelax Seed Data Populated Successfully!'))
        self.stdout.write(self.style.SUCCESS(' Admin Login:  username: admin | password: admin123'))
        self.stdout.write(self.style.SUCCESS(' Agent Login:  username: agent_roy | password: agent123'))
        self.stdout.write(self.style.SUCCESS(' Customer:     username: customer_alex | password: pass123'))
        self.stdout.write(self.style.SUCCESS('=========================================\n'))

