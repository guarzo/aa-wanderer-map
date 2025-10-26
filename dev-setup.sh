#!/bin/bash

# Development setup script for aa-wanderer-map
# This script sets up a development environment with virtual environment and dependencies

set -e  # Exit on error

echo "=================================="
echo "aa-wanderer-map Development Setup"
echo "=================================="
echo ""

# Check Python version
PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python"
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo "❌ Error: Python 3 is not installed or not in PATH"
        exit 1
    fi
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "✓ Found Python: $PYTHON_VERSION"

# Check minimum Python version (3.10)
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "❌ Error: Python 3.10 or higher is required (you have $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python version is compatible"
echo ""

# Check for system dependencies
echo "🔍 Checking system dependencies..."
MISSING_DEPS=()

# Check for pkg-config
if ! command -v pkg-config &> /dev/null; then
    MISSING_DEPS+=("pkg-config")
fi

# Check for mysql_config or mariadb_config
if ! command -v mysql_config &> /dev/null && ! command -v mariadb_config &> /dev/null; then
    MISSING_DEPS+=("mysql-dev OR mariadb-dev")
fi

# Check for Python dev headers
if [ ! -f "/usr/include/python${PYTHON_MAJOR}.${PYTHON_MINOR}/Python.h" ] && \
   [ ! -f "/usr/local/include/python${PYTHON_MAJOR}.${PYTHON_MINOR}/Python.h" ]; then
    MISSING_DEPS+=("python3-dev")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "⚠️  Missing system dependencies detected!"
    echo ""
    echo "The following packages are required but not found:"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo "Install them with:"
    echo ""
    echo "Ubuntu/Debian:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y pkg-config python3-dev default-libmysqlclient-dev build-essential"
    echo ""
    echo "Or for MariaDB:"
    echo "  sudo apt-get install -y pkg-config python3-dev libmariadb-dev build-essential"
    echo ""
    echo "Fedora/RHEL/CentOS:"
    echo "  sudo dnf install -y pkg-config python3-devel mysql-devel gcc"
    echo ""
    echo "macOS:"
    echo "  brew install pkg-config mysql"
    echo ""
    echo "Do you want to continue anyway? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Exiting. Please install the required dependencies and run this script again."
        exit 1
    fi
else
    echo "✓ System dependencies found"
fi
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Remove it? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -rf venv
        $PYTHON_CMD -m venv venv
        echo "✓ Virtual environment recreated"
    else
        echo "✓ Using existing virtual environment"
    fi
else
    $PYTHON_CMD -m venv venv
    echo "✓ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    VENV_ACTIVATED=true
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    VENV_ACTIVATED=true
else
    echo "❌ Error: Could not find activation script"
    exit 1
fi
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"
echo ""

# Install package in editable mode
echo "📥 Installing aa-wanderer-map in editable mode..."
pip install -e . --quiet
echo "✓ Package installed"
echo ""

# Install development dependencies
echo "📥 Installing development dependencies..."
pip install tox build twine black isort flake8 --quiet
echo "✓ Development dependencies installed"
echo ""

# Check for Redis (needed for tests)
echo "🔍 Checking for Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✓ Redis is running"
    else
        echo "⚠️  Redis is installed but not running"
        echo "   Start it with: redis-server --daemonize yes"
    fi
else
    echo "⚠️  Redis is not installed (required for running tests)"
    echo "   Install it with:"
    echo "   - Ubuntu/Debian: sudo apt-get install redis-server"
    echo "   - macOS: brew install redis"
    echo "   - Other: See https://redis.io/download"
fi
echo ""

echo "=================================="
echo "✨ Setup Complete!"
echo "=================================="
echo ""
echo "Virtual environment is activated and ready to use."
echo ""
echo "Quick Start Commands:"
echo "  • Run tests:           tox"
echo "  • Run specific test:   tox -e py310-django42"
echo "  • Format code:         black ."
echo "  • Check imports:       isort . --check-only"
echo "  • Run linter:          flake8 wanderer/"
echo "  • Build package:       python -m build"
echo "  • Deactivate venv:     deactivate"
echo ""
echo "To activate this environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "Happy coding! 🚀"
