"""Interactions with the wanderer's API"""

import enum

import requests

from allianceauth.services.hooks import get_extension_logger

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


DEFAULT_TIMEOUT = 5


def create_acl_associated_to_map(
    wanderer_url: str, map_slug: str, requesting_character_id: int, map_api_key: str
) -> (str, str):
    """
    Will create a new ACL associated with the map `map_slug`

    Returns the ACL associated id and API key
    """

    logger.info(
        "Creating ACL on wanderer %s for map %s by character %d with api key %s",
        wanderer_url,
        map_slug,
        requesting_character_id,
        map_api_key,
    )

    r = requests.post(
        f"{wanderer_url}/api/map/acls?slug={map_slug}",
        headers={"Authorization": f"Bearer {map_api_key}"},
        json={
            "acl": {
                "name": f"AA ACL {map_slug}",
                "description": f"Access list managed by aa-wanderer for the map {map_slug}. Do not manually edit.",
                "owner_eve_id": str(requesting_character_id),
            }
        },
        timeout=DEFAULT_TIMEOUT,
    )

    logger.debug("Received status code %d", r.status_code)
    logger.debug(r.text)

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
            f"The API key {map_api_key} returned a 401 when trying to create an ACL on map {wanderer_url} {map_slug}"
        )

    r.raise_for_status()

    acl_id = r.json()["data"]["id"]
    acl_key = r.json()["data"]["api_key"]
    logger.info("Successfully created ACL id %s")

    return acl_id, acl_key


def get_acl_member_ids(wanderer_url: str, acl_id: str, acl_api_key: str) -> list[int]:
    """
    Returns all members eve_character_id present in an ACL
    """
    logger.info("Requesting character on the ACL of map %s / %s", wanderer_url, acl_id)

    r = _get_raw_acl_members(wanderer_url, acl_id, acl_api_key)

    return [
        int(member["eve_character_id"])
        for member in r.json()["data"]["members"]
        if member["eve_character_id"]
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

    r = requests.post(
        f"{wanderer_url}/api/acls/{acl_id}/members",
        headers={"Authorization": f"Bearer {acl_api_key}"},
        json={
            "member": {
                "eve_character_id": str(character_id),
                "role": role.value,
            }
        },
        timeout=DEFAULT_TIMEOUT,
    )

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"The API key {acl_api_key} returned a 401 when trying to access the members of ACL {wanderer_url} {acl_id}"
        )

    r.raise_for_status()


def remove_member_from_access_list(
    wanderer_url: str, acl_id: str, acl_api_key: str, member_id: int
):
    """
    Removes the member with specified id from the ACL
    """

    r = requests.delete(
        f"{wanderer_url}/api/acls/{acl_id}/members/{member_id}",
        headers={"Authorization": f"Bearer {acl_api_key}"},
        timeout=DEFAULT_TIMEOUT,
    )

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"The API key {acl_api_key} returned a 401 when trying to access the members of ACL {wanderer_url} {acl_id}"
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
    logger.info(
        "Requesting character on the ACL of map %s / %s without member role",
        wanderer_url,
        acl_id,
    )

    r = _get_raw_acl_members(wanderer_url, acl_id, acl_api_key)

    return [
        (int(member["eve_character_id"]), AccessListRoles(member["role"]))
        for member in r.json()["data"]["members"]
        if member["role"] != "member" and member["eve_character_id"]
    ]


def set_character_to_member(
    wanderer_url: str, acl_id: str, acl_api_key: str, character_id
):
    """
    Sets the character with the given eve id to member on the access list
    """
    logger.info(
        "Making character %d to member on map %s / %s",
        character_id,
        wanderer_url,
        acl_id,
    )

    r = requests.put(
        f"{wanderer_url}/api/acls/{acl_id}/members/{character_id}",
        headers={"Authorization": f"Bearer {acl_api_key}"},
        json={
            "member": {
                "role": "member",
            }
        },
        timeout=DEFAULT_TIMEOUT,
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
    logger.info(
        "Updating character %d to role %s on map %s / %s",
        character_id,
        role.value,
        wanderer_url,
        acl_id,
    )

    r = requests.put(
        f"{wanderer_url}/api/acls/{acl_id}/members/{character_id}",
        headers={"Authorization": f"Bearer {acl_api_key}"},
        json={"member": {"role": role.value}},
        timeout=DEFAULT_TIMEOUT,
    )

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"The API key {acl_api_key} returned a 401 when trying to update character role on ACL {wanderer_url} {acl_id}"
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
    logger.info(
        "Getting role for character %d on map %s / %s",
        character_id,
        wanderer_url,
        acl_id,
    )

    r = requests.get(
        f"{wanderer_url}/api/acls/{acl_id}/members/{character_id}",
        headers={"Authorization": f"Bearer {acl_api_key}"},
        timeout=DEFAULT_TIMEOUT,
    )

    if r.status_code == 404:
        raise NotFoundError(f"Character {character_id} not found on ACL {acl_id}")

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"The API key {acl_api_key} returned a 401 when trying to get character role on ACL {wanderer_url} {acl_id}"
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
    logger.info(
        "Getting ACLs for map %s / %s",
        wanderer_url,
        map_slug,
    )

    r = requests.get(
        f"{wanderer_url}/api/map/acls",
        params={"slug": map_slug},
        headers={"Authorization": f"Bearer {map_api_key}"},
        timeout=DEFAULT_TIMEOUT,
    )

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"The API key {map_api_key} returned a 401 when trying to get ACLs for map {wanderer_url} {map_slug}"
        )

    r.raise_for_status()

    data = r.json()
    # API returns: {"data": [{"id": "...", "name": "...", "description": ..., "owner_eve_id": "...", ...}]}
    return data.get("data", [])


def _get_raw_acl_members(wanderer_url: str, acl_id: str, acl_api_key: str):
    """Returns the raw result of requesting the members on an access list"""
    r = requests.get(
        f"{wanderer_url}/api/acls/{acl_id}",
        headers={"Authorization": f"Bearer {acl_api_key}"},
        timeout=DEFAULT_TIMEOUT,
    )
    logger.debug(r)
    logger.debug(r.text)

    if r.status_code == 401:
        raise BadAPIKeyError(
            f"The API key {acl_api_key} returned a 401 when trying to access the members of ACL {wanderer_url} {acl_id}"
        )

    r.raise_for_status()

    return r
