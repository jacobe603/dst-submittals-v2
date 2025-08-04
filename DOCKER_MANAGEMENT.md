# Docker Container Management Strategy

## 🐳 Container Update Philosophy

### Current Approach: **Replace Containers**
We **replace** containers on each update rather than updating in-place.

```
[Old Container v1] → Stop → Remove → [New Container v2]
         ↑                                    ↑
    Old Image                            New Image
                     (rebuilt)
```

## 📊 What Happens During Updates

### Standard Update Process (`docker-compose up -d --build`)

1. **Code Update**
   ```bash
   git pull origin main  # Get latest code
   ```

2. **Image Rebuild**
   ```bash
   docker-compose build --no-cache
   ```
   - Creates NEW image with:
     - Latest code from GitHub
     - Fresh pip install of requirements.txt
     - Clean Python environment

3. **Container Recreation**
   ```bash
   docker-compose down     # Stop and remove old containers
   docker-compose up -d    # Create and start new containers
   ```

## 💾 Data Persistence Strategy

### What Survives Container Replacement

✅ **Persistent Volumes** (mounted directories):
```yaml
volumes:
  - /mnt/user/dst-submittals/outputs:/app/web_outputs      # PDFs persist
  - /mnt/user/appdata/dst-submittals-v2:/app/config        # Config persists
  - /mnt/user/dst-submittals/uploads:/app/uploads          # Uploads persist
```

❌ **What Gets Replaced**:
- Container filesystem
- Installed Python packages (reinstalled fresh)
- Application code (updated from image)
- Temp files in /tmp
- Container logs (unless mounted)

## 🔄 Update Strategies Comparison

| Strategy | Command | Downtime | Risk | Use Case |
|----------|---------|----------|------|----------|
| **Full Rebuild** (Recommended) | `docker-compose build --no-cache && docker-compose up -d` | ~30 seconds | Low | Production updates |
| **Quick Restart** | `docker-compose restart` | ~5 seconds | Medium | Config changes only |
| **Hot Reload** | `docker cp` + reload | None | High | Development only |
| **Clean Rebuild** | Remove all + rebuild | ~2 minutes | Low | Major issues |

## 🎯 Why We Replace Containers

### Benefits
1. **Clean State** - No accumulated temp files or memory leaks
2. **Dependency Consistency** - Fresh pip install ensures correct versions
3. **Predictable** - Same as initial deployment
4. **Security** - No lingering processes or files

### Drawbacks
1. **Brief Downtime** - 20-30 seconds typically
2. **Lost Container State** - In-memory caches cleared
3. **New Container ID** - Monitoring tools see new container

## 🛠️ Container Lifecycle Management

### Check Container Age
```bash
# See when containers were created
docker ps --format "table {{.Names}}\t{{.CreatedAt}}\t{{.Status}}"
```

### Container Health Over Time
```bash
# Monitor container resource usage
docker stats dst-submittals-app dst-gotenberg-service

# Check container logs for issues
docker logs dst-submittals-app --since 24h | grep ERROR
```

### When to Rebuild vs Restart

**Just Restart** when:
- Changing environment variables
- Minor config updates
- Clearing temporary issues

**Full Rebuild** when:
- Updating application code
- Changing requirements.txt
- Major version updates
- Monthly maintenance

## 🔧 Advanced Container Management

### Blue-Green Deployment (Zero Downtime)
```bash
# Start new container with different name
docker-compose -p dst-v2 up -d --build

# Test new container
curl http://localhost:5001/status-v2

# Switch traffic in NPM to new container
# Then remove old container
docker-compose -p dst-v1 down
```

### Container Versioning
```yaml
# In docker-compose.yml
services:
  dst-submittals:
    image: dst-submittals-v2:${VERSION:-latest}
    container_name: dst-submittals-app-${VERSION:-latest}
```

### Rollback Strategy
```bash
# Tag current version before update
docker tag dst-submittals-v2:local dst-submittals-v2:backup

# If update fails, restore
docker tag dst-submittals-v2:backup dst-submittals-v2:local
docker-compose up -d
```

## 📈 Container Monitoring

### Health Checks
Your containers have built-in health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/status-v2"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Monitor Health Status
```bash
# Watch container health
watch 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Get detailed health info
docker inspect dst-submittals-app | jq '.[0].State.Health'
```

## 🧹 Cleanup Old Images

After updates, clean up old images:

```bash
# Remove unused images
docker image prune -a

# See image disk usage
docker system df

# Full cleanup (careful!)
docker system prune -a --volumes
```

## 📝 Best Practices

1. **Always backup before major updates**
   ```bash
   docker commit dst-submittals-app dst-backup:$(date +%Y%m%d)
   ```

2. **Test updates in staging first** (if available)

3. **Schedule updates during low usage**

4. **Keep 2-3 old images for rollback**
   ```bash
   docker images | grep dst-submittals
   ```

5. **Monitor after updates**
   - Check logs: `docker logs -f dst-submittals-app`
   - Test functionality
   - Monitor resources

## 🚀 Quick Reference

```bash
# Standard update (recommended)
cd /mnt/user/appdata/dst-submittals-v2/source
git pull
docker-compose -f docker-compose.unraid.yml build --no-cache
docker-compose -f docker-compose.unraid.yml up -d

# Quick restart (no rebuild)
docker-compose -f docker-compose.unraid.yml restart

# Full cleanup and rebuild
docker-compose -f docker-compose.unraid.yml down
docker system prune -a
docker-compose -f docker-compose.unraid.yml up -d --build

# Check what would be updated
docker-compose -f docker-compose.unraid.yml pull --dry-run
```

---

**Remember:** Container replacement is the safest, most predictable update method. Brief downtime is worth the clean state!