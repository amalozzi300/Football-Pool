from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

class CreateUserForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = UserCreationForm.Meta.fields + ('street_address', 'city', 'state', 'zip_code', 'phone_number')

class EditUserForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = UserChangeForm.Meta.fields + ('street_address', 'city', 'state', 'zip_code', 'phone_number')
        