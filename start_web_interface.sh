#!/bin/bash

echo "DST Submittals Generator - Web Interface"
echo "========================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.7+ and try again"
    echo "You can install it via Homebrew: brew install python"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Found Python version: $python_version"

# Create and activate virtual environment
echo "Setting up virtual environment..."
python3 -m venv dst_venv
source dst_venv/bin/activate

# Check if Flask is installed in the virtual environment
if ! python -c "import flask" &> /dev/null; then
    echo "Flask not found. Installing dependencies..."
    pip install -r requirements_mac.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies"
        exit 1
    fi
fi

# Create necessary directories
mkdir -p uploads
mkdir -p web_outputs
mkdir -p templates

echo "Starting web interface..."
echo
echo "Access the interface at: http://127.0.0.1:5001 (local)"
echo "Network access: http://$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n1):5001"
echo
echo "SHUTDOWN OPTIONS:"
echo "  - Press Ctrl+C in this window for graceful shutdown, OR"
echo "  - Run ./shutdown_web_interface.sh from another window, OR"
echo "  - POST to http://127.0.0.1:5001/shutdown endpoint"
echo

# Start the web interface
python3 web_interface.py --host 0.0.0.0 --port 5001
