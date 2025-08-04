#!/bin/bash

# DST Submittals V2 - Version Sync Checker
# Checks if GitHub, local, and server are all in sync

# Configuration
UNRAID_HOST="192.168.50.15"
UNRAID_USER="root"
APP_DIR="/mnt/user/appdata/dst-submittals-v2/source"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== DST Submittals V2 - Version Sync Check ===${NC}"
echo

# Get versions
echo "Checking versions across all systems..."
echo

LOCAL_VERSION=$(git rev-parse --short HEAD)
LOCAL_BRANCH=$(git branch --show-current)
GITHUB_VERSION=$(git ls-remote origin HEAD | cut -f1 | cut -c1-7)
SERVER_VERSION=$(ssh -q ${UNRAID_USER}@${UNRAID_HOST} "cd ${APP_DIR} && git rev-parse --short HEAD 2>/dev/null" || echo "error")

# Display versions
echo -e "${BLUE}📍 Local (Dev)${NC}"
echo "   Branch:  $LOCAL_BRANCH"
echo "   Version: $LOCAL_VERSION"
echo "   Path:    $(pwd)"
echo

echo -e "${BLUE}🌐 GitHub${NC}"
echo "   Branch:  main"
echo "   Version: $GITHUB_VERSION"
echo "   URL:     https://github.com/jacobe603/dst-submittals-v2"
echo

echo -e "${BLUE}🖥️  Server (Unraid)${NC}"
echo "   Host:    $UNRAID_HOST"
echo "   Version: $SERVER_VERSION"
echo "   Path:    $APP_DIR"
echo

# Check sync status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}Sync Status:${NC}"
echo

ALL_SYNCED=true

# Check local vs GitHub
if [ "$LOCAL_VERSION" == "$GITHUB_VERSION" ]; then
    echo -e "  Local ↔ GitHub:  ${GREEN}✅ In sync${NC}"
else
    echo -e "  Local ↔ GitHub:  ${RED}❌ Out of sync${NC}"
    echo "    → Run: git pull origin main"
    ALL_SYNCED=false
fi

# Check server vs GitHub
if [ "$SERVER_VERSION" == "$GITHUB_VERSION" ]; then
    echo -e "  Server ↔ GitHub: ${GREEN}✅ In sync${NC}"
else
    echo -e "  Server ↔ GitHub: ${RED}❌ Out of sync${NC}"
    echo "    → Run: ./scripts/server-update.sh"
    ALL_SYNCED=false
fi

# Check local vs server
if [ "$LOCAL_VERSION" == "$SERVER_VERSION" ]; then
    echo -e "  Local ↔ Server:  ${GREEN}✅ In sync${NC}"
else
    echo -e "  Local ↔ Server:  ${YELLOW}⚠️  Different versions${NC}"
    ALL_SYNCED=false
fi

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Overall status
if [ "$ALL_SYNCED" = true ]; then
    echo -e "${GREEN}✅ All systems are in sync!${NC}"
else
    echo -e "${YELLOW}⚠️  Systems are out of sync${NC}"
    echo
    echo "Recommended actions:"
    echo "  1. Commit and push local changes: git add . && git commit -m 'message' && git push"
    echo "  2. Pull latest from GitHub: git pull origin main"
    echo "  3. Update server: ./scripts/server-update.sh"
fi

# Check for uncommitted changes
echo
echo -e "${BLUE}Local Changes:${NC}"
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  You have uncommitted changes:${NC}"
    git status --short
    echo
    echo "Commit these before syncing!"
else
    echo -e "${GREEN}✅ No uncommitted changes${NC}"
fi