"""Forms for wanderer admin interface."""

import logging

import requests

from django import forms
from django.core.exceptions import ValidationError

from wanderer.models import WandererManagedMap
from wanderer.utils import validate_wanderer_url
from wanderer.wanderer import BadAPIKeyError, get_map_acls

logger = logging.getLogger(__name__)


class WandererManagedMapAdminForm(forms.ModelForm):
    """
    Custom form for WandererManagedMap that allows selecting existing ACL
    or creating a new one.
    """

    acl_selection = forms.ChoiceField(
        required=False,
        label="Access Control List",
        help_text="Select an existing ACL or create a new one",
        widget=forms.RadioSelect,
    )

    existing_acl_api_key = forms.CharField(
        required=False,
        label="Existing ACL API Key",
        max_length=100,
        help_text="If using an existing ACL, enter its API key (found in Wanderer's ACL edit screen)",
        widget=forms.TextInput(attrs={"size": "50"}),
    )

    class Meta:
        model = WandererManagedMap
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only show ACL selection on creation (not edit)
        if not self.instance.pk:
            # Try to fetch existing ACLs if we have the required fields
            data = self.data if self.is_bound else (self.initial or {})
            if (
                data.get("wanderer_url")
                and data.get("map_slug")
                and data.get("map_api_key")
            ):
                try:
                    acls = get_map_acls(
                        data["wanderer_url"],
                        data["map_slug"],
                        data["map_api_key"],
                    )

                    choices = [
                        ("__CREATE_NEW__", "Create new ACL (managed by Alliance Auth)")
                    ]
                    for acl in acls:
                        # API doesn't return api_key for security reasons, only ID and name
                        choices.append(
                            (acl["id"], f"Use existing: {acl.get('name', acl['id'])}")
                        )

                    self.fields["acl_selection"].choices = choices
                    self.fields["acl_selection"].initial = "__CREATE_NEW__"
                except BadAPIKeyError:
                    logger.warning("Invalid API key when fetching ACLs")
                    self.fields["acl_selection"].choices = [
                        (
                            "__CREATE_NEW__",
                            "Create new ACL (unable to verify existing ACLs - invalid API key)",
                        )
                    ]
                    self.fields["acl_selection"].initial = "__CREATE_NEW__"
                except requests.RequestException as e:
                    logger.warning("Network error when fetching ACLs: %s", e)
                    self.fields["acl_selection"].choices = [
                        (
                            "__CREATE_NEW__",
                            "Create new ACL (unable to fetch existing ACLs - network error)",
                        )
                    ]
                    self.fields["acl_selection"].initial = "__CREATE_NEW__"
                except ValidationError as exc:
                    logger.warning("Invalid Wanderer URL: %s", exc)
                    self.fields["acl_selection"].choices = [
                        (
                            "__CREATE_NEW__",
                            "Create new ACL (unable to fetch existing ACLs - invalid URL)",
                        )
                    ]
                    self.fields["acl_selection"].initial = "__CREATE_NEW__"
            else:
                # No data yet, show placeholder
                self.fields["acl_selection"].choices = [
                    ("", "Fill in map details above to see ACL options")
                ]
        else:
            # Editing existing map - remove ACL selection fields
            del self.fields["acl_selection"]
            del self.fields["existing_acl_api_key"]

    def clean_wanderer_url(self):
        """Validate and normalize wanderer_url"""
        url = self.cleaned_data.get("wanderer_url")
        if url:
            try:
                url = validate_wanderer_url(url)
            except ValidationError as e:
                raise forms.ValidationError(str(e))
        return url

    def clean(self):
        cleaned_data = super().clean()

        # Validation only applies on creation
        if not self.instance.pk:
            acl_selection = cleaned_data.get("acl_selection")
            existing_acl_api_key = cleaned_data.get("existing_acl_api_key")

            if not acl_selection or acl_selection == "":
                raise ValidationError("Please select an ACL option")

            # If selecting existing ACL, require the API key
            if acl_selection != "__CREATE_NEW__" and not existing_acl_api_key:
                raise ValidationError(
                    {
                        "existing_acl_api_key": "API key is required when using an existing ACL. "
                        "Find it in Wanderer by editing the ACL."
                    }
                )

        return cleaned_data
