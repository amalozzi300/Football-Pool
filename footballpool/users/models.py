from django.contrib.auth.models import AbstractUser
from django.db import models

from localflavor.us.models import USStateField, USZipCodeField
from phone_field import PhoneField

PAYMENT_METHODS = (
    ('cash', 'Cash'),
    ('check', 'Check'),
    ('paypal', 'PayPal'),
    ('venmo', 'Venmo'),
)

class User(AbstractUser):
    email = models.EmailField(unique=True)
    street_address = models.CharField(max_length=512, help_text='Include Apt./Ste./PO # here.')
    city = models.CharField(max_length=128)
    state = USStateField()
    zip_code = USZipCodeField()
    phone_number = PhoneField()
    is_paid = models.BooleanField(default=False, blank=True)
    payment_method = models.CharField(max_length=6, choices=PAYMENT_METHODS, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.get_full_name()