# DST Submittals V2 - Maintenance & Version Control Guide

## 🎯 Source of Truth: GitHub

**Repository:** https://github.com/jacobe603/dst-submittals-v2  
**Branch:** `main` (production)  
**Dev Branch:** `develop` (optional for testing)

## 📊 Current Infrastructure

```
GitHub (Source of Truth)
    ↓
Dev Computer (Mac) - Development & Testing
    ↓
Unraid Server (192.168.50.15) - Production
```

## 🔄 Maintenance Workflow

### 1. Development Workflow (On Your Mac)

```bash
# Always start by pulling latest from GitHub
cd ~/dst-submittals-generator
git pull origin main

# Make your changes
# ... edit files ...

# Test locally
python web_interface.py

# Commit and push to GitHub
git add .
git commit -m "feat: Description of changes"
git push origin main
```

### 2. Server Update Workflow (On Unraid)

#### Manual Update (Current Method)

SSH into your Unraid server:

```bash
# Navigate to the app directory
cd /mnt/user/appdata/dst-submittals-v2/source

# Check current version
git log --oneline -1

# Pull latest changes from GitHub
git pull origin main

# Rebuild the Docker container with new code
docker-compose -f docker-compose.unraid.yml build --no-cache

# Restart services
docker-compose -f docker-compose.unraid.yml down
docker-compose -f docker-compose.unraid.yml up -d

# Verify services are healthy
docker ps | grep dst
```

#### Quick Update Script

Create this script on your Unraid server:

```bash
#!/bin/bash
# Save as: /mnt/user/appdata/dst-submittals-v2/update.sh

cd /mnt/user/appdata/dst-submittals-v2/source

echo "🔄 DST Submittals V2 - Update Script"
echo "Current version:"
git log --oneline -1

echo -e "\n📥 Pulling latest from GitHub..."
git pull origin main

echo -e "\n🔨 Rebuilding containers..."
docker-compose -f docker-compose.unraid.yml build --no-cache

echo -e "\n🔄 Restarting services..."
docker-compose -f docker-compose.unraid.yml down
docker-compose -f docker-compose.unraid.yml up -d

echo -e "\n✅ Update complete! New version:"
git log --oneline -1

echo -e "\n📊 Service status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep dst
```

Make it executable: `chmod +x /mnt/user/appdata/dst-submittals-v2/update.sh`

## 🤖 Automated Deployment Options

### Option 1: GitHub Webhook + Watchtower

Install Watchtower on Unraid to auto-update containers:

```yaml
# Add to your docker-compose.unraid.yml
watchtower:
  image: containrrr/watchtower
  container_name: watchtower
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  environment:
    - WATCHTOWER_CLEANUP=true
    - WATCHTOWER_INCLUDE_STOPPED=false
    - WATCHTOWER_SCHEDULE=0 0 3 * * *  # Daily at 3 AM
  labels:
    - "com.centurylinklabs.watchtower.enable=false"
```

### Option 2: GitHub Actions Auto-Deploy

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Unraid

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Unraid via SSH
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.UNRAID_HOST }}
        username: ${{ secrets.UNRAID_USER }}
        key: ${{ secrets.UNRAID_SSH_KEY }}
        script: |
          cd /mnt/user/appdata/dst-submittals-v2/source
          git pull origin main
          docker-compose -f docker-compose.unraid.yml build --no-cache
          docker-compose -f docker-compose.unraid.yml restart
```

### Option 3: Cron Job on Unraid

Add to Unraid's User Scripts plugin:

```bash
#!/bin/bash
# Name: Update DST Submittals
# Schedule: Daily at 2 AM

/mnt/user/appdata/dst-submittals-v2/update.sh >> /mnt/user/appdata/dst-submittals-v2/update.log 2>&1
```

## 📋 Version Management

### Check Current Versions

**On Dev Computer:**
```bash
cd ~/dst-submittals-generator
git log --oneline -1
```

**On Unraid Server:**
```bash
cd /mnt/user/appdata/dst-submittals-v2/source
git log --oneline -1
```

**In Running Container:**
```bash
docker exec dst-submittals-app cat /app/src/config.py | grep VERSION
```

### Version Tagging

When releasing a new version:

```bash
# On dev computer
git tag -a v2.1.0 -m "Release version 2.1.0"
git push origin v2.1.0
```

## 🔧 Maintenance Tasks

### Daily Checks
- ✅ Service health: `https://submittals.jetools.net/status-v2`
- ✅ Disk usage: Check Cleanup Status in web interface

### Weekly Tasks
- 📊 Review logs: `docker logs dst-submittals-app --tail 100`
- 🔄 Check for updates: Run update script
- 💾 Verify backups of `/mnt/user/dst-submittals/outputs`

### Monthly Tasks
- 🐳 Update base images: `docker pull python:3.11-slim`
- 🧹 Clean old Docker images: `docker image prune -a`
- 📈 Review usage patterns and performance

## 🚨 Rollback Procedure

If an update causes issues:

```bash
# On Unraid server
cd /mnt/user/appdata/dst-submittals-v2/source

# View recent commits
git log --oneline -5

# Rollback to previous commit
git reset --hard HEAD~1

# Or rollback to specific version
git reset --hard [commit-hash]

# Rebuild with old version
docker-compose -f docker-compose.unraid.yml build --no-cache
docker-compose -f docker-compose.unraid.yml restart
```

## 🔍 Troubleshooting Sync Issues

### Problem: Server has uncommitted changes

```bash
# Check what changed
git status
git diff

# If changes should be kept, commit them
git add .
git commit -m "Server-specific configuration"
git push origin main

# If changes should be discarded
git reset --hard origin/main
```

### Problem: Merge conflicts

```bash
# Stash local changes
git stash

# Pull latest
git pull origin main

# Apply stashed changes
git stash pop

# Resolve conflicts manually, then
git add .
git commit -m "Resolved merge conflicts"
git push origin main
```

## 📝 Development vs Production

### Development Environment (Mac)
```bash
# Use development settings
export FLASK_ENV=development
export DST_LOG_LEVEL=DEBUG

# Run locally
python web_interface.py --debug
```

### Production Environment (Unraid)
```bash
# Production settings (in docker-compose)
FLASK_ENV=production
DST_LOG_LEVEL=INFO
DST_CLEANUP_ON_STARTUP=true
```

## 🔐 Security Best Practices

1. **Never commit secrets** to GitHub
2. **Use environment variables** for sensitive data
3. **Keep `.env` files** in `.gitignore`
4. **Regular updates** for security patches
5. **Monitor logs** for suspicious activity

## 📊 Monitoring & Alerts

### Health Check Script
```bash
#!/bin/bash
# Add to Unraid User Scripts (hourly)

if ! curl -f https://submittals.jetools.net/status-v2 > /dev/null 2>&1; then
    echo "DST Submittals is DOWN!" | mail -s "Service Alert" your-email@example.com
fi
```

### Container Auto-Restart
Already configured with `restart: unless-stopped` in Docker

## 🎯 Quick Commands Reference

```bash
# Update server to latest GitHub version
ssh root@192.168.50.15 "/mnt/user/appdata/dst-submittals-v2/update.sh"

# Check versions everywhere
echo "GitHub:" && git ls-remote origin HEAD
echo "Local:" && git rev-parse HEAD  
echo "Server:" && ssh root@192.168.50.15 "cd /mnt/user/appdata/dst-submittals-v2/source && git rev-parse HEAD"

# Force server to match GitHub exactly
ssh root@192.168.50.15 "cd /mnt/user/appdata/dst-submittals-v2/source && git fetch && git reset --hard origin/main"
```

## 📅 Recommended Update Schedule

- **Development:** Continuous (as you code)
- **GitHub:** Push daily or after features complete
- **Production:** Weekly updates (or use auto-deploy for immediate)

---

**Remember:** GitHub is ALWAYS the source of truth. Never make changes directly on the server without pushing to GitHub first!