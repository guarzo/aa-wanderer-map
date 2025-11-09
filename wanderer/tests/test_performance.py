"""Performance tests for wanderer."""

from django.contrib.auth.models import Group, User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from wanderer.tests.utils import create_managed_map, create_wanderer_users


class TestQueryPerformance(TestCase):
    """Test database query performance to catch N+1 issues."""

    def setUp(self):
        """Set up test data"""
        self.wanderer_map = create_managed_map()
        self.users = create_wanderer_users(self.wanderer_map, count=5)

    def test_get_admin_character_ids_query_count(self):
        """Test that getting admin character IDs doesn't have N+1 queries"""
        # Add some admin users and groups
        admin_group = Group.objects.create(name="Admins")

        # Add users to admin assignments
        for user_account in self.users[:3]:
            self.wanderer_map.admin_users.add(user_account.user)

        # Add group
        self.wanderer_map.admin_groups.add(admin_group)
        for user_account in self.users[3:]:
            user_account.user.groups.add(admin_group)

        # Measure queries
        with CaptureQueriesContext(connection) as context:
            character_ids = self.wanderer_map.get_admin_character_ids()

        # Should be constant number of queries regardless of number of users
        # Expected queries:
        # 1. Get user IDs from admin_users
        # 2. Get user IDs from admin_groups members
        # 3. Get all characters for all users
        # 4. Get user info for logging (if any users without chars)
        self.assertLessEqual(
            len(context.captured_queries),
            5,
            f"Too many queries ({len(context.captured_queries)}). "
            f"Possible N+1 problem. Queries: {context.captured_queries}",
        )

        # Verify we got the right number of characters
        # 5 users * 2 characters each = 10 characters
        self.assertEqual(len(character_ids), 10)

    def test_get_manager_character_ids_query_count(self):
        """Test that getting manager character IDs doesn't have N+1 queries"""
        manager_group = Group.objects.create(name="Managers")

        for user_account in self.users[:2]:
            self.wanderer_map.manager_users.add(user_account.user)

        self.wanderer_map.manager_groups.add(manager_group)
        for user_account in self.users[2:]:
            user_account.user.groups.add(manager_group)

        with CaptureQueriesContext(connection) as context:
            character_ids = self.wanderer_map.get_manager_character_ids()

        self.assertLessEqual(
            len(context.captured_queries),
            5,
            f"Too many queries ({len(context.captured_queries)})",
        )

        self.assertEqual(len(character_ids), 10)

    def test_query_count_with_many_users(self):
        """Test query count scales well with many users"""
        # Create more users
        for i in range(10, 20):
            user = User.objects.create(username=f"user_{i}")
            self.wanderer_map.admin_users.add(user)

        with CaptureQueriesContext(connection) as context:
            self.wanderer_map.get_admin_character_ids()

        # Query count should remain constant
        self.assertLessEqual(len(context.captured_queries), 5)
