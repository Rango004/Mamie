from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import UserProfile

class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for static files, media files, admin, and auth paths
        if (request.path.startswith('/static/') or 
            request.path.startswith('/media/') or
            request.path.startswith('/admin/') or
            request.path.startswith('/accounts/')):
            response = self.get_response(request)
            return response
        
        # Check if user is authenticated and needs to change password
        if request.user.is_authenticated:
            # Skip change password page itself
            if request.path == reverse('change_password'):
                response = self.get_response(request)
                return response
                
            try:
                profile = UserProfile.objects.get(user=request.user)
                if profile.must_change_password:
                    return redirect('change_password')
            except UserProfile.DoesNotExist:
                pass

        response = self.get_response(request)
        return response