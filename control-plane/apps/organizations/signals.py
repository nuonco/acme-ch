from django.db.models.signals import post_save
from django.dispatch import receiver
from organizations.models import Organization
from organizations.tasks import create_nuon_install, create_service_account_user


@receiver(post_save, sender=Organization)
def organization_post_create(sender, instance, created, **kwargs):
    if created:
        create_nuon_install.delay(instance.id)
        create_service_account_user.delay(instance.id)
