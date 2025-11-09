"""Tasks."""

from celery import chain, shared_task

from allianceauth.services.hooks import get_extension_logger

from wanderer.models import WandererAccount, WandererManagedMap
from wanderer.wanderer import (
    AccessListRoles,
    NotFoundError,
    get_member_role,
    update_character_role,
)

logger = get_extension_logger(__name__)


@shared_task
def add_alts_to_map(wanderer_user_id: int, wanderer_managed_map_id: int):
    """
    Ensures that all alts of this user are properly added on the wanderer map ACL.

    MODIFIED: Now assigns admin/manager roles based on map configuration.
    """
    logger.info(
        "Updating character of user id %d on map id %d",
        wanderer_user_id,
        wanderer_managed_map_id,
    )

    wanderer_user = WandererAccount.objects.get(pk=wanderer_user_id)
    wanderer_managed_map = WandererManagedMap.objects.get(pk=wanderer_managed_map_id)

    logger.debug("Recovered user %s and map %s", wanderer_user, wanderer_managed_map)

    characters_on_acl_ids_set = set(
        wanderer_managed_map.get_character_ids_on_access_list()
    )
    logger.debug(characters_on_acl_ids_set)
    user_character_ids_set = set(wanderer_user.get_all_character_ids())
    logger.debug(user_character_ids_set)

    missing_characters_set = user_character_ids_set - characters_on_acl_ids_set
    logger.info(
        "Need to add %d characters to the access list", len(missing_characters_set)
    )
    logger.debug(missing_characters_set)

    # Add missing characters with appropriate roles
    for missing_character_id in missing_characters_set:
        # Determine the role this character should have
        role = wanderer_managed_map.get_character_role(missing_character_id)
        logger.debug(
            "Adding character id %d to the access list with role %s",
            missing_character_id,
            role.value,
        )
        # Add with the determined role
        wanderer_managed_map.add_character_to_acl(missing_character_id, role=role)

    # Invalidate cache after modifications
    wanderer_managed_map.invalidate_acl_cache()
    logger.info("Invalidated ACL cache after adding characters")


@shared_task
def remove_user_characters_from_map(
    wanderer_user_id: int, wanderer_managed_map_id: int
):
    """
    Removes all characters from that specific user from the map
    """
    logger.info(
        "Removing all characters of user id %d from map id %d",
        wanderer_user_id,
        wanderer_managed_map_id,
    )

    wanderer_user = WandererAccount.objects.get(pk=wanderer_user_id)
    wanderer_managed_map = WandererManagedMap.objects.get(pk=wanderer_managed_map_id)
    logger.debug(wanderer_user, wanderer_managed_map)

    characters_on_acl_ids_set = set(
        wanderer_managed_map.get_character_ids_on_access_list()
    )
    logger.debug(characters_on_acl_ids_set)
    user_character_ids_set = set(wanderer_user.get_all_character_ids())
    logger.debug(user_character_ids_set)

    character_ids_to_remove = characters_on_acl_ids_set & user_character_ids_set

    for character_id_to_remove in character_ids_to_remove:
        logger.debug(
            "Removing char id %d from map %s",
            character_id_to_remove,
            wanderer_managed_map,
        )
        wanderer_managed_map.remove_member_from_access_list(character_id_to_remove)

    # Invalidate cache after modifications
    wanderer_managed_map.invalidate_acl_cache()
    logger.info("Invalidated ACL cache after removing characters")


@shared_task
def cleanup_access_list(
    wanderer_managed_map_id: int,
):  # pylint: disable=too-many-locals
    """
    Cleanup the access list for a Wanderer map.

    MODIFIED: Now syncs admin/manager roles in addition to membership.

    Steps:
    1. Remove unauthorized characters
    2. Add missing authorized characters (with correct roles)
    3. Update roles for existing characters (promote/demote as needed)
    4. Preserve manually-set admin/manager roles not managed by Auth
    """
    logger.info("Updating access list of map id %d", wanderer_managed_map_id)

    wanderer_managed_map = WandererManagedMap.objects.get(pk=wanderer_managed_map_id)

    # Get current state
    characters_on_acl_ids_set = set(
        wanderer_managed_map.get_character_ids_on_access_list()
    )
    logger.debug("Member characters on ACL: %s", characters_on_acl_ids_set)

    # Get non-member characters (admin, manager, viewer, blocked, etc.)
    non_member_characters = wanderer_managed_map.get_non_member_characters()
    non_member_char_ids = {char_id for char_id, role in non_member_characters}
    logger.debug("Non-member characters on ACL: %s", non_member_char_ids)

    characters_that_should_be_on_acls_ids_set = set(
        wanderer_managed_map.get_all_accounts_characters_ids()
    )
    logger.debug(
        "Characters that should be on ACL: %s",
        characters_that_should_be_on_acls_ids_set,
    )

    admin_char_ids = wanderer_managed_map.get_admin_character_ids()
    manager_char_ids = wanderer_managed_map.get_manager_character_ids()

    def expected_role_for(character_id: int) -> AccessListRoles:
        if character_id in admin_char_ids:
            return AccessListRoles.ADMIN
        if character_id in manager_char_ids:
            return AccessListRoles.MANAGER
        return AccessListRoles.MEMBER

    # Step 1: Remove unauthorized MEMBER-role characters
    # Note: We only remove unauthorized members; non-member roles are handled in Step 4
    character_ids_to_remove = (
        characters_on_acl_ids_set - characters_that_should_be_on_acls_ids_set
    )
    logger.info("Removing %d character ids from the ACL", len(character_ids_to_remove))
    for character_id_to_remove in character_ids_to_remove:
        logger.debug("Removing char id %d", character_id_to_remove)
        wanderer_managed_map.remove_member_from_access_list(character_id_to_remove)

    # Step 2: Add missing characters with correct roles
    # Exclude non-member characters as they're already on the ACL
    character_ids_to_add = (
        characters_that_should_be_on_acls_ids_set
        - characters_on_acl_ids_set
        - non_member_char_ids
    )
    logger.info("Adding %d character ids to the ACL", len(character_ids_to_add))
    for character_id_to_add in character_ids_to_add:
        role = expected_role_for(character_id_to_add)
        logger.debug(
            "Adding character id %d with role %s", character_id_to_add, role.value
        )
        wanderer_managed_map.add_character_to_acl(character_id_to_add, role=role)

    # Step 3: Update roles for existing authorized characters (both members and non-members)
    existing_authorized_chars = (
        characters_on_acl_ids_set | non_member_char_ids
    ) & characters_that_should_be_on_acls_ids_set
    logger.info(
        "Checking roles for %d existing characters", len(existing_authorized_chars)
    )

    for character_id in existing_authorized_chars:
        expected_role = expected_role_for(character_id)

        try:
            current_role = get_member_role(
                wanderer_managed_map.wanderer_url,
                wanderer_managed_map.map_acl_id,
                wanderer_managed_map.map_acl_api_key,
                character_id,
            )

            # Only update if role has changed
            if current_role != expected_role:
                logger.info(
                    "Map '%s' (ID:%d): Updating character %d role from %s to %s",
                    wanderer_managed_map.name,
                    wanderer_managed_map_id,
                    character_id,
                    current_role.value,
                    expected_role.value,
                )
                update_character_role(
                    wanderer_managed_map.wanderer_url,
                    wanderer_managed_map.map_acl_id,
                    wanderer_managed_map.map_acl_api_key,
                    character_id,
                    expected_role,
                )
        except NotFoundError:
            # Character disappeared from ACL, skip
            logger.warning(
                "Character %d not found on ACL during role sync", character_id
            )
            continue
        except Exception:  # pylint: disable=broad-exception-caught
            # Log other errors but continue with other characters
            # Broad exception is intentional - we want to process all characters
            # even if one encounters an unexpected error
            logger.exception(
                "Error updating role for character %d",
                character_id,
            )
            continue

    # Step 4: Handle non-member roles (preserve manually-set admin/manager)
    # This preserves admins/managers NOT managed by Auth
    # We use the non_member_characters we got earlier (stored during initial ACL fetch)
    for character_id, role in non_member_characters:
        # If they're Auth-managed admin/manager, they were already updated in Step 3
        if character_id in admin_char_ids or character_id in manager_char_ids:
            continue

        # This is a manually-set admin/manager not managed by Auth, or VIEWER/BLOCKED
        # Only demote viewers and blocked users, preserve manual admin/manager
        if role in [AccessListRoles.VIEWER, AccessListRoles.BLOCKED]:
            logger.info(
                "Demoting character %d from %s to member",
                character_id,
                role.value,
            )
            wanderer_managed_map.set_character_to_member(character_id)

    # Invalidate cache after cleanup
    wanderer_managed_map.invalidate_acl_cache()
    logger.info("Invalidated ACL cache after cleanup")


@shared_task
def cleanup_all_access_lists():
    """
    Periodically cycle through all access lists to clean up unwanted members and add missing alts
    """
    logger.info("Starting a cleanup of all access lists")

    wanderer_managed_maps = WandererManagedMap.objects.all()

    logger.info("%d maps to cleanup", wanderer_managed_maps.count())

    tasks = [
        cleanup_access_list.si(wanderer_managed_map.id)
        for wanderer_managed_map in wanderer_managed_maps
    ]

    chain(tasks).delay()
