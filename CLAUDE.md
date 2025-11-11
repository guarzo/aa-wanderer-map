# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

aa-wanderer-map is a Django plugin for Alliance Auth that integrates with Wanderer (a wormhole mapping service for EVE Online). It manages access control lists (ACLs) for Wanderer maps through Alliance Auth's permission system.

This is a maintained fork of the original aa-wanderer by T'rahk Rokym.

## Development Commands

### Setup
```bash
# Make setup script executable and run it
chmod +x dev-setup.sh
./dev-setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .
pip install tox black isort flake8
```

### Testing
```bash
# Run all tests with tox
tox

# Run tests for specific Python/Django version
tox -e py310-django42

# Run single test
coverage run runtests.py wanderer.tests.test_tasks -v 2

# Run linting
tox -e pylint
flake8 wanderer/
```

### Code Formatting
```bash
# Format code with Black
black .

# Sort imports
isort .

# Check formatting without changes
black --check .
isort . --check-only
```

### Building
```bash
# Install build tools
pip install build

# Build the package
python -m build
```

### Management Commands
```bash
# Cleanup all managed map access lists
python manage.py wanderer_cleanup_acls
```

## Architecture

### Core Components

**Models (`wanderer/models.py`)**:
- `WandererManagedMap`: Represents a Wanderer map with auth-managed ACL. Stores map URL, slug, API keys, and access permissions (state, group, character, corporation, alliance, faction).
- `WandererAccount`: Links an Alliance Auth user to a specific Wanderer map.

**API Client (`wanderer/wanderer.py`)**:
- Handles all HTTP interactions with Wanderer's API
- Functions for ACL management: create ACL, add/remove members, update roles
- Key exception types: `BadAPIKeyError`, `NotFoundError`, `OwnerEveIdDoesNotExistError`

**Celery Tasks (`wanderer/tasks.py`)**:
- `add_alts_to_map`: Adds user's alts to map ACL
- `remove_user_characters_from_map`: Removes user characters from ACL
- `cleanup_access_list`: Synchronizes ACL with current permissions (removes unauthorized, adds missing)
- `cleanup_all_access_lists`: Periodic task that cleans up all managed maps (configured in settings)

**Views (`wanderer/views.py`)**:
- `link`: Links user to a map (creates WandererAccount, triggers alt sync)
- `sync`: Manually syncs user's characters with map
- `remove`: Removes user from map and deletes all their characters from ACL

**Dynamic Hooks (`wanderer/auth_hooks.py`)**:
- Creates dynamic `ServicesHook` instances for each WandererManagedMap
- Uses Django signals to add/remove hooks when maps are created/deleted
- Each map appears as a separate service in Alliance Auth
- **Important**: Changes to maps during runtime require auth restart to be fully reflected

### Access Control Flow

1. User requests access to a map
2. `WandererManagedMap.accessible_by()` checks permissions based on:
   - State access
   - Group membership
   - Individual character access
   - Corporation membership
   - Alliance membership
   - Faction affiliation
3. If authorized, user can link their account
4. Linking triggers `add_alts_to_map` task to add all characters to Wanderer ACL
5. Periodic cleanup task (`cleanup_all_access_lists`) ensures ACLs stay synchronized

### Role Assignment

In addition to controlling access, admins can assign users/groups to admin and manager roles:

1. **Admin Roles**: Set via `admin_users` and `admin_groups` on WandererManagedMap
2. **Manager Roles**: Set via `manager_users` and `manager_groups` on WandererManagedMap
3. **All characters** (main + alts) for assigned users receive the elevated role
4. Role priority: ADMIN > MANAGER > MEMBER
5. Cleanup task syncs roles hourly
6. Manually-set admin/manager roles (not managed by Auth) are preserved during cleanup if the character is authorized

### ACL Selection

When creating a new WandererManagedMap:

1. Admin can choose to create a new ACL or use an existing one
2. Existing ACLs for the map are retrieved via Wanderer API
3. If using an existing ACL, Alliance Auth will manage it going forward
4. Manual changes to Auth-managed ACLs may be overwritten during cleanup

### Key Design Patterns

- Uses Django signals (`post_save`, `post_delete`) to dynamically register/unregister service hooks
- Celery tasks handle all Wanderer API interactions asynchronously
- ACL sync uses set operations to compute differences (characters to add/remove)
- Non-member roles (admin, manager) are preserved during cleanup; only viewers are demoted to members

## Configuration

### Django Settings
Add to `local.py`:
```python
INSTALLED_APPS += ['wanderer']

CELERYBEAT_SCHEDULE['wanderer_cleanup_access_lists'] = {
    'task': 'wanderer.tasks.cleanup_all_access_lists',
    'schedule': crontab(minute='0', hour='*/1'),
}
```

### Code Style
- Black formatter (max line length: 88)
- isort with custom sections (ALLIANCEAUTH, DJANGO)
- flake8 linting with specific ignores (E203, E231, E501, W503, W291, W293)
- pylint with custom config (max line length: 120)

## Testing Infrastructure

- Tests use `testauth/` as a minimal Alliance Auth installation
- Tests require Redis running
- `runtests.py` is the test runner
- Coverage reports generated automatically with tests
- Test environments: Python 3.10-3.13 with Django 4.2

## Important Notes

- The managed ACL should not be manually edited in Wanderer
- Admin/manager roles on the ACL are preserved during cleanup
- Changes to WandererManagedMap objects may require auth restart for hooks to update
- All Wanderer API calls have a 5-second timeout
