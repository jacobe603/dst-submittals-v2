#!/bin/bash

# DST Submittals V2 - Complete Unraid Deployment Script
# This script handles everything: ports, files, and deployment

set -e

echo "=== DST Submittals V2 - Complete Unraid Deployment ==="
echo

# Check if running as root (recommended for Unraid)
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  Warning: Not running as root. Some operations may fail."
    echo "   Consider running: sudo $0"
    echo
fi

# Check if running on Unraid
if [ ! -d "/mnt/user" ]; then
    echo "⚠️  Warning: This doesn't appear to be an Unraid system"
    echo "   Expected /mnt/user directory not found"
    echo
fi

# Function to find available port
find_available_port() {
    local start_port=$1
    local port=$start_port
    while netstat -ln 2>/dev/null | grep -q ":$port "; do
        port=$((port + 1))
        if [ $port -gt $((start_port + 100)) ]; then
            echo "ERROR: No available ports found starting from $start_port"
            exit 1
        fi
    done
    echo $port
}

# Find available ports
echo "🔍 Finding available ports..."
GOTENBERG_PORT=$(find_available_port 3000)
DST_PORT=$(find_available_port 5000)

echo "✅ Using ports: Gotenberg=$GOTENBERG_PORT, DST Submittals=$DST_PORT"

# Set up directories
echo "📁 Creating directories..."
APP_DIR="/mnt/user/appdata/dst-submittals-v2"
mkdir -p "$APP_DIR"
mkdir -p /mnt/user/dst-submittals/{outputs,uploads,documents}

# Clean up any existing deployment
echo "🧹 Cleaning up existing deployment..."
cd "$APP_DIR"
if [ -f "docker-compose.yml" ] || [ -f "unraid-docker-compose.yml" ]; then
    docker-compose down 2>/dev/null || true
    docker compose down 2>/dev/null || true
fi

# Remove old source if it exists
if [ -d "source" ]; then
    echo "🗑️  Removing old source directory..."
    rm -rf source
fi

# Clone fresh repository
echo "📥 Cloning repository..."
git clone https://github.com/jacobe603/dst-submittals-v2.git source
cd source

# Check required files exist
if [ ! -f "Dockerfile" ]; then
    echo "❌ Dockerfile not found in repository"
    exit 1
fi

if [ ! -f "requirements.txt" ] && [ ! -f "requirements_mac.txt" ]; then
    echo "❌ Requirements file not found in repository"
    exit 1
fi

# Create optimized docker-compose for Unraid
echo "📝 Creating Unraid-optimized docker-compose..."
cat > docker-compose.unraid.yml << EOF
version: '3.8'

services:
  gotenberg:
    image: gotenberg/gotenberg:8
    container_name: dst-gotenberg-service
    ports:
      - "${GOTENBERG_PORT}:3000"
    restart: unless-stopped
    environment:
      - GOTENBERG_LOG_LEVEL=INFO
      - GOTENBERG_API_TIMEOUT=120s
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
    image: dst-submittals-v2:local
    container_name: dst-submittals-app
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
      - TZ=America/Los_Angeles
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
    name: dst-submittals-network
EOF

# Determine docker compose command
DOCKER_COMPOSE_CMD="docker-compose"
if docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
fi

echo "🐳 Using Docker Compose command: $DOCKER_COMPOSE_CMD"

# Stop any existing containers with same names
echo "🛑 Stopping any existing containers..."
docker stop dst-gotenberg-service dst-submittals-app 2>/dev/null || true
docker rm dst-gotenberg-service dst-submittals-app 2>/dev/null || true

# Build and start services
echo "🔨 Building and starting services..."
echo "   This may take several minutes for the first build..."
$DOCKER_COMPOSE_CMD -f docker-compose.unraid.yml up -d --build

# Wait for services to be healthy
echo "⏳ Waiting for services to start (up to 2 minutes)..."
for i in {1..24}; do
    echo -n "."
    sleep 5
    
    # Check if both services are healthy
    if curl -f http://localhost:${GOTENBERG_PORT}/health &> /dev/null && \
       curl -f http://localhost:${DST_PORT}/status-v2 &> /dev/null; then
        echo " ✅"
        break
    fi
    
    if [ $i -eq 24 ]; then
        echo " ⏰ Timeout waiting for services"
    fi
done

# Check service status
echo
echo "🔍 Final service status check..."
GOTENBERG_STATUS="❌ Not responding"
DST_STATUS="❌ Not responding"

if curl -f http://localhost:${GOTENBERG_PORT}/health &> /dev/null; then
    GOTENBERG_STATUS="✅ Healthy"
fi

if curl -f http://localhost:${DST_PORT}/status-v2 &> /dev/null; then
    DST_STATUS="✅ Healthy"
fi

echo "   Gotenberg (port $GOTENBERG_PORT): $GOTENBERG_STATUS"
echo "   DST Submittals (port $DST_PORT): $DST_STATUS"

# Show container status
echo
echo "📊 Container Status:"
$DOCKER_COMPOSE_CMD -f docker-compose.unraid.yml ps

# Show service logs if any failures
if [[ "$GOTENBERG_STATUS" == *"Not responding"* ]] || [[ "$DST_STATUS" == *"Not responding"* ]]; then
    echo
    echo "🔍 Service logs (last 20 lines each):"
    echo "--- Gotenberg Logs ---"
    docker logs dst-gotenberg-service --tail 20 2>/dev/null || echo "No logs available"
    echo
    echo "--- DST Submittals Logs ---"
    docker logs dst-submittals-app --tail 20 2>/dev/null || echo "No logs available"
fi

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

echo
echo "🎉 Deployment Complete!"
echo
echo "📍 Access URLs:"
echo "   DST Submittals: http://$SERVER_IP:$DST_PORT"
echo "   Gotenberg API:  http://$SERVER_IP:$GOTENBERG_PORT/health"
echo
echo "📂 Data Directories:"
echo "   Config:     /mnt/user/appdata/dst-submittals-v2"
echo "   Outputs:    /mnt/user/dst-submittals/outputs"
echo "   Uploads:    /mnt/user/dst-submittals/uploads"
echo "   Documents:  /mnt/user/dst-submittals/documents"
echo
echo "🛠️  Management Commands:"
echo "   View logs:       cd $APP_DIR/source && $DOCKER_COMPOSE_CMD -f docker-compose.unraid.yml logs -f"
echo "   Stop services:   cd $APP_DIR/source && $DOCKER_COMPOSE_CMD -f docker-compose.unraid.yml down"
echo "   Restart:         cd $APP_DIR/source && $DOCKER_COMPOSE_CMD -f docker-compose.unraid.yml restart"
echo "   Update:          curl -sSL https://raw.githubusercontent.com/jacobe603/dst-submittals-v2/main/deploy-unraid.sh | bash"
echo
echo "💡 Next Steps:"
echo "   1. Open http://$SERVER_IP:$DST_PORT in your browser"
echo "   2. Upload some HVAC documents to test"
echo "   3. Check the cleanup settings in the web interface"
echo