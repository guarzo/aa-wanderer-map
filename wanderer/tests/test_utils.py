"""Tests for utility functions."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from wanderer.utils import (
    WandererURLValidator,
    sanitize_api_key,
    sanitize_url,
    validate_wanderer_url,
)


class TestSanitizeApiKey(TestCase):
    """Tests for sanitize_api_key function."""

    def test_sanitize_api_key_full_length(self):
        """Test sanitizing a normal API key"""
        key = "key_for_testing_value_12345"
        result = sanitize_api_key(key)
        self.assertEqual(result, "***2345")
        self.assertNotIn("key_for_testing_value", result)

    def test_sanitize_api_key_short(self):
        """Test sanitizing a short API key"""
        key = "abc"
        result = sanitize_api_key(key)
        self.assertEqual(result, "***")

    def test_sanitize_api_key_none(self):
        """Test sanitizing None"""
        result = sanitize_api_key(None)
        self.assertEqual(result, "None")

    def test_sanitize_api_key_empty(self):
        """Test sanitizing empty string"""
        result = sanitize_api_key("")
        self.assertEqual(result, "None")

    def test_sanitize_api_key_custom_visible(self):
        """Test custom visible characters"""
        key = "key_for_testing_visible_foobar"
        result = sanitize_api_key(key, visible_chars=6)
        self.assertEqual(result, "***foobar")


class TestSanitizeUrl(TestCase):
    """Tests for sanitize_url function."""

    def test_sanitize_url_no_credentials(self):
        """Test URL without credentials"""
        url = "https://wanderer.example.com/api"
        result = sanitize_url(url)
        self.assertEqual(result, url)

    def test_sanitize_url_with_credentials(self):
        """Test URL with credentials are removed"""
        url = "https://user:pass@wanderer.example.com/api"
        result = sanitize_url(url)
        self.assertEqual(result, "https://wanderer.example.com/api")
        self.assertNotIn("user", result)
        self.assertNotIn("pass", result)


class TestWandererURLValidator(TestCase):
    """Tests for WandererURLValidator class."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL"""
        url = "https://wanderer.example.com"
        result = WandererURLValidator.validate(url)
        self.assertEqual(result, "https://wanderer.example.com")

    def test_valid_http_url(self):
        """Test valid HTTP URL"""
        url = "http://wanderer.example.com"
        result = WandererURLValidator.validate(url)
        self.assertEqual(result, "http://wanderer.example.com")

    def test_trailing_slash_removed(self):
        """Test trailing slashes are removed"""
        url = "https://wanderer.example.com/"
        result = WandererURLValidator.validate(url)
        self.assertEqual(result, "https://wanderer.example.com")

    def test_url_with_port(self):
        """Test URL with custom port"""
        url = "https://wanderer.example.com:8443"
        result = WandererURLValidator.validate(url)
        self.assertEqual(result, "https://wanderer.example.com:8443")

    def test_url_with_path(self):
        """Test URL with path"""
        url = "https://wanderer.example.com/maps"
        result = WandererURLValidator.validate(url)
        self.assertEqual(result, "https://wanderer.example.com/maps")

    def test_invalid_scheme(self):
        """Test invalid scheme is rejected"""
        with self.assertRaises(ValidationError) as cm:
            WandererURLValidator.validate("ftp://wanderer.example.com")
        self.assertIn("Invalid URL scheme", str(cm.exception))

    def test_localhost_blocked(self):
        """Test localhost is blocked"""
        with self.assertRaises(ValidationError) as cm:
            WandererURLValidator.validate("http://localhost:8000")
        self.assertIn("not allowed", str(cm.exception))

    def test_127_0_0_1_blocked(self):
        """Test 127.0.0.1 is blocked"""
        with self.assertRaises(ValidationError) as cm:
            WandererURLValidator.validate("http://127.0.0.1:8000")
        self.assertIn("not allowed", str(cm.exception))

    def test_private_network_blocked(self):
        """Test private network IPs are blocked"""
        blocked_ips = [
            "http://10.0.0.1",
            "http://172.16.0.1",
            "http://192.168.1.1",
        ]
        for url in blocked_ips:
            with self.assertRaises(ValidationError):
                WandererURLValidator.validate(url)

    def test_ipv6_loopback_blocked(self):
        """Test IPv6 loopback is blocked"""
        with self.assertRaises(ValidationError) as cm:
            WandererURLValidator.validate("http://[::1]:8000")
        self.assertIn("not allowed", str(cm.exception))

    def test_empty_url(self):
        """Test empty URL is rejected"""
        with self.assertRaises(ValidationError):
            WandererURLValidator.validate("")

    def test_no_hostname(self):
        """Test URL without hostname is rejected"""
        with self.assertRaises(ValidationError):
            WandererURLValidator.validate("http://")

    def test_public_ip_allowed(self):
        """Test public IP addresses are allowed"""
        url = "http://8.8.8.8"  # Google DNS - definitely public
        result = WandererURLValidator.validate(url)
        self.assertEqual(result, "http://8.8.8.8")

    def test_validate_wanderer_url_wrapper(self):
        """Test convenience wrapper function"""
        url = "https://wanderer.example.com/"
        result = validate_wanderer_url(url)
        self.assertEqual(result, "https://wanderer.example.com")
