"""Models."""

from typing import Optional

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.translation import gettext_lazy as _

from allianceauth.authentication.models import State
from allianceauth.eveonline.models import (
    EveAllianceInfo,
    EveCharacter,
    EveCorporationInfo,
    EveFactionInfo,
)
from allianceauth.framework.api.user import get_all_characters_from_user
from allianceauth.services.hooks import get_extension_logger

from wanderer.cache import WandererCache
from wanderer.managers import WandererManagedMapManager
from wanderer.utils import validate_wanderer_url
from wanderer.wanderer import (
    AccessListRoles,
    NotFoundError,
    add_character_to_acl,
    get_acl_member_ids,
    get_non_member_characters,
    remove_member_from_access_list,
    set_character_to_member,
)

logger = get_extension_logger(__name__)


class General(models.Model):
    """A metamodel for app permissions."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (("basic_access", "Can access this app"),)


class WandererManagedMap(models.Model):
    """Wanderer map with an ACL managed by the auth"""

    objects = WandererManagedMapManager()

    name = models.CharField(
        max_length=80,
        help_text=_("User friendly name for your users to recognize the map"),
    )
    wanderer_url = models.CharField(
        max_length=120,
        help_text=_("URL of the wanderer instance"),
        validators=[validate_wanderer_url],
    )
    map_slug = models.CharField(
        max_length=20, help_text=_("Map slug on the wanderer instance")
    )
    map_api_key = models.CharField(max_length=100, help_text=_("API key of the map"))

    map_acl_id = models.CharField(
        max_length=100, help_text=_("ID of the managed access list")
    )
    map_acl_api_key = models.CharField(
        max_length=100, help_text=_("API key of the managed access list")
    )

    state_access = models.ManyToManyField(
        State, blank=True, help_text=_("States to whose members this map is available.")
    )

    group_access = models.ManyToManyField(
        Group, blank=True, help_text=_("Groups to whose members this map is available.")
    )

    character_access = models.ManyToManyField(
        EveCharacter,
        blank=True,
        help_text=_("Characters to which this map is available."),
    )

    corporation_access = models.ManyToManyField(
        EveCorporationInfo,
        blank=True,
        help_text=_("Corporations to whose members this map is available."),
    )

    alliance_access = models.ManyToManyField(
        EveAllianceInfo,
        blank=True,
        help_text=_("Alliances to whose members this map is available."),
    )

    faction_access = models.ManyToManyField(
        EveFactionInfo,
        blank=True,
        help_text=_("Factions to whose members this map is available."),
    )

    # Admin Access - users/groups who should have admin role on the ACL
    admin_users = models.ManyToManyField(
        User,
        blank=True,
        related_name="wanderer_admin_maps",
        help_text=_("Users who should be granted admin role on this map's ACL"),
    )

    admin_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="wanderer_admin_maps",
        help_text=_(
            "Groups whose members should be granted admin role on this map's ACL"
        ),
    )

    # Manager Access - users/groups who should have manager role on the ACL
    manager_users = models.ManyToManyField(
        User,
        blank=True,
        related_name="wanderer_manager_maps",
        help_text=_("Users who should be granted manager role on this map's ACL"),
    )

    manager_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="wanderer_manager_maps",
        help_text=_(
            "Groups whose members should be granted manager role on this map's ACL"
        ),
    )

    def __str__(self):
        return f"{self.wanderer_url}/{self.map_slug}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["wanderer_url", "map_slug"], name="functional_pk_urlslug"
            )
        ]
        indexes = [
            models.Index(fields=["map_acl_id"], name="wanderer_map_acl_id_idx"),
            models.Index(fields=["map_slug"], name="wanderer_map_slug_idx"),
        ]

    def accessible_by(self, user: User) -> bool:
        """Defines if a user can access this map or not"""

        logger.debug("Checking if user %s can access the map %s", user, self.name)

        if not user.has_perm("wanderer.basic_access"):
            return False

        try:
            main_character: EveCharacter = user.profile.main_character
            assert main_character

            if user.is_superuser:
                logger.info("Returning all servers to user %s", user)
                return True

            # build queries then OR them all
            queries = []

            # States access everyone has a state
            queries.append(models.Q(state_access=user.profile.state))
            # Groups access, is ok if no groups.
            queries.append(models.Q(group_access__in=user.groups.all()))
            # ONLY on main char from here down
            # Character access
            queries.append(models.Q(character_access=main_character))
            # Corp access
            try:
                queries.append(
                    models.Q(
                        corporation_access=EveCorporationInfo.objects.get(
                            corporation_id=main_character.corporation_id
                        )
                    )
                )
            except EveCorporationInfo.DoesNotExist:
                pass
            # Alliance access if part of an alliance
            try:
                if main_character.alliance_id:
                    queries.append(
                        models.Q(
                            alliance_access=EveAllianceInfo.objects.get(
                                alliance_id=main_character.alliance_id
                            )
                        )
                    )
            except EveAllianceInfo.DoesNotExist:
                pass
            # Faction access if part of a faction
            try:
                if main_character.faction_id:
                    queries.append(
                        models.Q(
                            faction_access=EveFactionInfo.objects.get(
                                faction_id=main_character.faction_id
                            )
                        )
                    )
            except EveFactionInfo.DoesNotExist:
                pass

            logger.debug(
                "%d queries for %s 's visible characters", len(queries), main_character
            )

            if settings.DEBUG:
                logger.debug(queries)

            # filter based on "OR" all queries
            query = queries.pop()
            for q in queries:
                query |= q
            return WandererManagedMap.objects.filter(query, id=self.id).exists()

        except AssertionError:
            logger.info("User %s without eve character can't access maps", user)
            return False

    def user_has_account(self, user: User) -> bool:
        """Return true if the user has an active account on this map"""
        return WandererAccount.objects.filter(user=user, wanderer_map=self).exists()

    def get_user_account(self, user: User) -> Optional["WandererAccount"]:
        """Returns the user account associated to this map if it exists"""
        try:
            return WandererAccount.objects.get(user=user, wanderer_map=self)
        except WandererAccount.DoesNotExist:
            return None

    def delete_user(self, user: User):
        """Removes the user characters from the map and then deletes the associated account"""
        wanderer_account = self.get_user_account(user)
        for character_to_remove_id in wanderer_account.get_all_character_ids():
            try:
                self.remove_member_from_access_list(character_to_remove_id)
            except (
                NotFoundError
            ):  # If the character is already off the access list we're good
                pass
        wanderer_account.delete()

    def get_character_ids_on_access_list(self) -> list[int]:
        """
        Returns all character_ids present on the access list.

        Cached for 5 minutes to reduce API calls.
        """
        return WandererCache.get_acl_members(
            self.id,
            lambda: get_acl_member_ids(
                self.wanderer_url, self.map_acl_id, self.map_acl_api_key
            ),
        )

    def add_character_to_acl(
        self, character_id: int, role: AccessListRoles = AccessListRoles.MEMBER
    ):
        """Adds a single character to the ACL with specified role (defaults to MEMBER)"""
        return add_character_to_acl(
            self.wanderer_url, self.map_acl_id, self.map_acl_api_key, character_id, role
        )

    def remove_member_from_access_list(self, member_id: int):
        """
        Removes a member from the access list.
        member_id can be character/corporation/alliance.
        """

        return remove_member_from_access_list(
            self.wanderer_url, self.map_acl_id, self.map_acl_api_key, member_id
        )

    def get_all_accounts_characters_ids(self) -> list[int]:
        """
        Returns a list of all character ids of accounts linked to this map
        """
        return list(
            self.accounts.values_list(
                "user__character_ownerships__character__character_id", flat=True
            )
        )

    def get_non_member_characters(self) -> list[(int, AccessListRoles)]:
        """
        Return a list of all character ids and roles that are not set as members.

        Cached for 5 minutes to reduce API calls.
        """
        return WandererCache.get_non_member_chars(
            self.id,
            lambda: get_non_member_characters(
                self.wanderer_url, self.map_acl_id, self.map_acl_api_key
            ),
        )

    def set_character_to_member(self, character_id: int):
        """
        Sets the given character id to member on the access list
        """
        set_character_to_member(
            self.wanderer_url, self.map_acl_id, self.map_acl_api_key, character_id
        )

    def _get_role_character_ids(self, users_qs, groups_qs, role_name: str) -> set[int]:
        """
        Helper method to collect character IDs from user and group relationships.

        OPTIMIZED: Uses bulk queries to avoid N+1 problem.

        Args:
            users_qs: QuerySet or related manager for users assigned the role
            groups_qs: QuerySet or related manager for groups assigned the role
            role_name: Name of the role (e.g., 'admin', 'manager') for logging

        Returns:
            Set of character IDs for all characters owned by assigned users
        """
        character_ids = set()

        # Get all user IDs from users_qs in a single query
        user_ids_from_users = list(users_qs.values_list("id", flat=True))

        # Get all user IDs from group members in a single query
        user_ids_from_groups = list(
            User.objects.filter(groups__in=groups_qs.all())
            .distinct()
            .values_list("id", flat=True)
        )

        # Combine all user IDs
        all_user_ids = set(user_ids_from_users) | set(user_ids_from_groups)

        if not all_user_ids:
            logger.debug(
                "No users assigned as %s for map '%s'",
                role_name,
                self.name,
            )
            return character_ids

        # Single query to get ALL characters for ALL users
        characters = EveCharacter.objects.filter(
            character_ownership__user_id__in=all_user_ids
        ).values_list("character_id", "character_ownership__user_id")

        # Track users without characters for logging
        users_with_chars = set()

        for char_id, user_id in characters:
            character_ids.add(char_id)
            users_with_chars.add(user_id)

        # Log warnings for users without characters
        users_without_chars = all_user_ids - users_with_chars
        if users_without_chars:
            # Get usernames in a single query for better logging
            users_info = User.objects.filter(id__in=users_without_chars).values_list(
                "id", "username"
            )
            for user_id, username in users_info:
                logger.warning(
                    "User %s (ID: %d) is assigned as %s for map '%s' but has no characters",
                    username,
                    user_id,
                    role_name,
                    self.name,
                )

        logger.debug(
            "Found %d characters for %d users with %s role on map '%s'",
            len(character_ids),
            len(all_user_ids),
            role_name,
            self.name,
        )

        return character_ids

    def get_admin_character_ids(self) -> set[int]:
        """
        Returns set of character IDs that should have admin role.
        Includes ALL characters (main + alts) from admin_users and all users in admin_groups.
        """
        return self._get_role_character_ids(
            self.admin_users, self.admin_groups, "admin"
        )

    def get_manager_character_ids(self) -> set[int]:
        """
        Returns set of character IDs that should have manager role.
        Includes ALL characters (main + alts) from manager_users and all users in manager_groups.
        """
        return self._get_role_character_ids(
            self.manager_users, self.manager_groups, "manager"
        )

    def invalidate_acl_cache(self):
        """Invalidate cached ACL data for this map."""
        WandererCache.invalidate_acl_cache(self.id)

    def invalidate_user_access_cache(self, user):
        """Invalidate user access cache for this map."""
        WandererCache.invalidate_user_access(self.id, user.id)

    def get_character_role(self, character_id: int) -> AccessListRoles:
        """
        Determine what role a character should have on the ACL.
        Returns: AccessListRoles enum value (ADMIN, MANAGER, or MEMBER)

        Priority order: ADMIN > MANAGER > MEMBER
        """
        admin_chars = self.get_admin_character_ids()
        manager_chars = self.get_manager_character_ids()

        if character_id in admin_chars:
            return AccessListRoles.ADMIN
        if character_id in manager_chars:
            return AccessListRoles.MANAGER
        return AccessListRoles.MEMBER


class WandererAccount(models.Model):
    """Represents a user linked to a wanderer map"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, help_text=_("Auth user linked to the map")
    )
    wanderer_map = models.ForeignKey(
        WandererManagedMap,
        models.CASCADE,
        related_name="accounts",
        related_query_name="account",
        help_text=_("Wanderer map to which the user is linked"),
    )

    def __str__(self):
        return f"{self.user} - {self.wanderer_map}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "wanderer_map"], name="functional_pk_user_map"
            )
        ]

    def get_all_character_ids(self) -> list[int]:
        """Return all character ids associated to this account"""
        return [
            character.character_id
            for character in get_all_characters_from_user(self.user)
        ]
