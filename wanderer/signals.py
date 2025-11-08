"""Signal handlers for Wanderer."""

import logging

from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from wanderer.models import WandererManagedMap

logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender=WandererManagedMap.admin_users.through)
@receiver(m2m_changed, sender=WandererManagedMap.admin_groups.through)
@receiver(m2m_changed, sender=WandererManagedMap.manager_users.through)
@receiver(m2m_changed, sender=WandererManagedMap.manager_groups.through)
def trigger_cleanup_on_admin_change(sender, instance, action, **kwargs):
    """
    When admin/manager assignments change, trigger ACL cleanup to sync roles.

    This signal is triggered when:
    - Admin users are added/removed from a map
    - Admin groups are added/removed from a map
    - Manager users are added/removed from a map
    - Manager groups are added/removed from a map

    The cleanup task will sync the ACL roles to match the new assignments.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        from .tasks import cleanup_access_list

        logger.info(
            "Admin/manager assignment changed for map '%s' (ID:%s), triggering ACL cleanup",
            instance.name,
            instance.pk,
        )
        cleanup_access_list.delay(instance.pk)
