# Generated manually for Phase 1 implementation

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("wanderer", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="wanderermanagedmap",
            name="admin_users",
            field=models.ManyToManyField(
                blank=True,
                help_text="Users who should be granted admin role on this map's ACL",
                related_name="wanderer_admin_maps",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="wanderermanagedmap",
            name="admin_groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="Groups whose members should be granted admin role on this map's ACL",
                related_name="wanderer_admin_maps",
                to="auth.group",
            ),
        ),
        migrations.AddField(
            model_name="wanderermanagedmap",
            name="manager_users",
            field=models.ManyToManyField(
                blank=True,
                help_text="Users who should be granted manager role on this map's ACL",
                related_name="wanderer_manager_maps",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="wanderermanagedmap",
            name="manager_groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="Groups whose members should be granted manager role on this map's ACL",
                related_name="wanderer_manager_maps",
                to="auth.group",
            ),
        ),
    ]
