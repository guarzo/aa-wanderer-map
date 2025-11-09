from django.core.management import BaseCommand

from allianceauth.services.hooks import get_extension_logger

from wanderer.models import WandererManagedMap
from wanderer.tasks import cleanup_access_list, cleanup_all_access_lists

logger = get_extension_logger(__name__)


class Command(BaseCommand):
    """Cleanup utility for Wanderer ACLs"""

    help = "Runs the cleanup command on all registered access lists or a specific map"

    def add_arguments(self, parser):
        parser.add_argument(
            "--map-id",
            type=int,
            help="Sync only this specific map ID (optional)",
        )

    def handle(self, *args, **options):
        map_id = options.get("map_id")

        if map_id:
            # Sync specific map
            try:
                wmap = WandererManagedMap.objects.get(pk=map_id)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Syncing roles for map: {wmap.name} (ID:{map_id})"
                    )
                )
                cleanup_access_list.delay(wmap.pk)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Cleanup task queued for map '{wmap.name}'")
                )
            except WandererManagedMap.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"✗ Map with ID {map_id} not found"))
                return
        else:
            # Sync all maps
            maps = WandererManagedMap.objects.all()
            count = maps.count()

            if count == 0:
                self.stdout.write(
                    self.style.WARNING("No Wanderer maps found to cleanup")
                )
                return

            self.stdout.write(
                self.style.SUCCESS(f"Syncing roles for {count} map(s)...")
            )
            cleanup_all_access_lists.delay()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Cleanup tasks queued for all {count} map(s)")
            )

        self.stdout.write(
            self.style.NOTICE(
                "\nNote: Tasks are running asynchronously via Celery. "
                "Check logs for progress and results."
            )
        )
