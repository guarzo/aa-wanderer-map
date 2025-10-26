# Fork Summary: aa-wanderer-map

## Overview

This document summarizes all changes made to fork the original `aa-wanderer` project into `aa-wanderer-map` for publication and maintenance by guarzo on GitHub.

## Changes Made

### 1. Bug Fixes (Critical)

**Files Modified:**
- `wanderer/auth_hooks.py` (Line 82-96)
- `wanderer/apps.py` (Line 13-22)

**Issue Fixed:**
- Fixed critical migration error where database tables were being queried before creation
- Added proper exception handling to gracefully handle missing database tables during initial setup
- Improved error logging to be more informative and less alarming

**Impact:**
- `python manage.py migrate` now completes successfully on fresh installations
- Plugin can now be installed without errors

### 2. Project Renaming

**Old Name:** `aa-wanderer`
**New Name:** `aa-wanderer-map`
**Reason:** Avoid conflicts with existing PyPI package

**Files Modified:**
- `pyproject.toml` - Updated project name
- `README.md` - Updated installation instructions
- All documentation references

### 3. Repository Migration

**Old Repository:** GitLab (`gitlab.com/r0kym/aa-wanderer`)
**New Repository:** GitHub (`github.com/guarzo/aa-wanderer-map`)

**Files Modified:**
- `pyproject.toml` - All project URLs updated
- `README.md` - Repository links updated
- `.pre-commit-config.yaml` - Commented out GitLab-specific pre-commit hook

**Files Created:**
- `.github/workflows/tests.yml` - Automated testing on push/PR
- `.github/workflows/publish.yml` - Automated PyPI publishing on release

**Files to Remove (optional):**
- `.gitlab-ci.yml` - No longer needed (replaced by GitHub Actions)

### 4. Author/Maintainer Updates

**Old Author:** T'rahk Rokym
**New Maintainer:** guarzo

**Files Modified:**
- `pyproject.toml` - Updated author and added maintainer fields
- `README.md` - Added attribution to original author
- `CHANGELOG.md` - Documented fork information

### 5. Version Bump

**Old Version:** 0.1.4
**New Version:** 0.1.5

**Files Modified:**
- `wanderer/__init__.py`
- `CHANGELOG.md` - Added detailed v0.1.5 release notes

### 6. Documentation Updates

**Files Modified:**
- `README.md`:
  - Added fork attribution
  - Updated installation command
  - Added version badge and other status badges
  - Added "Recent Updates" section

**Files Created:**
- `CHANGELOG.md` - Comprehensive fork and fix documentation
- `PUBLISHING.md` - Complete guide for publishing to PyPI
- `FORK_SUMMARY.md` - This file

### 7. CI/CD Migration

**From:** GitLab CI/CD
**To:** GitHub Actions

**Workflows Created:**

1. **tests.yml** - Runs on every push and PR
   - Pre-commit checks
   - Pylint linting
   - Tests on Python 3.10, 3.11, 3.12, 3.13
   - Tests with Django 4.2

2. **publish.yml** - Runs on GitHub releases
   - Builds package using `python-build`
   - Publishes to PyPI using trusted publishing (OIDC)
   - No API tokens needed

## File Change Summary

### Modified Files (9)
1. `wanderer/auth_hooks.py` - Bug fix
2. `wanderer/apps.py` - Bug fix
3. `wanderer/__init__.py` - Version bump
4. `pyproject.toml` - Name, URLs, author
5. `README.md` - Complete documentation update
6. `CHANGELOG.md` - Release notes and fork info
7. `.pre-commit-config.yaml` - Disable GitLab hook

### Created Files (4)
1. `.github/workflows/tests.yml` - CI testing
2. `.github/workflows/publish.yml` - PyPI publishing
3. `PUBLISHING.md` - Publishing guide
4. `FORK_SUMMARY.md` - This summary

### Files to Consider Removing (1)
1. `.gitlab-ci.yml` - No longer needed

## Next Steps for Publication

See `PUBLISHING.md` for detailed instructions, but in brief:

1. **Push to GitHub:**
   ```bash
   git remote remove origin
   git remote add origin https://github.com/guarzo/aa-wanderer-map.git
   git push -u origin main
   ```

2. **Set up PyPI Trusted Publishing:**
   - Register project at pypi.org
   - Configure trusted publisher in PyPI settings

3. **Create First Release:**
   - Go to GitHub releases
   - Create tag `v0.1.5`
   - Publish release
   - GitHub Actions will auto-publish to PyPI

## Testing Recommendations

Before publishing:

```bash
# Run tests locally
pip install tox
tox

# Test build process
pip install build
python -m build

# Verify package contents
tar -tzf dist/aa_wanderer_map-0.1.5.tar.gz
```

## Attribution

This fork maintains attribution to:
- **Original Author:** T'rahk Rokym (aa-wanderer)
- **Inspiration:** A-A-Ron (allianceauth-multiverse)
- **New Maintainer:** guarzo

## License

This project maintains the original MIT License from the upstream project.

---

**Fork Date:** October 26, 2025
**Maintainer:** guarzo
**Repository:** https://github.com/guarzo/aa-wanderer-map
