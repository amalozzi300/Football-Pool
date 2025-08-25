from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from profiles.models import Profile


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """
    Automatically creates a Profile object when a User object is created.
    """
    if created:
        user = instance
        profile = Profile.objects.create(user=user)

@receiver(post_delete, sender=Profile)
def delete_user(sender, instance, **kwargs):
    """
    Automatically deletes a User object when the Profile object it's associated with is deleted.
    If the User object cannot be found, no action is required.
    """
    try:
        user = instance.user
        user.delete()
    except:
        pass