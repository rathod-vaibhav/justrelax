from django.shortcuts import render, get_object_or_404, redirect
from decimal import Decimal
from .models import PackageCategory, HolidayPackage, PackageItineraryDay

def packages_list_view(request):
    category_slug = request.GET.get('category')
    dest_query = request.GET.get('destination')
    duration_filter = request.GET.get('duration') # e.g. 'short' (1-4), 'medium' (5-7), 'long' (8+)
    max_price = request.GET.get('max_price')
    sort_by = request.GET.get('sort', 'featured')

    packages_qs = HolidayPackage.objects.filter(is_active=True).select_related('category')

    if category_slug:
        packages_qs = packages_qs.filter(category__slug=category_slug)

    if dest_query:
        packages_qs = packages_qs.filter(destination_city__icontains=dest_query)

    if duration_filter == 'short':
        packages_qs = packages_qs.filter(duration_days__lte=4)
    elif duration_filter == 'medium':
        packages_qs = packages_qs.filter(duration_days__gte=5, duration_days__lte=7)
    elif duration_filter == 'long':
        packages_qs = packages_qs.filter(duration_days__gte=8)

    if max_price:
        try:
            packages_qs = packages_qs.filter(starting_price__lte=Decimal(max_price))
        except:
            pass

    agent_markup_pct = Decimal('0.00')
    if request.user.is_authenticated and getattr(request.user, 'is_agent', False):
        if hasattr(request.user, 'agent_profile'):
            agent_markup_pct = request.user.agent_profile.markup_package_pct

    package_results = []
    for pkg in packages_qs:
        markup_val = (pkg.starting_price * agent_markup_pct) / Decimal('100.00')
        display_price = pkg.starting_price + markup_val
        package_results.append({
            'package': pkg,
            'starting_price': pkg.starting_price,
            'display_price': display_price,
            'markup_val': markup_val,
        })

    if sort_by == 'price_low':
        package_results.sort(key=lambda x: x['display_price'])
    elif sort_by == 'price_high':
        package_results.sort(key=lambda x: x['display_price'], reverse=True)
    elif sort_by == 'rating':
        package_results.sort(key=lambda x: x['package'].user_rating, reverse=True)

    categories = PackageCategory.objects.all()

    context = {
        'packages': package_results,
        'categories': categories,
        'selected_category': category_slug,
        'dest_query': dest_query,
        'duration_filter': duration_filter,
        'sort_by': sort_by,
        'agent_markup_pct': agent_markup_pct,
    }
    return render(request, 'customer/packages_list.html', context)


def package_detail_view(request, slug):
    package = get_object_or_404(HolidayPackage.objects.prefetch_related('itinerary_days'), slug=slug)
    
    agent_markup_pct = Decimal('0.00')
    if request.user.is_authenticated and getattr(request.user, 'is_agent', False):
        if hasattr(request.user, 'agent_profile'):
            agent_markup_pct = request.user.agent_profile.markup_package_pct

    markup_val = (package.starting_price * agent_markup_pct) / Decimal('100.00')
    display_price = package.starting_price + markup_val

    context = {
        'package': package,
        'display_price': display_price,
        'agent_markup_pct': agent_markup_pct,
        'itinerary_days': package.itinerary_days.all(),
    }
    return render(request, 'customer/package_detail.html', context)
