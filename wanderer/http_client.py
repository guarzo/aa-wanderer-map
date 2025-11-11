"""HTTP client for Wanderer API with retry logic."""

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from django.conf import settings

logger = logging.getLogger(__name__)


class WandererHTTPClient:
    """HTTP client configured for Wanderer API with retry logic."""

    # Configuration from Django settings with defaults
    DEFAULT_TIMEOUT = getattr(settings, "WANDERER_API_TIMEOUT", 10)
    LONG_TIMEOUT = getattr(settings, "WANDERER_API_LONG_TIMEOUT", 30)

    # Retry configuration
    RETRY_TOTAL = getattr(settings, "WANDERER_API_RETRY_TOTAL", 3)
    RETRY_BACKOFF_FACTOR = getattr(settings, "WANDERER_API_RETRY_BACKOFF", 0.5)
    RETRY_STATUS_CODES = getattr(
        settings,
        "WANDERER_API_RETRY_STATUS_CODES",
        (500, 502, 503, 504, 429),  # Server errors and rate limiting
    )

    @classmethod
    def get_session(cls) -> requests.Session:
        """
        Get a requests Session configured with retry logic.

        Retry configuration:
        - Total retries: 3
        - Backoff factor: 0.5 (waits 0.5s, 1s, 2s between retries)
        - Retry on: 500, 502, 503, 504, 429 status codes
        - Retry methods: All HTTP methods

        Returns:
            Configured requests.Session
        """
        session = requests.Session()

        retry = Retry(
            total=cls.RETRY_TOTAL,
            backoff_factor=cls.RETRY_BACKOFF_FACTOR,
            status_forcelist=cls.RETRY_STATUS_CODES,
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "POST", "PATCH"],
            raise_on_status=False,  # We handle status codes manually
        )

        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    @classmethod
    def post(cls, url: str, timeout: int | None = None, **kwargs) -> requests.Response:
        """
        POST request with retry logic.

        Args:
            url: URL to request
            timeout: Request timeout (uses DEFAULT_TIMEOUT if not specified)
            **kwargs: Additional arguments passed to requests.post

        Returns:
            Response object
        """
        timeout = timeout or cls.DEFAULT_TIMEOUT
        session = cls.get_session()

        logger.debug("POST %s (timeout: %ss)", url, timeout)

        try:
            response = session.post(url, timeout=timeout, **kwargs)
        except requests.Timeout:
            logger.exception("POST %s timed out after %ss", url, timeout)
            raise
        except requests.RequestException as e:
            logger.exception("POST %s failed: %s", url, e)
            raise

        logger.debug("POST %s -> %s", url, response.status_code)
        return response

    @classmethod
    def get(cls, url: str, timeout: int | None = None, **kwargs) -> requests.Response:
        """
        GET request with retry logic.

        Args:
            url: URL to request
            timeout: Request timeout (uses DEFAULT_TIMEOUT if not specified)
            **kwargs: Additional arguments passed to requests.get

        Returns:
            Response object
        """
        timeout = timeout or cls.DEFAULT_TIMEOUT
        session = cls.get_session()

        logger.debug("GET %s (timeout: %ss)", url, timeout)

        try:
            response = session.get(url, timeout=timeout, **kwargs)
        except requests.Timeout:
            logger.exception("GET %s timed out after %ss", url, timeout)
            raise
        except requests.RequestException as e:
            logger.exception("GET %s failed: %s", url, e)
            raise

        logger.debug("GET %s -> %s", url, response.status_code)
        return response

    @classmethod
    def put(cls, url: str, timeout: int | None = None, **kwargs) -> requests.Response:
        """
        PUT request with retry logic.

        Args:
            url: URL to request
            timeout: Request timeout (uses DEFAULT_TIMEOUT if not specified)
            **kwargs: Additional arguments passed to requests.put

        Returns:
            Response object
        """
        timeout = timeout or cls.DEFAULT_TIMEOUT
        session = cls.get_session()

        logger.debug("PUT %s (timeout: %ss)", url, timeout)

        try:
            response = session.put(url, timeout=timeout, **kwargs)
        except requests.Timeout:
            logger.exception("PUT %s timed out after %ss", url, timeout)
            raise
        except requests.RequestException as e:
            logger.exception("PUT %s failed: %s", url, e)
            raise

        logger.debug("PUT %s -> %s", url, response.status_code)
        return response

    @classmethod
    def delete(
        cls, url: str, timeout: int | None = None, **kwargs
    ) -> requests.Response:
        """
        DELETE request with retry logic.

        Args:
            url: URL to request
            timeout: Request timeout (uses DEFAULT_TIMEOUT if not specified)
            **kwargs: Additional arguments passed to requests.delete

        Returns:
            Response object
        """
        timeout = timeout or cls.DEFAULT_TIMEOUT
        session = cls.get_session()

        logger.debug("DELETE %s (timeout: %ss)", url, timeout)

        try:
            response = session.delete(url, timeout=timeout, **kwargs)
        except requests.Timeout:
            logger.exception("DELETE %s timed out after %ss", url, timeout)
            raise
        except requests.RequestException as e:
            logger.exception("DELETE %s failed: %s", url, e)
            raise

        logger.debug("DELETE %s -> %s", url, response.status_code)
        return response
