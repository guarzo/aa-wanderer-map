"""Interactions with the wanderer's API"""

import enum

from allianceauth.services.hooks import get_extension_logger

from wanderer.http_client import WandererHTTPClient as http
from wanderer.utils import sanitize_api_key, sanitize_url, validate_wanderer_url

logger = get_extension_logger(__name__)


class AccessListRoles(enum.Enum):
    """All roles that can be assigned on an access list"""

    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"
    BLOCKED = "-blocked-"


class BadAPIKeyError(Exception):
    """Exception raised when a wrong API key is provided"""


class NotFoundError(Exception):
    """Exception raised when the API returned an expected 404"""


class OwnerEveIdDoesNotExistError(Exception):
    """Exception raised when attempting to create a map with an owner not known by Wanderer"""


def create_acl_associated_to_map(
    wanderer_url: str, map_slug: str, requesting_character_id: int, map_api_key: str
) -> (str, str):
    """
    Will create a new ACL associated with the map `map_slug`

    Returns the ACL associated id and API key
    """
    # Validate URL
    wanderer_url = validate_wanderer_url(wanderer_url)

    logger.info(
        "Creating ACL on wanderer %s for map %s by character %d",
        sanitize_url(wanderer_url),
        map_slug,
        requesting_character_id,
    )
    logger.debug("Using map API key: %s", sanitize_api_key(map_api_key))

    r = http.post(
        f"{wanderer_url}/api/map/acls?slug={map_slug}",
        headers={"Authorization": f"Bearer {map_api_key}"},
        json={
            "acl": {
                "name": f"AA ACL {map_slug}",
                "description": f"Access list managed by aa-wanderer for the map {map_slug}. Do not manually edit.",
                "owner_eve_id": str(requesting_character_id),
            }
        },
    )

    logger.debug("Received status code %d", r.status_code)

    if (
        r.status_code == 400
        and "owner_eve_id does not match any existing character" in r.text
    ):
        raise OwnerEveIdDoesNotExistError(
            f"The eve character with id {requesting_character_id} "
            "doesn't seem to be known by Wanderer"
        )

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"Invalid map API key (ending in {sanitize_api_key(map_api_key)}) "
            f"for map {wanderer_url}/{map_slug}"
        )

    r.raise_for_status()

    # Parse JSON response
    try:
        payload = r.json()
    except ValueError as e:
        logger.error(
            "Failed to parse JSON response from Wanderer API. "
            "Status: %d, Response: %s",
            r.status_code,
            r.text[:500],  # Limit response length for logging
        )
        raise ValueError(
            f"Wanderer API returned invalid JSON (status {r.status_code}): {str(e)}"
        ) from e

    # Validate response structure
    if not isinstance(payload, dict):
        logger.error(
            "Wanderer API returned non-dict JSON payload. "
            "Status: %d, Type: %s, Response: %s",
            r.status_code,
            type(payload).__name__,
            str(r.text[:500]),  # Limit response length for logging
        )
        raise ValueError(
            f"Wanderer API returned unexpected JSON type (status {r.status_code}): "
            f"expected dict, got {type(payload).__name__}"
        )

    acl_data = payload.get("data")
    if not isinstance(acl_data, dict):
        logger.error(
            "Wanderer API response missing 'data' field or invalid format. "
            "Response: %s",
            r.text[:500],
        )
        raise ValueError(
            f"Wanderer API returned unexpected response format. "
            f"Expected 'data' dict, got: {type(acl_data).__name__}"
        )

    # Extract ACL ID and API key
    acl_id = acl_data.get("id")
    acl_key = acl_data.get("api_key")

    if not acl_id:
        # Create sanitized copy for logging (don't leak api_key in logs)
        sanitized_acl_data = acl_data.copy()
        if "api_key" in sanitized_acl_data:
            sanitized_acl_data["api_key"] = sanitize_api_key(
                sanitized_acl_data["api_key"]
            )
        logger.error(
            "Wanderer API response missing ACL 'id'. Response data: %s",
            sanitized_acl_data,
        )
        raise ValueError("Wanderer API response missing ACL 'id' field")

    if not acl_key:
        # Create sanitized copy for logging (don't leak api_key in logs)
        sanitized_acl_data = acl_data.copy()
        if "api_key" in sanitized_acl_data:
            sanitized_acl_data["api_key"] = sanitize_api_key(
                sanitized_acl_data["api_key"]
            )
        logger.error(
            "Wanderer API response missing ACL 'api_key'. Response data: %s",
            sanitized_acl_data,
        )
        raise ValueError("Wanderer API response missing ACL 'api_key' field")

    logger.debug(
        "Successfully created ACL id %s (api_key=%s)",
        acl_id,
        sanitize_api_key(acl_key),
    )
    logger.info("Successfully created ACL id %s", acl_id)

    return acl_id, acl_key


def get_acl_member_ids(wanderer_url: str, acl_id: str, acl_api_key: str) -> list[int]:
    """
    Returns all members eve_character_id present in an ACL
    """
    # Validate URL
    wanderer_url = validate_wanderer_url(wanderer_url)

    logger.info("Requesting character on the ACL of map %s / %s", wanderer_url, acl_id)

    r = _get_raw_acl_members(wanderer_url, acl_id, acl_api_key)

    data = r.json()
    members = data.get("data", {}).get("members", [])
    return [
        int(member["eve_character_id"])
        for member in members
        if member.get("eve_character_id")
    ]


def add_character_to_acl(
    wanderer_url: str,
    acl_id: str,
    acl_api_key: str,
    character_id: int,
    role: AccessListRoles = AccessListRoles.MEMBER,
):
    """
    Adds a single character to the ACL with specified role.

    Args:
        wanderer_url: Base URL of the Wanderer instance
        acl_id: The ACL ID
        acl_api_key: API key for the ACL
        character_id: EVE character ID to add
        role: AccessListRoles enum value (defaults to MEMBER for backwards compatibility)

    Raises:
        BadAPIKeyError: If the API key is invalid
        requests.HTTPError: If the API call fails
    """
    # Validate URL
    wanderer_url = validate_wanderer_url(wanderer_url)

    r = http.post(
        f"{wanderer_url}/api/acls/{acl_id}/members",
        headers={"Authorization": f"Bearer {acl_api_key}"},
        json={
            "member": {
                "eve_character_id": str(character_id),
                "role": role.value,
            }
        },
    )

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"Invalid ACL API key (ending in {sanitize_api_key(acl_api_key)}) "
            f"for ACL {acl_id}"
        )

    r.raise_for_status()


def remove_member_from_access_list(
    wanderer_url: str, acl_id: str, acl_api_key: str, member_id: int
):
    """
    Removes the member with specified id from the ACL
    """
    # Validate URL
    wanderer_url = validate_wanderer_url(wanderer_url)

    r = http.delete(
        f"{wanderer_url}/api/acls/{acl_id}/members/{member_id}",
        headers={"Authorization": f"Bearer {acl_api_key}"},
    )

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"Invalid ACL API key (ending in {sanitize_api_key(acl_api_key)}) "
            f"for ACL {acl_id}"
        )

    if r.status_code == 404:  # If the API isn't found a 401 is raised
        raise NotFoundError(f"Member id {member_id} was not found on ACL {acl_id}")

    r.raise_for_status()


def get_non_member_characters(
    wanderer_url: str, acl_id: str, acl_api_key: str
) -> list[(int, AccessListRoles)]:
    """
    Return the character_id and role of characters that have a role different from member
    """
    # Validate URL
    wanderer_url = validate_wanderer_url(wanderer_url)

    logger.info(
        "Requesting character on the ACL of map %s / %s without member role",
        wanderer_url,
        acl_id,
    )

    r = _get_raw_acl_members(wanderer_url, acl_id, acl_api_key)

    data = r.json()
    members = data.get("data", {}).get("members", [])
    return [
        (int(member["eve_character_id"]), AccessListRoles(member["role"]))
        for member in members
        if member.get("role") != "member" and member.get("eve_character_id")
    ]


def set_character_to_member(
    wanderer_url: str, acl_id: str, acl_api_key: str, character_id
):
    """
    Sets the character with the given eve id to member on the access list
    """
    # Validate URL
    wanderer_url = validate_wanderer_url(wanderer_url)

    logger.info(
        "Making character %d to member on map %s / %s",
        character_id,
        wanderer_url,
        acl_id,
    )

    r = http.put(
        f"{wanderer_url}/api/acls/{acl_id}/members/{character_id}",
        headers={"Authorization": f"Bearer {acl_api_key}"},
        json={
            "member": {
                "role": AccessListRoles.MEMBER.value,
            }
        },
    )

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"Invalid ACL API key (ending in {sanitize_api_key(acl_api_key)}) "
            f"when setting character {character_id} to member on ACL {acl_id}"
        )

    r.raise_for_status()


def update_character_role(
    wanderer_url: str,
    acl_id: str,
    acl_api_key: str,
    character_id: int,
    role: AccessListRoles,
) -> None:
    """
    Update a character's role on the ACL.

    Args:
        wanderer_url: Base URL of the Wanderer instance
        acl_id: The ACL ID
        acl_api_key: API key for the ACL
        character_id: EVE character ID to update
        role: AccessListRoles enum value (ADMIN, MANAGER, MEMBER, etc.)

    Raises:
        BadAPIKeyError: If the API key is invalid
        requests.HTTPError: If the API call fails
    """
    # Validate URL
    wanderer_url = validate_wanderer_url(wanderer_url)

    logger.info(
        "Updating character %d to role %s on map %s / %s",
        character_id,
        role.value,
        wanderer_url,
        acl_id,
    )

    r = http.put(
        f"{wanderer_url}/api/acls/{acl_id}/members/{character_id}",
        headers={"Authorization": f"Bearer {acl_api_key}"},
        json={"member": {"role": role.value}},
    )

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"Invalid ACL API key (ending in {sanitize_api_key(acl_api_key)}) "
            f"when updating character role on ACL {acl_id}"
        )

    r.raise_for_status()


def get_member_role(
    wanderer_url: str,
    acl_id: str,
    acl_api_key: str,
    character_id: int,
) -> AccessListRoles:
    """
    Get the current role of a character on the ACL.

    Args:
        wanderer_url: Base URL of the Wanderer instance
        acl_id: The ACL ID
        acl_api_key: API key for the ACL
        character_id: EVE character ID to query

    Returns:
        AccessListRoles enum value

    Raises:
        NotFoundError: If character is not on the ACL
        BadAPIKeyError: If the API key is invalid
        requests.HTTPError: If the API call fails
    """
    # Validate URL
    wanderer_url = validate_wanderer_url(wanderer_url)

    logger.info(
        "Getting role for character %d on map %s / %s",
        character_id,
        wanderer_url,
        acl_id,
    )

    r = http.get(
        f"{wanderer_url}/api/acls/{acl_id}/members/{character_id}",
        headers={"Authorization": f"Bearer {acl_api_key}"},
    )

    if r.status_code == 404:
        raise NotFoundError(f"Character {character_id} not found on ACL {acl_id}")

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"Invalid ACL API key (ending in {sanitize_api_key(acl_api_key)}) "
            f"when getting character role on ACL {acl_id}"
        )

    r.raise_for_status()
    data = r.json()

    role_str = data.get("member", {}).get("role", "member")
    return AccessListRoles(role_str)


def get_map_acls(
    wanderer_url: str,
    map_slug: str,
    map_api_key: str,
) -> list:
    """
    Get all ACLs associated with a map.

    Args:
        wanderer_url: Base URL of the Wanderer instance
        map_slug: Map identifier/slug
        map_api_key: API key for the map

    Returns:
        List of ACL dicts: [{"id": "uuid", "name": "ACL Name", "description": "...",
                            "owner_eve_id": "...", "inserted_at": "...", "updated_at": "..."}, ...]
        Note: The api_key field is NOT included in the response for security reasons.

    Raises:
        BadAPIKeyError: If the API key is invalid (401)
        requests.HTTPError: If the API call fails

    References:
        Wanderer API Documentation: https://wanderer.ltd/news/api
        Endpoint: GET /api/map/acls?slug={map_slug}
    """
    # Validate URL
    wanderer_url = validate_wanderer_url(wanderer_url)

    logger.info(
        "Getting ACLs for map %s / %s",
        wanderer_url,
        map_slug,
    )

    r = http.get(
        f"{wanderer_url}/api/map/acls",
        params={"slug": map_slug},
        headers={"Authorization": f"Bearer {map_api_key}"},
    )

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"Invalid map API key (ending in {sanitize_api_key(map_api_key)}) "
            f"when getting ACLs for map {map_slug}"
        )

    r.raise_for_status()

    data = r.json()
    # API returns: {"data": [{"id": "...", "name": "...", "description": ..., "owner_eve_id": "...", ...}]}
    return data.get("data", [])


def _get_raw_acl_members(wanderer_url: str, acl_id: str, acl_api_key: str):
    """Returns the raw result of requesting the members on an access list"""
    # Validate URL
    wanderer_url = validate_wanderer_url(wanderer_url)

    r = http.get(
        f"{wanderer_url}/api/acls/{acl_id}",
        headers={"Authorization": f"Bearer {acl_api_key}"},
    )
    logger.debug(r)
    logger.debug(r.text)

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"Invalid ACL API key (ending in {sanitize_api_key(acl_api_key)}) "
            f"for ACL {acl_id}"
        )

    r.raise_for_status()

    return r
