from django.contrib.auth.forms import UserCreationForm, UsernameField
from django.contrib.auth.models import User
from django.forms import ModelForm, CharField, EmailField, ValidationError

from footballpool.profiles.models import Profile


class RegisterUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'password1',
            'password2',
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            raise ValidationError('A profile with this email already exists.')
    
        return email

class ProfileForm(ModelForm):
    username = UsernameField(label='Username')
    first_name = CharField(max_length=150, label='First Name')
    last_name = CharField(max_length=150, label='Last Name')
    email = EmailField(label='Email')

    class Meta:
        model = Profile
        exclude = ('user', 'payment_method',)
        field_order = [
            'username',
            'first_name',
            'last_name',
            'email',
            'phone_number',
            'street_address',
            'city',
            'state',
            'zip_code',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].initial = self.instance.user.username
        self.fields['first_name'].initial = self.instance.user.first_name
        self.fields['last_name'].initial = self.instance.user.last_name
        self.fields['email'].initial = self.instance.user.email
        self.order_fields(self.Meta.field_order)

    def save(self, commit=True):
        instance = super().save(commit=False)
        user = instance.user
        user.username = self.cleaned_data.get('username')
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.email = self.cleaned_data.get('email')

        if commit:
            user.save()
            instance.save()

        return instance