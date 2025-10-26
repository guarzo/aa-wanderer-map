# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased] - yyyy-mm-dd

## [0.1.5] - 2025-10-26

### About This Fork

This is a maintained fork of the [original aa-wanderer](https://gitlab.com/r0kym/aa-wanderer) by T'rahk Rokym. The original project appeared to be unmaintained and had critical bugs preventing installation and use. This fork aims to fix those issues and continue development.

### Fixed

- **Critical:** Fixed migration error where database tables were being queried before they were created
  - Added proper exception handling in `auth_hooks.py:add_del_callback()` to gracefully handle missing database tables during initial setup
  - Improved error logging in `apps.py:ready()` to be less alarming and more informative
  - This fix allows `python manage.py migrate` to complete successfully on fresh installations

### Changed

- Updated repository URLs to point to GitHub (https://github.com/guarzo/aa-wanderer-map)
- Updated package name to `aa-wanderer-map` to avoid conflicts with original package
- Updated author information
- Improved error messages to be more helpful for troubleshooting
