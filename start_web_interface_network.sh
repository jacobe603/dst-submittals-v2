#!/bin/bash

echo "DST Submittals Generator - Web Interface (Network Access)"
echo "========================================================"
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

# Get the computer's IP address
ip_address=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n1)

echo "Starting web interface with network access..."
echo
echo "Local access:   http://127.0.0.1:5001"
echo "Network access: http://$ip_address:5001"
echo
echo "Other computers on your network can access this at:"
echo "  http://$ip_address:5001"
echo
echo "SECURITY WARNING: This exposes the interface to your entire network!"
echo "Only run this on trusted networks."
echo
echo "Press Ctrl+C to stop the server"
echo

# Start the web interface with network access
python3 web_interface.py --host 0.0.0.0 --port 5001
