# Quick Template: Adding New Service to jetools.net

## 🚀 5-Minute Setup for New Subdomain Service

### Example: Adding `toolname.jetools.net`

## Step 1: Deploy Container in Unraid

**Docker Settings:**
```
Container Name: toolname-app
Network Type: Custom: dst-submittals-network
Port Mapping: 192.168.50.15:50XX → Container:XXXX
```

**Suggested Port Ranges:**
- Web Apps: 5001-5099
- APIs: 3002-3099  
- Admin Tools: 9000-9099

## Step 2: Verify Container Running

```bash
# Check container is on network
docker ps | grep toolname

# Test from NPM
docker exec Nginx-Proxy-Manager-Official curl -I http://toolname-app:XXXX/
```

## Step 3: Add Cloudflare DNS

1. Go to Cloudflare → jetools.net
2. Add DNS Record:
   - Type: `A`
   - Name: `toolname`
   - IPv4: [Your Public IP]
   - Proxy: 🟠 Proxied

## Step 4: Create NPM Proxy Host

1. Access NPM: `http://192.168.50.15:81`
2. Proxy Hosts → Add Proxy Host

**Details:**
```
Domain Names: toolname.jetools.net
Scheme: http
Forward Hostname: toolname-app
Forward Port: [container port]
Websockets Support: ON (if needed)
```

**SSL:**
```
Request New Certificate: ✅
Force SSL: ✅
```

**Advanced (if needed):**
```nginx
client_max_body_size 100M;
proxy_buffering off;
```

## Step 5: Test

- Internal: `http://192.168.50.15:50XX`
- External: `https://toolname.jetools.net`

## 📋 Copy-Paste Checklist

```markdown
- [ ] Container deployed on dst-submittals-network
- [ ] Port 50XX chosen and free
- [ ] Container accessible locally
- [ ] Cloudflare DNS added
- [ ] NPM proxy host created
- [ ] SSL certificate generated
- [ ] External access working
- [ ] Added to UNRAID_PRODUCTION_SETUP.md
```

## 🔧 Common Docker Run Commands

### Basic Web App
```bash
docker run -d \
  --name=toolname-app \
  --network=dst-submittals-network \
  -p 192.168.50.15:50XX:YYYY \
  -v /mnt/user/appdata/toolname:/config \
  --restart=unless-stopped \
  image:tag
```

### With Environment Variables
```bash
docker run -d \
  --name=toolname-app \
  --network=dst-submittals-network \
  -p 192.168.50.15:50XX:YYYY \
  -e ENV_VAR=value \
  -e TZ=America/Los_Angeles \
  -v /mnt/user/appdata/toolname:/config \
  --restart=unless-stopped \
  image:tag
```

## 🎯 Service Examples

| Service Type | Container Port | Host Port | Example |
|-------------|---------------|-----------|---------|
| Web UI | 8080 | 5001 | `dashboard.jetools.net` |
| API Service | 3000 | 3002 | `api.jetools.net` |
| Database UI | 8080 | 9001 | `db.jetools.net` |
| Monitoring | 3000 | 9002 | `monitor.jetools.net` |

## 🚨 Quick Fixes

**NPM can't reach service:**
```bash
docker network connect dst-submittals-network [container-name]
```

**Port already in use:**
```bash
netstat -tlnp | grep :PORT
# Change port in Unraid template
```

**SSL not working:**
- Check Cloudflare proxy is ON (🟠)
- Wait 2-3 minutes for certificate
- Check NPM logs

---

Save this template for quickly adding new services to your jetools.net domain!