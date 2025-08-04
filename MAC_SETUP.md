# Mac Setup Guide for DST Submittals Generator

This guide will help you get the DST Submittals Generator running on your Mac.

## Prerequisites

1. **Python 3.7+**: Make sure you have Python 3 installed. You can check by running:
   ```bash
   python3 --version
   ```
   
   If Python is not installed, you can install it via Homebrew:
   ```bash
   brew install python
   ```

2. **pip3**: This should come with Python 3, but you can verify with:
   ```bash
   pip3 --version
   ```

## Quick Start

### Option 1: Local Access Only
Run the web interface for local access only:
```bash
./start_web_interface.sh
```

### Option 2: Network Access
Run the web interface with network access (other devices on your network can access it):
```bash
./start_web_interface_network.sh
```

## What the Scripts Do

The startup scripts will:
1. Check if Python 3 is installed
2. Install required dependencies (if not already installed)
3. Create necessary directories (`uploads`, `web_outputs`, `templates`)
4. Start the web interface on port 5000

## Accessing the Interface

- **Local access**: http://127.0.0.1:5000
- **Network access**: http://YOUR_IP_ADDRESS:5000 (shown when you start the network script)

## Shutting Down

### Option 1: Graceful Shutdown
Press `Ctrl+C` in the terminal where the server is running.

### Option 2: Shutdown Script
Run the shutdown script from another terminal:
```bash
./shutdown_web_interface.sh
```

### Option 3: HTTP Endpoint
Send a POST request to: http://127.0.0.1:5000/shutdown

## Troubleshooting

### Permission Denied
If you get a permission error when running the scripts, make sure they're executable:
```bash
chmod +x *.sh
```

### Port Already in Use
If port 5000 is already in use, the shutdown script will help clear it:
```bash
./shutdown_web_interface.sh
```

### Python Not Found
If Python 3 is not found, install it via Homebrew:
```bash
brew install python
```

### Dependencies Installation Issues
If you have issues installing dependencies, try:
```bash
pip3 install --upgrade pip
pip3 install -r requirements_mac.txt
```

## Files Created

- `start_web_interface.sh` - Starts the web interface for local access
- `start_web_interface_network.sh` - Starts the web interface with network access
- `shutdown_web_interface.sh` - Gracefully shuts down the web interface
- `requirements_mac.txt` - Mac-specific Python dependencies

## Security Note

The network access script exposes the interface to your entire network. Only use it on trusted networks. 