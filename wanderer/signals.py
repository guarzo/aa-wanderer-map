"""Signal handlers for Wanderer."""

import logging

from django.db import transaction
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from wanderer.models import WandererManagedMap

logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender=WandererManagedMap.admin_users.through)
@receiver(m2m_changed, sender=WandererManagedMap.admin_groups.through)
@receiver(m2m_changed, sender=WandererManagedMap.manager_users.through)
@receiver(m2m_changed, sender=WandererManagedMap.manager_groups.through)
def trigger_cleanup_on_admin_change(_sender, instance, action, **kwargs):
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

        is_reverse = kwargs.get("reverse", False)

        if is_reverse:
            # When reverse=True, instance is a User/Group, not a Map
            # pk_set contains the Map IDs
            pk_set = kwargs.get("pk_set")
            if pk_set:
                for map_id in pk_set:
                    logger.info(
                        "Admin/manager assignment changed for map ID:%s, triggering ACL cleanup",
                        map_id,
                    )
                    transaction.on_commit(
                        lambda mid=map_id: cleanup_access_list.delay(mid)
                    )
        else:
            # When reverse=False, instance is the Map
            logger.info(
                "Admin/manager assignment changed for map '%s' (ID:%s), triggering ACL cleanup",
                instance.name,
                instance.pk,
            )
            transaction.on_commit(lambda: cleanup_access_list.delay(instance.pk))
