from .models import HRMO

def user_context(request):
    """Add user-related context to all templates"""
    context = {
        'is_hrmo': False,
        'staff_record': None,
    }
    
    if request.user.is_authenticated:
        # Check if user is HRMO
        try:
            hrmo = HRMO.objects.get(user=request.user, is_active=True)
            context['is_hrmo'] = True
            context['staff_record'] = hrmo.staff
        except HRMO.DoesNotExist:
            # Try to find staff record by email
            from .models import Staff
            try:
                staff = Staff.objects.get(email=request.user.email)
                context['staff_record'] = staff
            except Staff.DoesNotExist:
                pass
    
    return context