from django.shortcuts import redirect


class RedirectAuthenticatedUserMixin:
    """ 
    Redirects logged-in users to their profile view when attempting to access login/register views.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('view_profile', username=request.user.username)
        
        return super().dispatch(request, *args, **kwargs)