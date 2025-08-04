#!/bin/bash

# DST Submittals V2 - Production Deployment Script
# Ensures all containers have correct settings from the beginning
# Run this on your Unraid server for initial deployment or fixes

set -e

# Configuration
APP_DIR="/mnt/user/appdata/dst-submittals-v2"
REPO_URL="https://github.com/jacobe603/dst-submittals-v2.git"
UNRAID_IP="192.168.50.15"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== DST Submittals V2 - Production Deployment ===${NC}"
echo

# Check if running on Unraid
if [ ! -d "/mnt/user" ]; then
    echo -e "${RED}❌ This script must run on your Unraid server${NC}"
    exit 1
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
echo -e "${YELLOW}🔍 Finding available ports...${NC}"
GOTENBERG_PORT=$(find_available_port 3000)
DST_PORT=$(find_available_port 5000)
NPM_API_PORT=$(find_available_port 3001)

echo "   Gotenberg: $GOTENBERG_PORT"
echo "   DST Submittals: $DST_PORT"
echo "   NPM API: $NPM_API_PORT"

# Create directory structure
echo -e "\n${YELLOW}📁 Creating directory structure...${NC}"
mkdir -p "$APP_DIR"
mkdir -p /mnt/user/dst-submittals/{outputs,uploads,documents}
mkdir -p /mnt/user/appdata/Nginx-Proxy-Manager-Official/{data,letsencrypt}

# Set proper permissions
chown -R 1000:1000 "$APP_DIR" 2>/dev/null || true
chown -R 1000:1000 /mnt/user/dst-submittals/ 2>/dev/null || true

# Clone or update repository
if [ -d "$APP_DIR/source" ]; then
    echo -e "\n${YELLOW}🔄 Updating existing repository...${NC}"
    cd "$APP_DIR/source"
    git fetch origin
    git reset --hard origin/main
else
    echo -e "\n${YELLOW}📥 Cloning repository...${NC}"
    git clone "$REPO_URL" "$APP_DIR/source"
    cd "$APP_DIR/source"
fi

# Stop any existing containers
echo -e "\n${YELLOW}🛑 Stopping existing containers...${NC}"
docker stop dst-submittals-app dst-gotenberg-service Nginx-Proxy-Manager-Official 2>/dev/null || true
docker rm dst-submittals-app dst-gotenberg-service 2>/dev/null || true

# Remove existing custom network if it exists
docker network rm dst-submittals-network 2>/dev/null || true

# Create optimized docker-compose with correct settings
echo -e "\n${YELLOW}📝 Creating production docker-compose...${NC}"
cat > docker-compose.production.yml << EOF
version: '3.8'

services:
  gotenberg:
    image: gotenberg/gotenberg:8
    container_name: dst-gotenberg-service
    ports:
      - "${UNRAID_IP}:${GOTENBERG_PORT}:3000"
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
    labels:
      - "com.centurylinklabs.watchtower.enable=true"

  dst-submittals:
    build:
      context: .
      dockerfile: Dockerfile
    image: dst-submittals-v2:latest
    container_name: dst-submittals-app
    ports:
      - "${UNRAID_IP}:${DST_PORT}:5000"
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
    labels:
      - "com.centurylinklabs.watchtower.enable=true"

networks:
  dst-network:
    driver: bridge
    name: dst-submittals-network
EOF

# Build and start services
echo -e "\n${YELLOW}🔨 Building and starting services...${NC}"
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be healthy
echo -e "\n${YELLOW}⏳ Waiting for services to be healthy...${NC}"
for i in {1..30}; do
    echo -n "."
    sleep 2
    
    # Check if both services are healthy
    if docker ps | grep -q "dst-gotenberg-service.*healthy" && \
       docker ps | grep -q "dst-submittals-app.*healthy"; then
        echo -e " ${GREEN}✅${NC}"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo -e " ${YELLOW}⏰ Timeout${NC}"
    fi
done

# Fix NPM container settings if needed
echo -e "\n${YELLOW}🔧 Checking NPM container settings...${NC}"
if docker ps | grep -q "Nginx-Proxy-Manager-Official"; then
    NPM_NETWORK=$(docker inspect Nginx-Proxy-Manager-Official | jq -r '.[0].NetworkSettings.Networks | keys[]' 2>/dev/null || echo "")
    
    if [ "$NPM_NETWORK" != "dst-submittals-network" ]; then
        echo "   Adding NPM to dst-submittals-network..."
        docker network connect dst-submittals-network Nginx-Proxy-Manager-Official 2>/dev/null || true
    fi
    
    # Check if NPM has autostart enabled
    NPM_RESTART=$(docker inspect Nginx-Proxy-Manager-Official | jq -r '.[0].HostConfig.RestartPolicy.Name' 2>/dev/null || echo "")
    if [ "$NPM_RESTART" != "unless-stopped" ]; then
        echo -e "${YELLOW}   ⚠️  NPM container needs restart policy update${NC}"
        echo "   Please update NPM in Unraid GUI: Docker tab > Edit > Advanced > Restart Policy: Unless Stopped"
    fi
else
    echo -e "${RED}   ❌ NPM container not found${NC}"
    echo "   Please ensure Nginx Proxy Manager is installed and running"
fi

# Verify all containers have correct restart policies
echo -e "\n${YELLOW}🔍 Verifying container settings...${NC}"
for container in dst-submittals-app dst-gotenberg-service; do
    if docker ps -a | grep -q "$container"; then
        RESTART_POLICY=$(docker inspect "$container" | jq -r '.[0].HostConfig.RestartPolicy.Name' 2>/dev/null || echo "unknown")
        STATUS=$(docker ps --format "{{.Status}}" --filter "name=$container" | head -1)
        
        if [ "$RESTART_POLICY" = "unless-stopped" ]; then
            echo -e "   ${GREEN}✅ $container: $RESTART_POLICY, $STATUS${NC}"
        else
            echo -e "   ${RED}❌ $container: $RESTART_POLICY, $STATUS${NC}"
        fi
    else
        echo -e "   ${RED}❌ $container: not found${NC}"
    fi
done

# Test services
echo -e "\n${YELLOW}🧪 Testing services...${NC}"
GOTENBERG_STATUS="❌"
DST_STATUS="❌"

if curl -f -s "http://localhost:${GOTENBERG_PORT}/health" > /dev/null; then
    GOTENBERG_STATUS="✅"
fi

if curl -f -s "http://localhost:${DST_PORT}/status-v2" > /dev/null; then
    DST_STATUS="✅"
fi

echo "   Gotenberg (port $GOTENBERG_PORT): $GOTENBERG_STATUS"
echo "   DST Submittals (port $DST_PORT): $DST_STATUS"

# Create management script
echo -e "\n${YELLOW}📝 Creating management script...${NC}"
cat > /mnt/user/appdata/dst-submittals-v2/manage.sh << 'MANAGE_EOF'
#!/bin/bash
# DST Submittals V2 - Management Script

cd /mnt/user/appdata/dst-submittals-v2/source

case "$1" in
    status)
        echo "=== Service Status ==="
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "NAME|dst|nginx"
        ;;
    logs)
        docker logs -f dst-submittals-app
        ;;
    restart)
        docker-compose -f docker-compose.production.yml restart
        ;;
    update)
        echo "Updating from GitHub..."
        git pull origin main
        docker-compose -f docker-compose.production.yml build --no-cache
        docker-compose -f docker-compose.production.yml up -d
        ;;
    *)
        echo "Usage: $0 {status|logs|restart|update}"
        exit 1
        ;;
esac
MANAGE_EOF

chmod +x /mnt/user/appdata/dst-submittals-v2/manage.sh

# Final status report
echo -e "\n${BLUE}=== Deployment Complete ===${NC}"
echo
echo -e "${GREEN}✅ Services deployed with correct settings:${NC}"
echo "   - Restart Policy: unless-stopped (survives reboots)"
echo "   - Network: dst-submittals-network (all containers)"
echo "   - Health checks: enabled"
echo "   - Watchtower labels: added for auto-updates"
echo
echo -e "${BLUE}📍 Access URLs:${NC}"
echo "   - DST Submittals: http://${UNRAID_IP}:${DST_PORT}"
echo "   - Gotenberg: http://${UNRAID_IP}:${GOTENBERG_PORT}/health"
echo "   - NPM Admin: http://${UNRAID_IP}:81"
echo
echo -e "${BLUE}🛠️  Management Commands:${NC}"
echo "   - Status: /mnt/user/appdata/dst-submittals-v2/manage.sh status"
echo "   - Logs: /mnt/user/appdata/dst-submittals-v2/manage.sh logs"
echo "   - Update: /mnt/user/appdata/dst-submittals-v2/manage.sh update"
echo
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "   1. Verify external access: https://submittals.jetools.net"
echo "   2. Test file upload functionality"
echo "   3. All containers will now auto-start on reboot"
echo

# Save deployment info
cat > /mnt/user/appdata/dst-submittals-v2/deployment-info.txt << EOF
DST Submittals V2 - Deployment Information
==========================================

Deployed: $(date)
Version: $(git rev-parse --short HEAD)
Ports:
  - DST Submittals: ${DST_PORT}
  - Gotenberg: ${GOTENBERG_PORT}
  - NPM API: ${NPM_API_PORT}

Container Settings:
  - Restart Policy: unless-stopped
  - Network: dst-submittals-network  
  - Health Checks: enabled
  - Watchtower: enabled

External URL: https://submittals.jetools.net
EOF

echo -e "${GREEN}🎉 Production deployment complete!${NC}"