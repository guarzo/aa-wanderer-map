# aa-wanderer-map

[![PyPI](https://img.shields.io/pypi/v/aa-wanderer-map)](https://pypi.org/project/aa-wanderer-map/)
[![Python Version](https://img.shields.io/pypi/pyversions/aa-wanderer-map)](https://pypi.org/project/aa-wanderer-map/)
[![Django Version](https://img.shields.io/badge/django-4.2-blue)](https://www.djangoproject.com/)
[![License](https://img.shields.io/github/license/guarzo/aa-wanderer-map)](https://github.com/guarzo/aa-wanderer-map/blob/main/LICENSE)

[Alliance Auth](https://gitlab.com/allianceauth/allianceauth) application linking your auth with a [wanderer](https://wanderer.ltd/) instance.

This is a maintained fork of the [original aa-wanderer](https://gitlab.com/r0kym/aa-wanderer) by T'rahk Rokym, which includes bug fixes and improvements.

## Recent Updates

**v0.1.5** - Fixed migration errors and improved database table initialization handling

Credit to:
- T'rahk Rokym for the original aa-wanderer implementation
- A-A-Ron for his work on [allianceauth-multiverse](https://github.com/Solar-Helix-Independent-Transport/allianceauth-discord-multiverse) without which multiple services wouldn't have been possible

## Planned features
- [ ] Wanderer ACL management through the auth

## Usage
Currently, I recommend keeping a normal wanderer access list on your map that you configure yourself.
You can add your corporation/alliance on this access list to make sure that all mains can easily open your map.
It also allows you to add another group if needed during a joint op. \
The application will create another access list that will be fully managed and shouldn't be manually edited.
The only thing you can change on that access list is moving some characters to admin or manager to keep an overview.
But even these admin/manager characters will be removed from the access list if they lose access to the service.

## Installation

### Step 1 - Check prerequisites

1. aa-wanderer is a plugin for Alliance Auth. If you don't have Alliance Auth running already, please install it first before proceeding. (see the official [AA installation guide](https://allianceauth.readthedocs.io/en/latest/installation/auth/allianceauth/) for details)
2. You need to have a map with administrator access on wanderer to recover the map API key that will be used to create a new access list.

### Step 2 - Install app

Make sure you are in the virtual environment (venv) of your Alliance Auth installation. Then install the newest release from PyPI:

```bash
pip install aa-wanderer-map
```

### Step 3 - Configure Auth settings

Configure your Auth settings (`local.py`) as follows:

- Add `'wanderer'` to `INSTALLED_APPS`
- Add below lines to your settings file:

```python
CELERYBEAT_SCHEDULE['wanderer_cleanup_access_lists'] = {
    'task': 'wanderer.tasks.cleanup_all_access_lists',
    'schedule': crontab(minute='0', hour='*/1'),
}
```

### Step 4 - Finalize App installation

Run migrations & copy static files

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

Restart your supervisor services for Auth.


### Commands

The following commands can be used when running the module:

| Name                    | Description                                                                              |
|-------------------------|------------------------------------------------------------------------------------------|
| `wanderer_cleanup_acls` | Will execute the cleanup command on all your managed maps and update their access lists. |

---

## Development

### Development Setup

If you want to contribute to this project or test it locally, follow these steps:

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

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Format your code: `black . && isort .`
5. Run tests: `tox`
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

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

### Reporting Issues

Please report issues on the [GitHub issue tracker](https://github.com/guarzo/aa-wanderer-map/issues).

Include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Your Python version
- Your Alliance Auth version
- Any relevant error messages
- Your operating system and version
