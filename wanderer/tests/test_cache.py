"""Tests for caching functionality."""

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase

from wanderer.cache import WandererCache
from wanderer.tests.utils import create_managed_map
from wanderer.wanderer import AccessListRoles


class TestWandererCache(TestCase):
    def setUp(self):
        """Clear cache before each test"""
        cache.clear()

    def tearDown(self):
        """Clear cache after each test"""
        cache.clear()

    def test_cache_key_generation(self):
        """Test cache key generation"""
        key = WandererCache.get_acl_members_key(123)
        self.assertEqual(key, "wanderer:acl_members:123")

        key = WandererCache.get_non_member_chars_key(456)
        self.assertEqual(key, "wanderer:non_member_chars:456")

        key = WandererCache.get_user_access_key(123, 789)
        self.assertEqual(key, "wanderer:user_access:123:789")

    def test_get_acl_members_cache_miss(self):
        """Test fetching ACL members on cache miss"""
        fetch_func = MagicMock(return_value=[1001, 1002, 1003])

        result = WandererCache.get_acl_members(123, fetch_func)

        self.assertEqual(result, [1001, 1002, 1003])
        fetch_func.assert_called_once()

    def test_get_acl_members_cache_hit(self):
        """Test fetching ACL members on cache hit"""
        # Prime the cache
        cache.set(WandererCache.get_acl_members_key(123), [1001, 1002])

        fetch_func = MagicMock()
        result = WandererCache.get_acl_members(123, fetch_func)

        self.assertEqual(result, [1001, 1002])
        fetch_func.assert_not_called()  # Should not fetch if cached

    def test_get_non_member_chars_cache_miss(self):
        """Test fetching non-member chars on cache miss"""
        expected = [(1001, AccessListRoles.ADMIN), (1002, AccessListRoles.MANAGER)]
        fetch_func = MagicMock(return_value=expected)

        result = WandererCache.get_non_member_chars(123, fetch_func)

        self.assertEqual(result, expected)
        fetch_func.assert_called_once()

    def test_get_non_member_chars_cache_hit(self):
        """Test fetching non-member chars on cache hit"""
        expected = [(1001, AccessListRoles.ADMIN)]
        cache.set(WandererCache.get_non_member_chars_key(123), expected)

        fetch_func = MagicMock()
        result = WandererCache.get_non_member_chars(123, fetch_func)

        self.assertEqual(result, expected)
        fetch_func.assert_not_called()

    def test_invalidate_acl_cache(self):
        """Test ACL cache invalidation"""
        # Prime caches
        cache.set(WandererCache.get_acl_members_key(123), [1001])
        cache.set(
            WandererCache.get_non_member_chars_key(123), [(1002, AccessListRoles.ADMIN)]
        )

        # Invalidate
        WandererCache.invalidate_acl_cache(123)

        # Verify caches are cleared
        self.assertIsNone(cache.get(WandererCache.get_acl_members_key(123)))
        self.assertIsNone(cache.get(WandererCache.get_non_member_chars_key(123)))

    def test_model_get_character_ids_uses_cache(self):
        """Test that model method uses cache"""
        wanderer_map = create_managed_map()

        # Mock the API call
        with patch("wanderer.models.get_acl_member_ids") as mock_api:
            mock_api.return_value = [1001, 1002]

            # First call - should hit API
            result1 = wanderer_map.get_character_ids_on_access_list()
            self.assertEqual(result1, [1001, 1002])
            self.assertEqual(mock_api.call_count, 1)

            # Second call - should use cache
            result2 = wanderer_map.get_character_ids_on_access_list()
            self.assertEqual(result2, [1001, 1002])
            self.assertEqual(mock_api.call_count, 1)  # No additional call

    def test_model_invalidate_acl_cache(self):
        """Test model's cache invalidation method"""
        wanderer_map = create_managed_map()

        # Prime cache
        cache.set(WandererCache.get_acl_members_key(wanderer_map.id), [1001])

        # Invalidate via model method
        wanderer_map.invalidate_acl_cache()

        # Verify cleared
        self.assertIsNone(cache.get(WandererCache.get_acl_members_key(wanderer_map.id)))
