from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView

from footballpool.profiles.forms import ProfileForm, RegisterUserForm
from footballpool.profiles.mixins import RedirectAuthenticatedUserMixin
from footballpool.profiles.models import Profile


class TemporaryHomepageView(View):
    """
    Temporary.
    If not an authenticated user, redirects to login. Else, redirects to profile display.
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('view_profile', request.user.username)
        else:
            return redirect('login')
        

class RegisterUserView(RedirectAuthenticatedUserMixin, CreateView):
    form_class = RegisterUserForm
    template_name = 'profiles/register_user.html'

    def get_success_url(self):
        return reverse_lazy('edit_profile', kwargs={'username': self.request.user.username})

    def form_valid(self, form):
        # Save the new User
        user = form.save()

        # Use form data to ensure proper authentication
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password1')
        auth_user = authenticate(self.request, username=username, password=password)

        if auth_user is not None:
            login(self.request, auth_user)

        return redirect(self.get_success_url())


class LoginView(RedirectAuthenticatedUserMixin, DjangoLoginView):
    template_name = 'profiles/login.html'
    
    def get_success_url(self):
        next_url = self.request.GET.get('next')

        if next_url:
            return next_url
        
        if self.request.user.profile.is_completed_profile:
            return reverse_lazy('view_profile', kwargs={'username': self.request.user.username})
        else:
            return reverse_lazy('edit_profile', kwargs={'username': self.request.user.username})


class ViewProfileView(DetailView):
    """
    View to display a profile.
    """
    model = Profile
    slug_field = 'user__username'
    slug_url_kwarg = 'username'
    template_name = 'profiles/view_profile.html'
    context_object_name = 'profile'


class EditProfileView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    slug_field = 'user__username'
    slug_url_kwarg = 'username'
    template_name = 'profiles/edit_profile.html'
    context_object_name = 'profile'
    
    def test_func(self):
        profile = self.get_object()
        return profile.user == self.request.user
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied('You are not authorized to access this page.')
        
        return super().handle_no_permission()
    
    def get_success_url(self):
        return reverse_lazy('view_profile', kwargs={'username': self.request.user.username})
    
    def get(self, request, *args, **kwargs):
        profile = self.get_object()
        storage = messages.get_messages(request)
        message_text = 'Please complete your profile.'

        if not profile.is_completed_profile and not any(m.message == message_text for m in storage):
            messages.warning(request, message_text)
        
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your profile was updated successfully!')
        return response