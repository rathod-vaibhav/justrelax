from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .forms import CustomerRegisterForm, AgentRegisterForm
from .models import UserRole, AgentProfile
from apps.wallet.models import Wallet
from apps.flights.models import Airport, FlightDailyInstance
from apps.hotels.models import Hotel, Destination
from apps.packages.models import HolidayPackage, PackageCategory
from apps.promotions.models import Coupon, CustomerReview

def home_view(request):
    """MakeMyTrip style landing page with dynamic Hero Booking Widget."""
    airports = Airport.objects.all()
    destinations = Destination.objects.filter(is_popular=True)
    categories = PackageCategory.objects.all()

    # Agent Markup consideration if logged-in agent
    agent_markup_pkg = Decimal('0.00')
    agent_markup_hotel = Decimal('0.00')
    if request.user.is_authenticated and getattr(request.user, 'is_agent', False):
        if hasattr(request.user, 'agent_profile'):
            agent_markup_pkg = request.user.agent_profile.markup_package_pct
            agent_markup_hotel = request.user.agent_profile.markup_hotel_pct

    # Featured Packages
    featured_packages_raw = HolidayPackage.objects.filter(is_featured=True, is_active=True).select_related('category')[:6]
    featured_packages = []
    for p in featured_packages_raw:
        markup = (p.starting_price * agent_markup_pkg) / Decimal('100.00')
        featured_packages.append({
            'pkg': p,
            'display_price': p.starting_price + markup,
        })

    # Featured Hotels
    featured_hotels_raw = Hotel.objects.filter(is_featured=True, is_active=True).select_related('destination')[:6]
    featured_hotels = []
    for h in featured_hotels_raw:
        min_p = h.min_price
        markup = (min_p * agent_markup_hotel) / Decimal('100.00')
        featured_hotels.append({
            'hotel': h,
            'display_price': min_p + markup,
        })

    # Active Coupons & Reviews
    coupons = Coupon.objects.filter(is_active=True, valid_until__gte=timezone.now().date())[:4]
    reviews = CustomerReview.objects.filter(is_approved=True).select_related('user')[:4]

    # Default flight dates
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)

    context = {
        'airports': airports,
        'destinations': destinations,
        'categories': categories,
        'featured_packages': featured_packages,
        'featured_hotels': featured_hotels,
        'coupons': coupons,
        'reviews': reviews,
        'today_str': today.strftime('%Y-%m-%d'),
        'tomorrow_str': tomorrow.strftime('%Y-%m-%d'),
        'day_after_str': day_after.strftime('%Y-%m-%d'),
    }
    return render(request, 'customer/home.html', context)


def login_view(request):
    if request.user.is_authenticated:
        if request.user.role == UserRole.ADMIN or request.user.is_superuser:
            return redirect('admin_dashboard')
        elif request.user.role == UserRole.AGENT:
            return redirect('agent_dashboard')
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            if user.role in [UserRole.ADMIN, UserRole.STAFF] or user.is_superuser:
                return redirect('admin_dashboard')
            elif user.role == UserRole.AGENT:
                return redirect('agent_dashboard')
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'auth/login.html', {'form': form})


def register_customer_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = CustomerRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Wallet.objects.get_or_create(user=user, defaults={'balance': 1000.00})
            login(request, user)
            messages.success(request, "Registration successful! You received ₹1,000 welcome wallet bonus.")
            return redirect('home')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomerRegisterForm()

    return render(request, 'auth/register_customer.html', {'form': form})


def register_agent_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AgentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Wallet.objects.get_or_create(user=user, defaults={'balance': 0.00})
            login(request, user)
            messages.success(request, "Agent registration submitted! Your account is active with trial access while KYC is verified.")
            return redirect('agent_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AgentRegisterForm()

    return render(request, 'auth/register_agent.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
            
        user.save()

        # Update B2B Agent Profile if user is a Travel Agent
        if getattr(user, 'is_agent', False) and hasattr(user, 'agent_profile'):
            profile = user.agent_profile
            profile.agency_name = request.POST.get('agency_name', profile.agency_name)
            profile.agency_phone = request.POST.get('agency_phone', profile.agency_phone)
            profile.agency_email = request.POST.get('agency_email', profile.agency_email)
            profile.agency_address = request.POST.get('agency_address', profile.agency_address)
            profile.city = request.POST.get('city', profile.city)
            profile.country = request.POST.get('country', profile.country)
            profile.tax_or_pan = request.POST.get('tax_or_pan', profile.tax_or_pan)
            profile.gstin = request.POST.get('gstin', profile.gstin)

            if 'agency_logo' in request.FILES:
                profile.agency_logo = request.FILES['agency_logo']
            profile.save()

        messages.success(request, "Your profile and profile photo have been updated successfully.")
        return redirect('profile')

    is_agent = user.is_agent and hasattr(user, 'agent_profile')
    agent_profile = getattr(user, 'agent_profile', None)

    # Choose base template dynamically based on portal role
    base_template = 'base.html'
    if user.is_admin_or_staff:
        base_template = 'admin_panel/base_admin.html'
    elif is_agent:
        base_template = 'agent/base_agent.html'

    context = {
        'user': user,
        'is_agent': is_agent,
        'agent_profile': agent_profile,
        'base_template': base_template,
    }
    return render(request, 'auth/profile.html', context)

