import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class WandererServiceConfig(AppConfig):
    name = "wanderer"
    label = "wanderer"
    verbose_name = "wanderer"

    def ready(self):
        """Runs service sync on startup"""
        # needs to be imported after the app is loaded
        from . import signals  # noqa: F401
        from .auth_hooks import add_del_callback

        try:
            add_del_callback()
        except Exception as e:
            logger.warning("WMM failed to initiate hooks: %s", e)
            logger.debug(
                "This is expected if migrations haven't been run yet", exc_info=True
            )
