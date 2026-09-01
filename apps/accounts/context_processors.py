def auth_user_context(request):
    """Context processor providing user role & agent info across templates."""
    context = {
        'is_agent': False,
        'agent_profile': None,
        'user_wallet': None,
    }
    if request.user.is_authenticated:
        context['is_agent'] = getattr(request.user, 'is_agent', False)
        if context['is_agent'] and hasattr(request.user, 'agent_profile'):
            context['agent_profile'] = request.user.agent_profile
        
        if hasattr(request.user, 'wallet'):
            context['user_wallet'] = request.user.wallet
    return context
