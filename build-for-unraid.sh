#!/bin/bash

# DST Submittals V2 - Unraid Build Script
# Run this on your Unraid server to build and deploy the containers

set -e

echo "=== DST Submittals V2 - Unraid Deployment ==="
echo

# Check if running on Unraid
if [ ! -d "/mnt/user" ]; then
    echo "⚠️  Warning: This doesn't appear to be an Unraid system"
    echo "   Expected /mnt/user directory not found"
    echo
fi

# Set up directories
echo "📁 Creating directories..."
mkdir -p /mnt/user/appdata/dst-submittals-v2
mkdir -p /mnt/user/dst-submittals/{outputs,uploads,documents}

# Clone or update repository
APP_DIR="/mnt/user/appdata/dst-submittals-v2/source"
if [ -d "$APP_DIR" ]; then
    echo "🔄 Updating existing repository..."
    cd "$APP_DIR"
    git pull
else
    echo "📥 Cloning repository..."
    git clone https://github.com/jacobe603/dst-submittals-v2.git "$APP_DIR"
    cd "$APP_DIR"
fi

# Check Docker and Docker Compose
echo "🐳 Checking Docker setup..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Use docker compose if available, otherwise docker-compose
DOCKER_COMPOSE_CMD="docker-compose"
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
$DOCKER_COMPOSE_CMD -f unraid-docker-compose.yml down || true

# Build and start services
echo "🔨 Building and starting services..."
$DOCKER_COMPOSE_CMD -f unraid-docker-compose.yml up -d --build

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "🔍 Checking service status..."
if curl -f http://localhost:3000/health &> /dev/null; then
    echo "✅ Gotenberg service is healthy"
else
    echo "❌ Gotenberg service is not responding"
fi

if curl -f http://localhost:5000/status-v2 &> /dev/null; then
    echo "✅ DST Submittals service is healthy"
else
    echo "❌ DST Submittals service is not responding"
fi

# Show container status
echo
echo "📊 Container Status:"
$DOCKER_COMPOSE_CMD -f unraid-docker-compose.yml ps

echo
echo "🎉 Deployment complete!"
echo
echo "📍 Access your DST Submittals V2 interface at:"
echo "   http://$(hostname -I | awk '{print $1}'):5000"
echo "   or"
echo "   http://localhost:5000"
echo
echo "🔧 Management commands:"
echo "   View logs:    $DOCKER_COMPOSE_CMD -f unraid-docker-compose.yml logs -f"
echo "   Stop:         $DOCKER_COMPOSE_CMD -f unraid-docker-compose.yml down"
echo "   Restart:      $DOCKER_COMPOSE_CMD -f unraid-docker-compose.yml restart"
echo "   Update:       $0  (run this script again)"
echo