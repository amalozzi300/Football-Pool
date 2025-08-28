from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models

from localflavor.us.models import USStateField, USZipCodeField

PAYMENT_METHOD_CHOICES = (
    ('', 'Not Paid'),
    ('cash', 'Cash'),
    ('check', 'Check'),
    ('paypal', 'PayPal'),
    ('venmo', 'Venmo'),
)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(
        max_length=12, null=True, validators=[RegexValidator(r'^\d{3}-\d{3}-\d{4}$', 'Please format the phone number as XXX-XXX-XXXX.')]
    )
    street_address = models.CharField(max_length=1024, null=True)
    city = models.CharField(max_length=128, null=True)
    state = USStateField(null=True)
    zip_code = USZipCodeField(null=True)
    payment_method = models.CharField(max_length=8, choices=PAYMENT_METHOD_CHOICES, default='')

    class Meta:
        ordering = ['user__first_name', 'user__last_name']

    @property
    def is_paid(self):
        return bool(self.payment_method)
    
    @property
    def is_completed_profile(self):
        return self.phone_number and self.street_address and self.city and self.state and self.zip_code
    
    def __str__(self):
        if self.user.first_name and self.user.last_name:
            return f'{self.user.first_name} {self.user.last_name}'
        
        return self.user.username