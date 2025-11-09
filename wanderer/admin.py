"""Admin site."""

from django.contrib import admin, messages

from wanderer.forms import WandererManagedMapAdminForm
from wanderer.models import WandererAccount, WandererManagedMap
from wanderer.wanderer import create_acl_associated_to_map


@admin.register(WandererManagedMap)
class WandererManagedMapAdmin(admin.ModelAdmin):
    form = WandererManagedMapAdminForm
    list_display = ("name", "wanderer_url", "map_slug")
    actions = ["sync_acl_roles"]

    fieldsets = [
        (None, {"fields": ["name", "wanderer_url", "map_slug", "map_api_key"]}),
        (
            "Access List Selection",
            {
                "fields": ["acl_selection", "existing_acl_api_key"],
                "description": "Choose to use an existing ACL or create a new one managed by Alliance Auth. "
                "If selecting an existing ACL, you must provide its API key from Wanderer.",
            },
        ),
        ("Access List", {"fields": ["map_acl_id", "map_acl_api_key"]}),
        (
            "Member Access",
            {
                "fields": [
                    "state_access",
                    "group_access",
                    "character_access",
                    "corporation_access",
                    "alliance_access",
                    "faction_access",
                ],
                "description": "Users matching these criteria can link to the map and will be added as members.",
            },
        ),
        (
            "Admin Roles",
            {
                "fields": [
                    "admin_users",
                    "admin_groups",
                ],
                "description": "Users/groups who should have admin role on the map's ACL. "
                "All their characters (main + alts) will be promoted to admin.",
            },
        ),
        (
            "Manager Roles",
            {
                "fields": [
                    "manager_users",
                    "manager_groups",
                ],
                "description": "Users/groups who should have manager role on the map's ACL. "
                "All their characters (main + alts) will be promoted to manager.",
            },
        ),
    ]

    readonly_fields = ("map_acl_id", "map_acl_api_key")

    filter_horizontal = (
        # Existing
        "state_access",
        "group_access",
        "character_access",
        "corporation_access",
        "alliance_access",
        "faction_access",
        # NEW
        "admin_users",
        "admin_groups",
        "manager_users",
        "manager_groups",
    )

    def get_fieldsets(self, request, obj=None):
        """
        Hide ACL selection fieldset when editing existing map.
        """
        fieldsets = super().get_fieldsets(request, obj)

        if obj:  # Editing existing object
            # Remove "Access List Selection" fieldset
            return [fs for fs in fieldsets if fs[0] != "Access List Selection"]

        return fieldsets

    def save_model(self, request, obj, form, change):
        if not change:  # Only on creation
            acl_selection = form.cleaned_data.get("acl_selection", "__CREATE_NEW__")

            if acl_selection == "__CREATE_NEW__":
                # Create new ACL
                try:
                    character_id = request.user.profile.main_character.character_id
                except (AttributeError, TypeError):
                    messages.error(
                        request,
                        "Cannot create ACL: You must have a main character set.",
                    )
                    return

                acl_id, acl_key = create_acl_associated_to_map(
                    obj.wanderer_url,
                    obj.map_slug,
                    character_id,
                    obj.map_api_key,
                )
                obj.map_acl_id = acl_id
                obj.map_acl_api_key = acl_key

                messages.success(request, f"Created new ACL: {acl_id}")
            else:
                # Use existing ACL
                # acl_selection now contains just the ACL ID
                acl_id = acl_selection
                acl_key = form.cleaned_data.get("existing_acl_api_key")

                obj.map_acl_id = acl_id
                obj.map_acl_api_key = acl_key

                messages.info(
                    request,
                    f"Using existing ACL: {acl_id}. "
                    "Note: Alliance Auth will manage this ACL going forward. "
                    "Manual changes may be overwritten.",
                )

        super().save_model(request, obj, form, change)

    @admin.action(description="Sync ACL roles now (queues cleanup task)")
    def sync_acl_roles(self, request, queryset):
        """Admin action to immediately sync ACL roles for selected maps"""
        from .tasks import cleanup_access_list

        count = queryset.count()

        for wmap in queryset:
            cleanup_access_list.delay(wmap.pk)

        self.message_user(
            request,
            f"Queued role sync for {count} map(s). Tasks are running asynchronously via Celery. "
            f"Check logs for progress and results.",
            messages.SUCCESS,
        )


@admin.register(WandererAccount)
class WandererUserAdmin(admin.ModelAdmin):
    list_filter = ["wanderer_map"]
    list_display = ["user", "wanderer_map"]
    readonly_fields = ["user", "wanderer_map"]

    def has_add_permission(self, request):
        return False
