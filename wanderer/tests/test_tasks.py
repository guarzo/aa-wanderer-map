"""Tasks tests"""

from unittest.mock import MagicMock, call

from django.test import TestCase

from wanderer.models import WandererAccount, WandererManagedMap
from wanderer.tasks import (
    add_alts_to_map,
    cleanup_access_list,
    remove_user_characters_from_map,
)

from ..wanderer import AccessListRoles
from .utils import create_managed_map, create_wanderer_users


class TestTasks(TestCase):

    def test_add_character_to_acl(self):
        """Checks that characters properly get added to the access list"""
        WandererManagedMap.get_character_ids_on_access_list = MagicMock(
            return_value=[1001, 1002]
        )  # Creating fake ids to be returned
        WandererManagedMap.add_character_to_acl = MagicMock()
        WandererManagedMap.get_character_role = MagicMock(
            return_value=AccessListRoles.MEMBER
        )
        WandererAccount.get_all_character_ids = MagicMock(
            return_value=[1001, 1003]
        )  # Missing id 1003

        wanderer_map = create_managed_map()
        user = create_wanderer_users(wanderer_map)[0]

        add_alts_to_map(user.id, wanderer_map.id)

        WandererManagedMap.get_character_ids_on_access_list.assert_called_once()
        WandererManagedMap.add_character_to_acl.assert_called_once_with(
            1003, role=AccessListRoles.MEMBER
        )
        WandererAccount.get_all_character_ids.assert_called_once()

    def test_remove_user_characters_from_acl(self):
        WandererManagedMap.get_character_ids_on_access_list = MagicMock(
            return_value=[1001, 1002, 1003]
        )
        WandererManagedMap.remove_member_from_access_list = MagicMock()
        WandererAccount.get_all_character_ids = MagicMock(return_value=[1001, 1002])

        wanderer_map = create_managed_map()
        user = create_wanderer_users(wanderer_map)[0]

        remove_user_characters_from_map(user.id, wanderer_map.id)

        WandererManagedMap.get_character_ids_on_access_list.assert_called_once()
        WandererAccount.get_all_character_ids.assert_called_once()

        remove_member_calls = [call(1001), call(1002)]
        WandererManagedMap.remove_member_from_access_list.assert_has_calls(
            remove_member_calls, any_order=True
        )

    def test_cleanup_access_list(self):
        from unittest.mock import patch

        # Characters on ACL include 1030 and 1031 who have non-member roles
        WandererManagedMap.get_character_ids_on_access_list = MagicMock(
            return_value=[1000, 1011, 1020, 1030, 1031]
        )
        WandererManagedMap.remove_member_from_access_list = MagicMock()
        WandererManagedMap.add_character_to_acl = MagicMock()
        WandererManagedMap.get_character_role = MagicMock(
            return_value=AccessListRoles.MEMBER
        )
        WandererManagedMap.get_admin_character_ids = MagicMock(return_value=set())
        WandererManagedMap.get_manager_character_ids = MagicMock(return_value=set())
        WandererManagedMap.get_non_member_characters = MagicMock(
            return_value=[
                (1030, AccessListRoles.VIEWER),
                (1031, AccessListRoles.BLOCKED),
            ]
        )
        WandererManagedMap.set_character_to_member = MagicMock()

        wanderer_map = create_managed_map()
        # create_wanderer_users creates users with character IDs: 1000, 1001, 1010, 1011
        # So get_all_accounts_characters_ids will return: [1000, 1001, 1010, 1011, 1030, 1031]
        # But we'll mock it to only return the authorized ones plus 1030, 1031
        WandererManagedMap.get_all_accounts_characters_ids = MagicMock(
            return_value=[1000, 1001, 1010, 1011, 1030, 1031]
        )
        create_wanderer_users(wanderer_map, 2)

        # Mock the get_member_role and update_character_role functions to avoid API calls
        with patch("wanderer.tasks.get_member_role") as mock_get_member_role:
            with patch("wanderer.tasks.update_character_role"):
                # Return matching roles for existing characters so no updates needed
                mock_get_member_role.return_value = AccessListRoles.MEMBER

                cleanup_access_list(wanderer_map.id)

                WandererManagedMap.get_character_ids_on_access_list.assert_called_once()
                # 1020 should be removed (not in authorized list)
                WandererManagedMap.remove_member_from_access_list.assert_called_once_with(
                    1020
                )
                # 1001 and 1010 should be added (authorized but not on ACL yet)
                add_character_calls = [
                    call(1001, role=AccessListRoles.MEMBER),
                    call(1010, role=AccessListRoles.MEMBER),
                ]
                WandererManagedMap.add_character_to_acl.assert_has_calls(
                    add_character_calls, any_order=True
                )
                WandererManagedMap.get_non_member_characters.assert_called_once()
                # 1030 (VIEWER) and 1031 (BLOCKED) should be demoted to member
                set_character_to_member_calls = [call(1030), call(1031)]
                WandererManagedMap.set_character_to_member.assert_has_calls(
                    set_character_to_member_calls, any_order=True
                )

    def test_dont_cleanup_access_list(self):
        """Test where the access list is correct and has different roles than member"""
        WandererManagedMap.get_character_ids_on_access_list = MagicMock(
            return_value=[1000, 1001, 1010, 1011]
        )
        WandererManagedMap.get_all_accounts_characters_ids = MagicMock(
            return_value=[1000, 1001, 1010, 1011]
        )
        WandererManagedMap.add_character_to_acl = MagicMock()
        WandererManagedMap.remove_member_from_access_list = MagicMock()
        WandererManagedMap.get_admin_character_ids = MagicMock(return_value={1000})
        WandererManagedMap.get_manager_character_ids = MagicMock(return_value={1001})
        WandererManagedMap.get_character_role = MagicMock(
            side_effect=lambda char_id: (
                AccessListRoles.ADMIN
                if char_id == 1000
                else (
                    AccessListRoles.MANAGER
                    if char_id == 1001
                    else AccessListRoles.MEMBER
                )
            )
        )
        WandererManagedMap.get_non_member_characters = MagicMock(
            return_value=[
                (1000, AccessListRoles.ADMIN),
                (1001, AccessListRoles.MANAGER),
            ]
        )
        WandererManagedMap.set_character_to_member = MagicMock()

        # Import get_member_role to mock it
        from unittest.mock import patch

        with patch("wanderer.tasks.get_member_role") as mock_get_member_role:
            # Return current role that matches expected role
            mock_get_member_role.side_effect = lambda url, acl_id, api_key, char_id: (
                AccessListRoles.ADMIN
                if char_id == 1000
                else (
                    AccessListRoles.MANAGER
                    if char_id == 1001
                    else AccessListRoles.MEMBER
                )
            )

            wanderer_map = create_managed_map()
            create_wanderer_users(wanderer_map, 2)

            cleanup_access_list(wanderer_map.id)

            WandererManagedMap.get_character_ids_on_access_list.assert_called_once()
            WandererManagedMap.get_all_accounts_characters_ids.assert_called_once()
            WandererManagedMap.add_character_to_acl.assert_not_called()
            WandererManagedMap.remove_member_from_access_list.assert_not_called()
            WandererManagedMap.get_non_member_characters.assert_called_once()
            WandererManagedMap.set_character_to_member.assert_not_called()
