from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from decimal import Decimal
from apps.accounts.models import AgentProfile, KycStatus, UserRole
from apps.bookings.models import MasterBooking, BookingStatus
from apps.wallet.models import Wallet, TransactionType, WalletTransaction

def agent_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not getattr(request.user, 'is_agent', False) and not request.user.is_admin_or_staff:
            messages.error(request, "Access restricted to registered Travel Agents.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
@agent_required
def agent_dashboard_view(request):
    agent = request.user
    agent_profile, _ = AgentProfile.objects.get_or_create(user=agent, defaults={'agency_name': f"{agent.username}'s Agency"})
    wallet, _ = Wallet.objects.get_or_create(user=agent, defaults={'balance': Decimal('0.00')})

    # Stats
    agent_bookings = MasterBooking.objects.filter(agent=agent)
    total_bookings = agent_bookings.count()
    confirmed_bookings = agent_bookings.filter(booking_status=BookingStatus.CONFIRMED).count()
    
    total_sales = agent_bookings.filter(booking_status=BookingStatus.CONFIRMED).aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
    total_markup_earned = agent_bookings.filter(booking_status=BookingStatus.CONFIRMED).aggregate(m=Sum('agent_markup_amount'))['m'] or Decimal('0.00')

    recent_bookings = agent_bookings.order_by('-created_at')[:8]

    context = {
        'agent_profile': agent_profile,
        'wallet': wallet,
        'total_bookings': total_bookings,
        'confirmed_bookings': confirmed_bookings,
        'total_sales': total_sales,
        'total_markup_earned': total_markup_earned,
        'recent_bookings': recent_bookings,
    }
    return render(request, 'agent/dashboard.html', context)


@login_required
@agent_required
def agent_markups_view(request):
    agent_profile = get_object_or_404(AgentProfile, user=request.user)

    if request.method == 'POST':
        try:
            agent_profile.markup_flight_pct = Decimal(request.POST.get('markup_flight_pct', '0.00'))
            agent_profile.markup_hotel_pct = Decimal(request.POST.get('markup_hotel_pct', '0.00'))
            agent_profile.markup_package_pct = Decimal(request.POST.get('markup_package_pct', '0.00'))
            agent_profile.save()
            messages.success(request, "Your default agency markup percentages have been updated!")
        except Exception as e:
            messages.error(request, f"Error updating markups: {str(e)}")
        return redirect('agent_markups')

    return render(request, 'agent/markups.html', {'agent_profile': agent_profile})


@login_required
@agent_required
def agent_wallet_view(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all().order_by('-created_at')

    if request.method == 'POST':
        amount_str = request.POST.get('amount')
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")
            wallet.credit(amount, "Agent Instant Wallet Recharge", ref="AGENT_TOPUP")
            messages.success(request, f"Successfully credited ₹{amount:.2f} to your agency wallet!")
        except Exception as e:
            messages.error(request, f"Failed to recharge wallet: {str(e)}")
        return redirect('agent_wallet')

    return render(request, 'agent/wallet.html', {
        'wallet': wallet,
        'transactions': transactions,
        'agent_profile': getattr(request.user, 'agent_profile', None)
    })


@login_required
@agent_required
def agent_kyc_upload_view(request):
    agent_profile = get_object_or_404(AgentProfile, user=request.user)

    if request.method == 'POST':
        agent_profile.tax_or_pan = request.POST.get('tax_or_pan', agent_profile.tax_or_pan)
        agent_profile.gstin = request.POST.get('gstin', agent_profile.gstin)
        agent_profile.agency_address = request.POST.get('agency_address', agent_profile.agency_address)
        
        if 'kyc_document' in request.FILES:
            agent_profile.kyc_document = request.FILES['kyc_document']
            agent_profile.kyc_status = KycStatus.PENDING
        
        if 'agency_logo' in request.FILES:
            agent_profile.agency_logo = request.FILES['agency_logo']

        agent_profile.save()
        messages.success(request, "KYC details submitted for administrator review.")
        return redirect('agent_dashboard')

    return render(request, 'agent/kyc_upload.html', {'agent_profile': agent_profile})
