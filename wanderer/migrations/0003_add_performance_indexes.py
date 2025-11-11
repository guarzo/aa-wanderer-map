# Generated for Phase 8 implementation - Performance optimizations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wanderer", "0002_add_admin_manager_fields"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="wanderermanagedmap",
            index=models.Index(fields=["map_acl_id"], name="wanderer_map_acl_id_idx"),
        ),
        migrations.AddIndex(
            model_name="wanderermanagedmap",
            index=models.Index(fields=["map_slug"], name="wanderer_map_slug_idx"),
        ),
    ]
