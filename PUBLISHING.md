# Publishing Guide for aa-wanderer-map

This document outlines the steps to publish this forked project to PyPI and maintain it on GitHub.

## Prerequisites

1. GitHub account: `guarzo`
2. PyPI account: [Create one at pypi.org](https://pypi.org/account/register/)

## Initial Setup

### 1. Create GitHub Repository

```bash
# Initialize git if not already done
git init

# Add GitHub remote
git remote remove origin  # Remove old GitLab remote
git remote add origin https://github.com/guarzo/aa-wanderer-map.git

# Push to GitHub
git add .
git commit -m "Fork and update documentation for aa-wanderer-map"
git push -u origin main
```

### 2. Set Up PyPI Trusted Publishing

This project uses PyPI's trusted publishing (OIDC) which is more secure than API tokens.

1. Go to [PyPI](https://pypi.org/) and log in
2. Navigate to your account settings
3. Go to "Publishing" → "Add a new pending publisher"
4. Fill in:
   - **PyPI Project Name**: `aa-wanderer-map`
   - **Owner**: `guarzo`
   - **Repository name**: `aa-wanderer-map`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`

This tells PyPI to trust releases from your GitHub repository.

## Publishing a Release

### Option 1: GitHub Release (Recommended)

1. Update version in `wanderer/__init__.py`
2. Update `CHANGELOG.md` with the new version
3. Commit changes:
   ```bash
   git add wanderer/__init__.py CHANGELOG.md
   git commit -m "Bump version to X.Y.Z"
   git push
   ```
4. Create a GitHub release:
   - Go to https://github.com/guarzo/aa-wanderer-map/releases
   - Click "Draft a new release"
   - Click "Choose a tag" and create new tag (e.g., `v0.1.5`)
   - Fill in release title and description
   - Click "Publish release"
5. GitHub Actions will automatically build and publish to PyPI

### Option 2: Manual Publishing

If you prefer to publish manually:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Upload to PyPI
twine upload dist/*
```

You'll need a PyPI API token for manual publishing.

## Development Setup

Before publishing, set up a development environment:

```bash
# Clone the repository
git clone https://github.com/guarzo/aa-wanderer-map.git
cd aa-wanderer-map

# Run the development setup script
chmod +x dev-setup.sh
./dev-setup.sh
```

This will:
- Create and activate a virtual environment
- Install the package in editable mode
- Install all development dependencies (tox, black, isort, flake8, build, twine)
- Check for Redis installation

## Testing Before Publishing

### Run Tests Locally

```bash
# Activate venv (if not already activated)
source venv/bin/activate

# Run all tests
tox

# Run specific test
tox -e py310-django42

# Check and format code
black .
isort .
flake8 wanderer/
```

### Test Installation Locally

```bash
# Build the package
python -m build

# Install in test environment
pip install dist/aa_wanderer_map-0.1.5-py3-none-any.whl
```

### Test with TestPyPI (Optional)

TestPyPI is a separate instance of PyPI for testing:

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ aa-wanderer-map
```

## Post-Publication

### Announce the Fork

Consider announcing this maintained fork in:
- Alliance Auth community forums/Discord
- EVE Online relevant channels
- Create an issue on the original repo linking to your maintained version

### Update Documentation

Add a badge to README.md:
```markdown
[![PyPI](https://img.shields.io/pypi/v/aa-wanderer-map)](https://pypi.org/project/aa-wanderer-map/)
[![Python Version](https://img.shields.io/pypi/pyversions/aa-wanderer-map)](https://pypi.org/project/aa-wanderer-map/)
[![License](https://img.shields.io/github/license/guarzo/aa-wanderer-map)](https://github.com/guarzo/aa-wanderer-map/blob/main/LICENSE)
```

## Maintenance

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features, backwards compatible
- **PATCH** (0.0.X): Bug fixes

### Regular Updates

- Monitor for issues on GitHub
- Keep dependencies updated
- Test with new Alliance Auth versions
- Check wanderer API for changes

## GitHub Actions Workflows

This project includes two workflows:

1. **tests.yml** - Runs on every push/PR
   - Code formatting checks (Black)
   - Import sorting checks (isort)
   - Linting (flake8)
   - Pylint
   - Tests on Python 3.10-3.13

2. **publish.yml** - Runs on release
   - Builds package
   - Publishes to PyPI using trusted publishing

## Troubleshooting

### Publishing Fails

- Verify PyPI trusted publishing is set up correctly
- Check that version number hasn't been used before
- Ensure `pyproject.toml` is valid: `python -m build --check`

### Tests Fail

- Check Redis is running: `redis-cli ping`
- Verify Python version compatibility
- Check dependencies: `pip install -e .[dev]`

## Resources

- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Alliance Auth Documentation](https://allianceauth.readthedocs.io/)
- [Flit Documentation](https://flit.pypa.io/) (build backend)
