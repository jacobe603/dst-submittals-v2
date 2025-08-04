#!/bin/bash

echo "🚀 Starting DST Submittals Generator V2 on Mac"
echo "=============================================="

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    echo "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is not running"
    echo "Please start Docker Desktop"
    exit 1
fi

echo "✅ Docker is available"

# Start Gotenberg service
echo "📦 Starting Gotenberg service..."
docker run -d \
    --name gotenberg-service \
    -p 3000:3000 \
    --restart unless-stopped \
    gotenberg/gotenberg:8

# Wait for Gotenberg to be ready
echo "⏳ Waiting for Gotenberg to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:3000/health > /dev/null 2>&1; then
        echo "✅ Gotenberg is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Gotenberg failed to start within 30 seconds"
        exit 1
    fi
    sleep 1
done

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements_mac.txt
else
    echo "✅ Virtual environment found"
    source venv/bin/activate
fi

# Test the system
echo "🧪 Running system tests..."
python test_v2_system.py

# Check if test passed
if [ $? -eq 0 ]; then
    echo ""
    echo "🌐 Starting web interface..."
    echo "📱 Access the application at: http://127.0.0.1:5000"
    echo "🔧 V2 Status endpoint: http://127.0.0.1:5000/status-v2"
    echo ""
    echo "Press Ctrl+C to stop the server"
    
    # Start the web interface
    python web_interface.py
else
    echo "❌ System tests failed. Please check the output above."
    exit 1
fi