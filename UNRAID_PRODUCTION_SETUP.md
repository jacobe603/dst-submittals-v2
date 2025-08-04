# Production Setup - Unraid + NPM + Multiple Services

## 🎯 Working Configuration for jetools.net

This document captures the working production setup for hosting DST Submittals V2 and future services on Unraid using Nginx Proxy Manager.

## 📊 Current Infrastructure

### Network Architecture
```
Internet → Router → Unraid Server (192.168.50.15)
                    ├── NPM (dst-submittals-network)
                    ├── DST Submittals (dst-submittals-network)
                    ├── Gotenberg (dst-submittals-network)
                    └── Future Services (dst-submittals-network)
```

### Docker Network Configuration
- **Network Name:** `dst-submittals-network`
- **Network Type:** Custom Docker Bridge
- **All services on same network for internal communication**

## 🔧 Working Service Configuration

### Nginx Proxy Manager (NPM)
**Container:** `Nginx-Proxy-Manager-Official`  
**Network:** `dst-submittals-network`  
**Internal IP:** `172.21.0.4`  
**Port Mappings:**
- `192.168.50.15:80` → Container:80 (HTTP)
- `192.168.50.15:443` → Container:443 (HTTPS)
- `192.168.50.15:81` → Container:81 (Admin UI)
- `192.168.50.15:3001` → Container:3000 (NPM API - changed from 3000 to avoid conflict)

### DST Submittals V2
**Container:** `dst-submittals-app`  
**Network:** `dst-submittals-network`  
**Internal IP:** `172.21.0.3`  
**Port Mapping:** `192.168.50.15:5000` → Container:5000  
**Access URL:** https://submittals.jetools.net

### Gotenberg Service
**Container:** `dst-gotenberg-service`  
**Network:** `dst-submittals-network`  
**Internal IP:** `172.21.0.2`  
**Port Mapping:** `192.168.50.15:3000` → Container:3000

## 🌐 Router Configuration

### Port Forwarding Rules
```
External Port 80  → 192.168.50.15:80  (NPM HTTP)
External Port 443 → 192.168.50.15:443 (NPM HTTPS)
```

### DNS Configuration (Cloudflare)
```
Type: A Record
Name: submittals
Content: [Your Public IP]
Proxy: 🟠 Proxied
TTL: Auto
```

## 📝 NPM Proxy Host Configuration

### Working Settings for submittals.jetools.net

**Details Tab:**
```
Domain Names: submittals.jetools.net
Scheme: http
Forward Hostname/IP: dst-submittals-app
Forward Port: 5000
Cache Assets: OFF
Block Common Exploits: ON
Websockets Support: ON
```

**SSL Tab:**
```
SSL Certificate: Let's Encrypt
Force SSL: ON
HTTP/2 Support: ON
HSTS Enabled: ON
Email: [your-email]
```

**Advanced Tab:**
```nginx
# Large file upload support
client_max_body_size 500M;
client_body_timeout 300;

# Real-time progress support
proxy_buffering off;
proxy_cache off;

# Extended timeouts
proxy_connect_timeout 300;
proxy_send_timeout 300;
proxy_read_timeout 300;
```

## 🚀 Adding New Services to jetools.net

### Step 1: Deploy New Service Container

**Unraid Docker Configuration:**
```yaml
Network Type: Custom: dst-submittals-network
Port Mapping: [Choose unique host port]
```

### Step 2: Create NPM Proxy Host

**Template for new subdomain (e.g., `newservice.jetools.net`):**

**Details Tab:**
```
Domain Names: newservice.jetools.net
Scheme: http
Forward Hostname/IP: [container-name]
Forward Port: [container-internal-port]
Websockets Support: ON (if needed)
```

### Step 3: Add Cloudflare DNS

```
Type: A or CNAME
Name: newservice
Content: [Same as submittals]
Proxy: 🟠 Proxied
```

## 🔌 Port Management Strategy

### Reserved Ports

| Service | Host Port | Container Port | Purpose |
|---------|-----------|---------------|---------|
| NPM HTTP | 80 | 80 | Web traffic |
| NPM HTTPS | 443 | 443 | Secure traffic |
| NPM Admin | 81 | 81 | NPM management |
| NPM API | 3001 | 3000 | Internal API |
| Gotenberg | 3000 | 3000 | PDF conversion |
| DST Submittals | 5000 | 5000 | Main app |
| **Next Service** | 5001+ | varies | Future apps |

### Port Allocation Guidelines

1. **5000-5099:** Web applications
2. **3000-3099:** API services  
3. **8000-8099:** Development/testing
4. **9000-9099:** Monitoring/admin tools

## 🛠️ Common Operations

### Add New Service to Network

```bash
# If container already exists
docker network connect dst-submittals-network [container-name]

# Or specify in Unraid Docker template
Network Type: Custom: dst-submittals-network
```

### Test Container Connectivity

```bash
# From NPM to new service
docker exec Nginx-Proxy-Manager-Official curl -I http://[container-name]:[port]/

# Check network membership
docker network inspect dst-submittals-network
```

### Restart Services

```bash
# Restart individual service
docker restart [container-name]

# Restart all on network
docker restart $(docker ps -q --filter network=dst-submittals-network)
```

## 🔍 Troubleshooting

### NPM Can't Reach Service

1. **Verify same network:**
   ```bash
   docker inspect [container] | grep -A 5 "Networks"
   ```

2. **Test direct connection:**
   ```bash
   docker exec Nginx-Proxy-Manager-Official curl -I http://[container]:[port]/
   ```

3. **Check container name resolution:**
   ```bash
   docker exec Nginx-Proxy-Manager-Official nslookup [container-name]
   ```

### SSL Certificate Issues

1. **Check Cloudflare SSL mode:** Should be "Full (strict)"
2. **Verify DNS propagation:** `nslookup subdomain.jetools.net`
3. **Check NPM logs:** `docker logs Nginx-Proxy-Manager-Official --tail 50`

### Port Conflicts

1. **Check port usage:**
   ```bash
   netstat -tlnp | grep :[port]
   docker ps --format "table {{.Names}}\t{{.Ports}}"
   ```

2. **Change conflicting ports in Unraid Docker template**

## 📋 Service Addition Checklist

When adding a new service to jetools.net:

- [ ] Deploy container on `dst-submittals-network`
- [ ] Choose unique host port (check port list)
- [ ] Test container is accessible locally
- [ ] Add Cloudflare DNS record
- [ ] Create NPM proxy host entry
- [ ] Configure SSL certificate
- [ ] Test external access
- [ ] Document in this file
- [ ] Update port allocation table

## 🔒 Security Notes

1. **All services behind NPM:** Never expose service ports directly
2. **Use container names:** For internal communication (not IPs)
3. **Cloudflare proxy:** Enable for DDoS protection
4. **Regular updates:** Keep NPM and services updated
5. **Strong passwords:** Change all default credentials

## 📊 Current Service URLs

| Service | Internal Access | External URL | Status |
|---------|----------------|--------------|---------|
| DST Submittals V2 | http://192.168.50.15:5000 | https://submittals.jetools.net | ✅ Live |
| NPM Admin | http://192.168.50.15:81 | N/A (Internal only) | ✅ Live |
| Gotenberg | http://192.168.50.15:3000 | N/A (Internal only) | ✅ Live |

## 📝 Notes & Lessons Learned

1. **Network is critical:** All services must be on same Docker network
2. **Port 3000 conflict:** Changed NPM API port to 3001 to avoid Gotenberg conflict
3. **Container names work:** Use container names instead of IPs for reliability
4. **Unraid GUI is helpful:** Easier to manage networks via Unraid interface
5. **Test connectivity first:** Always verify NPM can reach service before adding proxy host

---

**Last Updated:** August 2025  
**Tested On:** Unraid 6.12+  
**Domain:** jetools.net  
**Server IP:** 192.168.50.15