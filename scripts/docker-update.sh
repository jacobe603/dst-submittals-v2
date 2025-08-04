#!/bin/bash

# DST Submittals V2 - Docker Update Management Script
# Provides different update strategies for Docker containers

set -e

# Configuration
APP_DIR="/mnt/user/appdata/dst-submittals-v2/source"
COMPOSE_FILE="docker-compose.unraid.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default to full rebuild
UPDATE_MODE=${1:-rebuild}

show_help() {
    echo -e "${BLUE}DST Submittals V2 - Docker Update Management${NC}"
    echo
    echo "Usage: $0 [mode]"
    echo
    echo "Modes:"
    echo "  rebuild   - Full rebuild and container replacement (default, recommended)"
    echo "  quick     - Just restart containers with new code"
    echo "  hot       - Update code without restart (risky)"
    echo "  clean     - Remove everything and rebuild from scratch"
    echo "  status    - Show current container status"
    echo
    echo "Examples:"
    echo "  $0              # Full rebuild (recommended)"
    echo "  $0 quick        # Quick restart"
    echo "  $0 status       # Check status"
    exit 0
}

check_status() {
    echo -e "${BLUE}=== Container Status ===${NC}"
    docker-compose -f $COMPOSE_FILE ps
    echo
    echo -e "${BLUE}=== Image Information ===${NC}"
    docker images | grep -E "dst-submittals|gotenberg" || echo "No images found"
    echo
    echo -e "${BLUE}=== Container Health ===${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.CreatedAt}}" | grep -E "dst|gotenberg"
}

rebuild_update() {
    echo -e "${GREEN}=== Full Rebuild and Replace ===${NC}"
    echo "This will replace containers with fresh versions"
    echo
    
    # Pull latest code
    echo -e "${YELLOW}📥 Pulling latest code...${NC}"
    git pull origin main
    
    # Build new images
    echo -e "${YELLOW}🔨 Building new Docker images...${NC}"
    docker-compose -f $COMPOSE_FILE build --no-cache
    
    # Stop and remove old containers
    echo -e "${YELLOW}🛑 Stopping old containers...${NC}"
    docker-compose -f $COMPOSE_FILE down
    
    # Start new containers
    echo -e "${YELLOW}🚀 Starting new containers...${NC}"
    docker-compose -f $COMPOSE_FILE up -d
    
    # Wait for health
    echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
    sleep 10
    
    # Check health
    if docker ps | grep -q "dst-submittals-app.*healthy"; then
        echo -e "${GREEN}✅ DST Submittals is healthy${NC}"
    else
        echo -e "${RED}❌ DST Submittals may not be healthy${NC}"
    fi
    
    echo -e "${GREEN}✅ Full rebuild complete!${NC}"
}

quick_update() {
    echo -e "${BLUE}=== Quick Update (Restart Only) ===${NC}"
    echo "This will restart containers with new code"
    echo
    
    # Pull latest code
    echo -e "${YELLOW}📥 Pulling latest code...${NC}"
    git pull origin main
    
    # Just restart containers (uses cached image)
    echo -e "${YELLOW}🔄 Restarting containers...${NC}"
    docker-compose -f $COMPOSE_FILE restart
    
    echo -e "${GREEN}✅ Quick restart complete!${NC}"
}

hot_update() {
    echo -e "${YELLOW}=== Hot Update (No Restart) ===${NC}"
    echo -e "${RED}⚠️  WARNING: This may cause issues. Use with caution!${NC}"
    echo
    
    # Pull latest code
    echo -e "${YELLOW}📥 Pulling latest code...${NC}"
    git pull origin main
    
    # Copy new code into running container
    echo -e "${YELLOW}📝 Copying code to running container...${NC}"
    docker cp ./src/. dst-submittals-app:/app/src/
    docker cp ./templates/. dst-submittals-app:/app/templates/
    docker cp ./web_interface.py dst-submittals-app:/app/
    
    # Reload Python app (Flask auto-reload if in debug mode)
    echo -e "${YELLOW}🔄 Triggering reload...${NC}"
    docker exec dst-submittals-app touch /app/web_interface.py
    
    echo -e "${GREEN}✅ Hot update complete (may need manual refresh)${NC}"
}

clean_rebuild() {
    echo -e "${RED}=== Clean Rebuild (Remove Everything) ===${NC}"
    echo -e "${RED}⚠️  This will remove all containers and images!${NC}"
    read -p "Are you sure? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    
    # Stop everything
    echo -e "${YELLOW}🛑 Stopping all containers...${NC}"
    docker-compose -f $COMPOSE_FILE down
    
    # Remove images
    echo -e "${YELLOW}🗑️  Removing old images...${NC}"
    docker rmi dst-submittals-v2:local 2>/dev/null || true
    docker rmi $(docker images -q --filter "dangling=true") 2>/dev/null || true
    
    # Pull latest code
    echo -e "${YELLOW}📥 Pulling latest code...${NC}"
    git pull origin main
    
    # Build fresh
    echo -e "${YELLOW}🔨 Building fresh images...${NC}"
    docker-compose -f $COMPOSE_FILE build --no-cache --pull
    
    # Start fresh
    echo -e "${YELLOW}🚀 Starting fresh containers...${NC}"
    docker-compose -f $COMPOSE_FILE up -d
    
    # Clean old images
    echo -e "${YELLOW}🧹 Cleaning unused images...${NC}"
    docker image prune -f
    
    echo -e "${GREEN}✅ Clean rebuild complete!${NC}"
}

# Main script
cd $APP_DIR

case $UPDATE_MODE in
    rebuild)
        rebuild_update
        ;;
    quick)
        quick_update
        ;;
    hot)
        hot_update
        ;;
    clean)
        clean_rebuild
        ;;
    status)
        check_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown mode: $UPDATE_MODE${NC}"
        show_help
        ;;
esac

echo
echo -e "${BLUE}=== Final Status ===${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "NAME|dst|gotenberg"