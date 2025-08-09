from django import template
from staff.models import HRMO

register = template.Library()

@register.filter
def is_hrmo(user):
    """Check if user is an active HRMO"""
    try:
        return HRMO.objects.filter(user=user, is_active=True).exists()
    except:
        return False

@register.filter
def get_staff_record(user):
    """Get staff record for user"""
    try:
        hrmo = HRMO.objects.get(user=user, is_active=True)
        return hrmo.staff
    except:
        # Try to find staff by email
        from staff.models import Staff
        try:
            return Staff.objects.get(email=user.email)
        except:
            return None