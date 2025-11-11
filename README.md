# aa-wanderer-map

[![PyPI](https://img.shields.io/pypi/v/aa-wanderer-map)](https://pypi.org/project/aa-wanderer-map/)
[![Python Version](https://img.shields.io/pypi/pyversions/aa-wanderer-map)](https://pypi.org/project/aa-wanderer-map/)
[![Django Version](https://img.shields.io/badge/django-4.2-blue)](https://www.djangoproject.com/)
[![License](https://img.shields.io/github/license/guarzo/aa-wanderer-map)](https://github.com/guarzo/aa-wanderer-map/blob/main/LICENSE)

An [Alliance Auth](https://gitlab.com/allianceauth/allianceauth) plugin that integrates your Alliance Auth installation with [Wanderer](https://wanderer.ltd/) wormhole mapping service, providing automated access control list (ACL) management.

This is a maintained fork of the [original aa-wanderer](https://gitlab.com/r0kym/aa-wanderer) by T'rahk Rokym, featuring bug fixes, improvements, and ongoing maintenance.

## Features

- Automated access control list (ACL) management for Wanderer maps
- Granular permission system based on Alliance Auth states, groups, characters, corporations, alliances, and factions
- Automatic synchronization of user characters with Wanderer map access
- Support for multiple Wanderer instances and maps
- Periodic cleanup tasks to maintain ACL integrity
- Preserves admin and manager roles on the managed ACL

## Recent Updates

**v0.1.6** - Enhanced ACL management to allow usage of existing ACL, and control of admin/manager

**v0.1.5** - Fixed migration errors and improved database table initialization handling

## Credits

- **T'rahk Rokym** - Original aa-wanderer implementation
- **A-A-Ron** - [allianceauth-multiverse](https://github.com/Solar-Helix-Independent-Transport/allianceauth-discord-multiverse) architecture that enabled multiple service support

## How It Works

aa-wanderer-map creates and manages a dedicated access list on your Wanderer map, separate from any manually configured access lists. This managed ACL is automatically synchronized with your Alliance Auth permissions.

**Notes:**
- The managed ACL created by aa-wanderer-map should not be manually edited
- Users who lose Alliance Auth permissions will be automatically removed from the managed ACL, regardless of their role

## Installation

### Step 1 - Check Prerequisites

1. **Alliance Auth Installation** - This plugin requires a working Alliance Auth installation. If you haven't installed Alliance Auth yet, please follow the official [Alliance Auth installation guide](https://allianceauth.readthedocs.io/en/latest/installation/auth/allianceauth/).
2. **Wanderer Map Administrator Access** - You must have administrator access to a Wanderer map to obtain the map API key required for creating the managed access list.

### Step 2 - Install Application

Ensure you are in the virtual environment of your Alliance Auth installation, then install the latest release from PyPI:

```bash
pip install aa-wanderer-map
```

### Step 3 - Configure Settings

Add the following configuration to your Alliance Auth settings file (`local.py`):

1. Add `'wanderer'` to `INSTALLED_APPS`:

```python
INSTALLED_APPS += [
    'wanderer',
]
```

2. Configure the periodic cleanup task:

```python
CELERYBEAT_SCHEDULE['wanderer_cleanup_access_lists'] = {
    'task': 'wanderer.tasks.cleanup_all_access_lists',
    'schedule': crontab(minute='0', hour='*/1'),
}
```

### Step 4 - Finalize Installation

Run migrations and collect static files:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

Restart your Alliance Auth supervisor services:

```bash
supervisorctl restart myauth:
```

## Management Commands

The following Django management commands are available:

| Command                 | Description                                                                              |
|-------------------------|------------------------------------------------------------------------------------------|
| `wanderer_cleanup_acls` | Manually executes the cleanup task on all managed maps and updates their access lists.  |

### Usage Examples:

**Sync all maps:**
```bash
python manage.py wanderer_cleanup_acls
```

**Sync a specific map:**
```bash
python manage.py wanderer_cleanup_acls --map-id 5
```

The command queues Celery tasks for role synchronization. Check your logs to see the progress and results.

## Usage

### Creating a Wanderer Map

When creating a new Wanderer-managed map in Django Admin:

1. Navigate to **Django Admin → Wanderer → Wanderer Managed Maps → Add**
2. Fill in the map details:
   - **Name**: A descriptive name for the map
   - **Wanderer URL**: The base URL of your Wanderer instance (e.g., `https://wanderer.ltd`)
   - **Map slug**: The unique identifier for the map in Wanderer
   - **Map API key**: The API key for the map (with admin permissions)
3. In the **Access List Selection** section:
   - **Create new ACL**: Alliance Auth creates a fresh ACL for this map (recommended)
   - **Use existing**: Select from existing ACLs already on the map in Wanderer
4. Configure **Member Access** permissions:
   - Choose which states, groups, characters, corporations, alliances, or factions can access the map
   - Users matching these criteria will be able to link their account and access the map as members
5. Save the map

**Important Notes:**
- If you select an existing ACL, Alliance Auth will manage it going forward. Manual changes to the ACL may be overwritten during cleanup.
- Each map creates a dynamic service in Alliance Auth that users can link to

### Assigning Map Admins and Managers

To automatically assign users or groups as map admins or managers:

1. Navigate to **Django Admin → Wanderer → Wanderer Managed Maps**
2. Select and edit the map you want to configure
3. In the **Admin Roles** section:
   - **Admin users**: Add individual users who should have admin role on the map
   - **Admin groups**: Add groups whose members should have admin role on the map
4. In the **Manager Roles** section:
   - **Manager users**: Add individual users who should have manager role on the map
   - **Manager groups**: Add groups whose members should have manager role on the map
5. Save the map
6. Role synchronization happens automatically:
   - **Immediately**: Changes trigger automatic sync via signal handlers
   - **Hourly**: Periodic cleanup task ensures consistency
   - **Manual sync options**:
     - Use the "Sync ACL roles now" action in the Django admin (select maps → Actions dropdown)
     - Or run: `python manage.py wanderer_cleanup_acls`
     - Or sync specific map: `python manage.py wanderer_cleanup_acls --map-id 5`

**Important Notes:**
- **All characters** (main + alts) for each assigned user receive the admin/manager role, not just their main character
- Role priority: ADMIN > MANAGER > MEMBER (if a user is in multiple categories, they get the highest role)
- Manually-set admin/manager roles (not managed by Auth) are preserved during cleanup, as long as the character is authorized to access the map
- Users must still have access permissions (configured in Member Access) to be on the ACL

---

## Contributing

### Development Setup

To contribute to this project or test it locally, follow these steps:

#### 1. Install System Dependencies

Before setting up the development environment, you need to install system-level dependencies required by Alliance Auth:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y pkg-config python3-dev default-libmysqlclient-dev build-essential git redis-server
```

**Or for MariaDB:**
```bash
sudo apt-get install -y pkg-config python3-dev libmariadb-dev build-essential git redis-server
```

**Fedora/RHEL/CentOS:**
```bash
sudo dnf install -y pkg-config python3-devel mysql-devel gcc git redis
```

**macOS:**
```bash
brew install pkg-config mysql redis git
```

#### 2. Clone the Repository

```bash
git clone https://github.com/guarzo/aa-wanderer-map.git
cd aa-wanderer-map
```

#### 3. Create Virtual Environment

**Using the setup script (recommended):**

```bash
# Make the script executable
chmod +x dev-setup.sh

# Run the setup script
./dev-setup.sh
```

**Manual setup:**

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Upgrade pip
pip install --upgrade pip

# Install development dependencies
pip install -e .
pip install tox black isort flake8
```

#### 4. Running Tests

```bash
# Activate venv if not already activated
source venv/bin/activate

# Run all tests with tox
tox

# Run specific Python version tests
tox -e py310-django42

# Check code formatting
black --check .

# Format code
black .

# Check import sorting
isort . --check-only

# Sort imports
isort .

# Run linter
flake8 wanderer/

# Run pylint
tox -e pylint
```

#### 5. Building the Package

```bash
# Install build tools
pip install build

# Build the package
python -m build

# Check the built package
ls -la dist/
```

### Contribution Guidelines

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Format your code: `black . && isort .`
5. Run the test suite: `tox`
6. Commit your changes with a descriptive message
7. Push to your branch: `git push origin feature/your-feature-name`
8. Open a Pull Request with a clear description of your changes

### Troubleshooting

#### `mysqlclient` Build Errors

If you encounter errors like `Can not find valid pkg-config name` or `mysql_config not found`:

**Solution:** Install the required system packages:

```bash
# Ubuntu/Debian
sudo apt-get install pkg-config python3-dev default-libmysqlclient-dev build-essential

# Fedora/RHEL/CentOS
sudo dnf install pkg-config python3-devel mysql-devel gcc

# macOS
brew install pkg-config mysql
```

Then retry the setup.

#### Redis Connection Errors

If tests fail with Redis connection errors:

```bash
# Start Redis
redis-server --daemonize yes

# Or on macOS with Homebrew
brew services start redis
```

#### Code Formatting Issues

To format your code properly:

```bash
# Auto-format with Black
black .

# Sort imports
isort .

# Check for issues
flake8 wanderer/

# Then commit the changes
git add .
git commit -m "Fix formatting"
```

## Support

### Reporting Issues

Please report issues on the [GitHub issue tracker](https://github.com/guarzo/aa-wanderer-map/issues).

When reporting an issue, please include:
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Python version
- Alliance Auth version
- Relevant error messages or logs
- Operating system and version

### Getting Help

For questions and support:
- Open an issue on GitHub with the `question` label
- Check existing issues for similar questions or problems

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
