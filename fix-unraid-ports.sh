#!/bin/bash

# DST Submittals V2 - Port Conflict Fix Script
# Run this on your Unraid server to resolve port conflicts

set -e

echo "=== DST Submittals V2 - Port Conflict Resolution ==="
echo

# Check what's using port 3000
echo "🔍 Checking what's using port 3000..."
PORT_USAGE=$(netstat -tlnp 2>/dev/null | grep :3000 || true)
if [ -n "$PORT_USAGE" ]; then
    echo "❌ Port 3000 is in use:"
    echo "$PORT_USAGE"
    echo
    echo "🔧 We'll use port 3001 for Gotenberg instead"
    GOTENBERG_PORT=3001
else
    echo "✅ Port 3000 is available"
    GOTENBERG_PORT=3000
fi

# Check what's using port 5000
echo "🔍 Checking what's using port 5000..."
PORT_USAGE=$(netstat -tlnp 2>/dev/null | grep :5000 || true)
if [ -n "$PORT_USAGE" ]; then
    echo "❌ Port 5000 is in use:"
    echo "$PORT_USAGE"
    echo
    echo "🔧 We'll use port 5001 for DST Submittals instead"
    DST_PORT=5001
else
    echo "✅ Port 5000 is available"
    DST_PORT=5000
fi

# Set up directories
echo "📁 Creating directories..."
mkdir -p /mnt/user/appdata/dst-submittals-v2
mkdir -p /mnt/user/dst-submittals/{outputs,uploads,documents}

# Navigate to app directory
APP_DIR="/mnt/user/appdata/dst-submittals-v2"
cd "$APP_DIR"

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f unraid-docker-compose.yml down 2>/dev/null || true
docker compose -f unraid-docker-compose.yml down 2>/dev/null || true

# Create custom docker-compose with available ports
echo "📝 Creating docker-compose with available ports..."
cat > unraid-docker-compose-custom.yml << EOF
version: '3.8'

services:
  gotenberg:
    image: gotenberg/gotenberg:8
    container_name: gotenberg-service-dst
    ports:
      - "${GOTENBERG_PORT}:3000"
    restart: unless-stopped
    environment:
      - GOTENBERG_LOG_LEVEL=INFO
    networks:
      - dst-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  dst-submittals:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: dst-submittals-v2-app
    ports:
      - "${DST_PORT}:5000"
    depends_on:
      gotenberg:
        condition: service_healthy
    environment:
      - DST_GOTENBERG_URL=http://gotenberg:3000
      - DST_QUALITY_MODE=high
      - DST_MAX_OUTPUT_FILES=50
      - DST_OUTPUT_RETENTION_DAYS=30
      - DST_CLEANUP_ON_STARTUP=true
      - DST_PERIODIC_CLEANUP_HOURS=24
      - DST_CONVERSION_TIMEOUT=300
      - DST_LOG_LEVEL=INFO
      - DST_LOG_TO_FILE=true
      - FLASK_ENV=production
    volumes:
      - /mnt/user/appdata/dst-submittals-v2:/app/config
      - /mnt/user/dst-submittals/outputs:/app/web_outputs
      - /mnt/user/dst-submittals/uploads:/app/uploads
      - /mnt/user/dst-submittals/documents:/app/documents
    networks:
      - dst-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/status-v2"]
      interval: 30s
      timeout: 10s  
      retries: 3
      start_period: 60s

networks:
  dst-network:
    driver: bridge
EOF

# Use docker compose if available, otherwise docker-compose
DOCKER_COMPOSE_CMD="docker-compose"
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
fi

# Build and start services with custom ports
echo "🔨 Building and starting services on available ports..."
$DOCKER_COMPOSE_CMD -f unraid-docker-compose-custom.yml up -d --build

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 15

# Check service status
echo "🔍 Checking service status..."
if curl -f http://localhost:${GOTENBERG_PORT}/health &> /dev/null; then
    echo "✅ Gotenberg service is healthy on port ${GOTENBERG_PORT}"
else
    echo "❌ Gotenberg service is not responding on port ${GOTENBERG_PORT}"
fi

if curl -f http://localhost:${DST_PORT}/status-v2 &> /dev/null; then
    echo "✅ DST Submittals service is healthy on port ${DST_PORT}"
else
    echo "❌ DST Submittals service is not responding on port ${DST_PORT}"
fi

# Show container status
echo
echo "📊 Container Status:"
$DOCKER_COMPOSE_CMD -f unraid-docker-compose-custom.yml ps

echo
echo "🎉 Deployment complete with custom ports!"
echo
echo "📍 Access your DST Submittals V2 interface at:"
echo "   http://$(hostname -I | awk '{print $1}'):${DST_PORT}"
echo "   or"
echo "   http://localhost:${DST_PORT}"
echo
echo "🔧 Services running on:"
echo "   DST Submittals: Port ${DST_PORT}"
echo "   Gotenberg:      Port ${GOTENBERG_PORT}"
echo
echo "🛠️  Management commands:"
echo "   View logs:    $DOCKER_COMPOSE_CMD -f unraid-docker-compose-custom.yml logs -f"
echo "   Stop:         $DOCKER_COMPOSE_CMD -f unraid-docker-compose-custom.yml down"
echo "   Restart:      $DOCKER_COMPOSE_CMD -f unraid-docker-compose-custom.yml restart"
echo