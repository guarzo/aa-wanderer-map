"""Utility functions for the Wanderer plugin."""

import ipaddress
import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def sanitize_api_key(api_key: Optional[str], visible_chars: int = 4) -> str:
    """
    Sanitize API key for safe logging.

    Args:
        api_key: The API key to sanitize
        visible_chars: Number of characters to show at the end

    Returns:
        Sanitized string showing only last N characters

    Examples:
        >>> sanitize_api_key("abc123def456")
        "***f456"
        >>> sanitize_api_key(None)
        "None"
    """
    if not api_key:
        return "None"
    if len(api_key) <= visible_chars:
        return "*" * len(api_key)
    return f"***{api_key[-visible_chars:]}"


def sanitize_url(url: str) -> str:
    """
    Sanitize URL for safe logging (removes credentials if present).

    Args:
        url: URL to sanitize

    Returns:
        URL with credentials removed
    """
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        # Remove credentials by taking everything after the first '@'
        # This preserves IPv6 brackets and ports
        if "@" in parsed.netloc:
            netloc = parsed.netloc.split("@", 1)[1]
        else:
            netloc = parsed.netloc
        parsed = parsed._replace(netloc=netloc)

    return urlunparse(parsed)


class WandererURLValidator:
    """Validator for Wanderer instance URLs to prevent SSRF attacks."""

    BLOCKED_HOSTS = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "local",
    }

    BLOCKED_NETWORKS = [
        ipaddress.ip_network("10.0.0.0/8"),  # Private network
        ipaddress.ip_network("172.16.0.0/12"),  # Private network
        ipaddress.ip_network("192.168.0.0/16"),  # Private network
        ipaddress.ip_network("127.0.0.0/8"),  # Loopback
        ipaddress.ip_network("169.254.0.0/16"),  # Link-local
        ipaddress.ip_network("::1/128"),  # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),  # IPv6 private
        ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ]

    @classmethod
    def validate(cls, url: str) -> str:
        """
        Validate and normalize a Wanderer URL.

        Args:
            url: The URL to validate

        Returns:
            Normalized URL (stripped of trailing slashes)

        Raises:
            ValidationError: If URL is invalid or blocked
        """
        if not url:
            raise ValidationError("URL cannot be empty")

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValidationError(f"Invalid URL format: {e}") from e

        # Check scheme
        if parsed.scheme not in ("http", "https"):
            raise ValidationError(
                f"Invalid URL scheme '{parsed.scheme}'. "
                "Only http and https are allowed."
            )

        # Check for host
        if not parsed.netloc:
            raise ValidationError("URL must include a hostname")

        # Get hostname without port
        hostname = parsed.hostname
        if not hostname:
            raise ValidationError("Invalid hostname")

        # Check against blocked hosts
        hostname_lower = hostname.lower()
        if hostname_lower in cls.BLOCKED_HOSTS:
            raise ValidationError(
                f"Access to {hostname} is not allowed (security restriction)"
            )

        # Check if hostname is an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            # Check against blocked networks
            for network in cls.BLOCKED_NETWORKS:
                if ip in network:
                    raise ValidationError(
                        f"Access to {hostname} is not allowed "
                        "(private/loopback address)"
                    )
        except ValueError:
            # Not an IP address, that's fine - it's a domain name
            pass

        # Normalize: remove trailing slashes
        normalized_url = url.rstrip("/")

        return normalized_url


def validate_wanderer_url(url: str) -> str:
    """
    Validate a Wanderer URL.

    This is a convenience wrapper around WandererURLValidator.

    Args:
        url: The URL to validate

    Returns:
        Normalized URL

    Raises:
        ValidationError: If URL is invalid
    """
    return WandererURLValidator.validate(url)
