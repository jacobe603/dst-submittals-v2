#!/bin/bash

# DST Submittals V2 - Server Update Script
# This script updates the Unraid server to the latest GitHub version
# Run from your dev machine: ./scripts/server-update.sh

set -e

# Configuration
UNRAID_HOST="192.168.50.15"
UNRAID_USER="root"
APP_DIR="/mnt/user/appdata/dst-submittals-v2/source"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== DST Submittals V2 - Server Update ===${NC}"
echo

# Check if we can connect to server
echo -e "${YELLOW}Checking connection to Unraid server...${NC}"
if ! ssh -q ${UNRAID_USER}@${UNRAID_HOST} exit; then
    echo -e "${RED}❌ Cannot connect to ${UNRAID_HOST}${NC}"
    echo "Please check:"
    echo "  - Server is online"
    echo "  - SSH is enabled"
    echo "  - Your SSH key is configured"
    exit 1
fi
echo -e "${GREEN}✅ Connected to server${NC}"

# Get current versions
echo -e "\n${YELLOW}Checking versions...${NC}"
LOCAL_VERSION=$(git rev-parse --short HEAD)
echo "Local version:  $LOCAL_VERSION"

GITHUB_VERSION=$(git ls-remote origin HEAD | cut -f1 | cut -c1-7)
echo "GitHub version: $GITHUB_VERSION"

SERVER_VERSION=$(ssh ${UNRAID_USER}@${UNRAID_HOST} "cd ${APP_DIR} && git rev-parse --short HEAD 2>/dev/null || echo 'unknown'")
echo "Server version: $SERVER_VERSION"

# Check if local is up to date with GitHub
if [ "$LOCAL_VERSION" != "$GITHUB_VERSION" ]; then
    echo -e "\n${YELLOW}⚠️  Your local version is different from GitHub${NC}"
    echo "Run 'git pull origin main' first to sync with GitHub"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if server needs update
if [ "$SERVER_VERSION" == "$GITHUB_VERSION" ]; then
    echo -e "\n${GREEN}✅ Server is already up to date!${NC}"
    exit 0
fi

# Perform update
echo -e "\n${YELLOW}Updating server from $SERVER_VERSION to $GITHUB_VERSION...${NC}"

ssh ${UNRAID_USER}@${UNRAID_HOST} << 'ENDSSH'
set -e

cd /mnt/user/appdata/dst-submittals-v2/source

echo "📥 Pulling latest from GitHub..."
git fetch origin
git reset --hard origin/main

echo "🔨 Rebuilding containers..."
docker-compose -f unraid-docker-compose.yml build --no-cache

echo "🔄 Restarting services..."
docker-compose -f unraid-docker-compose.yml down
docker-compose -f unraid-docker-compose.yml up -d

echo "⏳ Waiting for services to start..."
sleep 10

echo "📊 Checking service health..."
if docker ps | grep -q "dst-submittals-app.*healthy"; then
    echo "✅ DST Submittals is healthy"
else
    echo "⚠️  DST Submittals may not be healthy"
fi

if docker ps | grep -q "dst-gotenberg-service.*healthy"; then
    echo "✅ Gotenberg is healthy"  
else
    echo "⚠️  Gotenberg may not be healthy"
fi

echo "🔍 New version:"
git log --oneline -1
ENDSSH

# Test the service
echo -e "\n${YELLOW}Testing service availability...${NC}"
sleep 5
if curl -f -s -o /dev/null https://submittals.jetools.net/status-v2; then
    echo -e "${GREEN}✅ Service is responding at https://submittals.jetools.net${NC}"
else
    echo -e "${YELLOW}⚠️  Service may not be fully ready yet${NC}"
    echo "Check manually at https://submittals.jetools.net"
fi

echo -e "\n${GREEN}=== Update Complete ===${NC}"
echo
echo "Next steps:"
echo "  1. Visit https://submittals.jetools.net"
echo "  2. Test file upload functionality"
echo "  3. Check cleanup status in web interface"
echo
echo "If issues occur, rollback with:"
echo "  ssh ${UNRAID_USER}@${UNRAID_HOST} 'cd ${APP_DIR} && git reset --hard HEAD~1 && docker-compose -f unraid-docker-compose.yml restart'"