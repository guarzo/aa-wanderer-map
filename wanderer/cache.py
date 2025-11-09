"""Cache management for Wanderer plugin."""

import logging
from typing import Callable, List

from django.core.cache import cache

logger = logging.getLogger(__name__)


class WandererCache:
    """Centralized cache management for Wanderer plugin."""

    # Cache key prefixes
    PREFIX_ACL_MEMBERS = "wanderer:acl_members"
    PREFIX_NON_MEMBER_CHARS = "wanderer:non_member_chars"
    PREFIX_USER_ACCESS = "wanderer:user_access"

    # Cache timeouts (in seconds)
    TIMEOUT_ACL_MEMBERS = 300  # 5 minutes
    TIMEOUT_NON_MEMBER_CHARS = 300  # 5 minutes
    TIMEOUT_USER_ACCESS = 60  # 1 minute

    @classmethod
    def get_acl_members_key(cls, map_id: int) -> str:
        """Get cache key for ACL members."""
        return f"{cls.PREFIX_ACL_MEMBERS}:{map_id}"

    @classmethod
    def get_non_member_chars_key(cls, map_id: int) -> str:
        """Get cache key for non-member characters."""
        return f"{cls.PREFIX_NON_MEMBER_CHARS}:{map_id}"

    @classmethod
    def get_user_access_key(cls, map_id: int, user_id: int) -> str:
        """Get cache key for user access check."""
        return f"{cls.PREFIX_USER_ACCESS}:{map_id}:{user_id}"

    @classmethod
    def get_acl_members(
        cls, map_id: int, fetch_func: Callable[[], List[int]]
    ) -> List[int]:
        """
        Get ACL members from cache or fetch and cache.

        Args:
            map_id: The map ID
            fetch_func: Function to call if cache miss

        Returns:
            List of character IDs on the ACL
        """
        key = cls.get_acl_members_key(map_id)
        members = cache.get(key)

        if members is not None:
            logger.debug("Cache HIT for ACL members (map %s)", map_id)
            return members

        logger.debug("Cache MISS for ACL members (map %s)", map_id)
        members = fetch_func()
        cache.set(key, members, cls.TIMEOUT_ACL_MEMBERS)
        return members

    @classmethod
    def get_non_member_chars(
        cls, map_id: int, fetch_func: Callable[[], List[tuple]]
    ) -> List[tuple]:
        """
        Get non-member characters from cache or fetch and cache.

        Args:
            map_id: The map ID
            fetch_func: Function to call if cache miss

        Returns:
            List of (character_id, role) tuples
        """
        key = cls.get_non_member_chars_key(map_id)
        chars = cache.get(key)

        if chars is not None:
            logger.debug("Cache HIT for non-member chars (map %s)", map_id)
            return chars

        logger.debug("Cache MISS for non-member chars (map %s)", map_id)
        chars = fetch_func()
        cache.set(key, chars, cls.TIMEOUT_NON_MEMBER_CHARS)
        return chars

    @classmethod
    def invalidate_acl_cache(cls, map_id: int) -> None:
        """
        Invalidate all ACL-related cache for a map.

        Call this whenever the ACL is modified.

        Args:
            map_id: The map ID
        """
        keys_to_delete = [
            cls.get_acl_members_key(map_id),
            cls.get_non_member_chars_key(map_id),
        ]

        for key in keys_to_delete:
            cache.delete(key)

        # Also invalidate user access cache for this map
        # Note: We use pattern deletion if supported by cache backend
        try:
            # This works with Redis cache backend
            cache.delete_pattern(f"{cls.PREFIX_USER_ACCESS}:{map_id}:*")
        except AttributeError:
            # Fallback: cache backend doesn't support patterns
            # User access cache will expire naturally
            pass

        logger.info("Invalidated ACL cache for map %s", map_id)

    @classmethod
    def get_user_access(
        cls, map_id: int, user_id: int, check_func: Callable[[], bool]
    ) -> bool:
        """
        Get user access status from cache or check and cache.

        Args:
            map_id: The map ID
            user_id: The user ID
            check_func: Function to call if cache miss

        Returns:
            True if user has access, False otherwise
        """
        key = cls.get_user_access_key(map_id, user_id)
        access = cache.get(key)

        if access is not None:
            logger.debug("Cache HIT for user access (map %s, user %s)", map_id, user_id)
            return access

        logger.debug("Cache MISS for user access (map %s, user %s)", map_id, user_id)
        access = check_func()
        cache.set(key, access, cls.TIMEOUT_USER_ACCESS)
        return access

    @classmethod
    def invalidate_user_access(cls, map_id: int, user_id: int) -> None:
        """
        Invalidate user access cache.

        Args:
            map_id: The map ID
            user_id: The user ID
        """
        key = cls.get_user_access_key(map_id, user_id)
        cache.delete(key)
        logger.debug("Invalidated user access cache (map %s, user %s)", map_id, user_id)

    @classmethod
    def clear_all(cls) -> None:
        """Clear all Wanderer caches. Use with caution."""
        try:
            cache.delete_pattern("wanderer:*")
            logger.warning("Cleared ALL Wanderer caches")
        except AttributeError:
            # Fallback: clear the entire cache (not recommended for production)
            cache.clear()
            logger.warning(
                "Cache backend doesn't support pattern deletion; "
                "cleared ENTIRE cache (not just Wanderer keys) to remove stale data"
            )
