# DST Submittals V2 - Unraid Setup Guide

Complete guide for hosting DST Submittals Generator V2 on Unraid with Docker containers.

## 🚀 Quick Start (Recommended)

### Option 1: Automated Build Script (Easiest)

**One-command deployment:**
```bash
# SSH into your Unraid server and run:
curl -sSL https://raw.githubusercontent.com/jacobe603/dst-submittals-v2/main/build-for-unraid.sh | bash
```

This script will:
- ✅ Create all necessary directories
- ✅ Clone the repository  
- ✅ Build and start both containers
- ✅ Verify services are healthy
- ✅ Show you the access URL

### Option 2: Manual Docker Compose

1. **SSH into your Unraid server**
2. **Create app directory:**
   ```bash
   mkdir -p /mnt/user/appdata/dst-submittals-v2
   cd /mnt/user/appdata/dst-submittals-v2
   ```
3. **Clone repository:**
   ```bash
   git clone https://github.com/jacobe603/dst-submittals-v2.git .
   ```
4. **Start services:**
   ```bash
   docker compose -f unraid-docker-compose.yml up -d --build
   ```
5. **Access**: `http://YOUR-UNRAID-IP:5000`

### Option 3: Using Community Applications Templates (Coming Soon)

*Note: Docker image is being built. Templates will work once GitHub Actions completes the build.*

1. **Install Community Applications** plugin if not already installed
2. **Search for "DST Submittals"** in Community Applications  
3. **Install both containers:**
   - `Gotenberg-Service` (install first)
   - `DST-Submittals-V2`
4. **Start Gotenberg** service first, then DST Submittals
5. **Access**: `http://YOUR-UNRAID-IP:5000`

### Option 2: Manual Template Installation

1. **Download templates:**
   ```bash
   cd /boot/config/plugins/dockerMan/templates-user
   wget https://raw.githubusercontent.com/jacobe603/dst-submittals-v2/main/unraid-gotenberg-template.xml
   wget https://raw.githubusercontent.com/jacobe603/dst-submittals-v2/main/unraid-template.xml
   ```

2. **Go to Docker tab** → Add Container → Select Template
3. **Install Gotenberg first**, then DST Submittals V2

## 📁 Directory Structure

The containers will create this structure on your Unraid server:

```
/mnt/user/appdata/dst-submittals-v2/     # App configuration
/mnt/user/dst-submittals/
├── outputs/                             # Generated PDFs (persistent)
├── uploads/                             # Upload staging (temporary)
└── documents/                           # Document library (optional)
```

## ⚙️ Configuration

### Essential Settings

| Setting | Default | Description |
|---------|---------|-------------|
| WebUI Port | 5000 | Web interface access port |
| Gotenberg URL | `http://gotenberg:3000` | PDF conversion service |
| PDF Quality | high | fast/balanced/high/maximum |
| Max Output Files | 50 | Cleanup: Max PDFs to keep |
| Retention Days | 30 | Cleanup: Days to keep PDFs |

### Volume Mappings

| Container Path | Host Path | Purpose |
|----------------|-----------|---------|
| `/app/config` | `/mnt/user/appdata/dst-submittals-v2` | App data & config |
| `/app/web_outputs` | `/mnt/user/dst-submittals/outputs` | Generated PDFs |
| `/app/uploads` | `/mnt/user/dst-submittals/uploads` | Upload staging |
| `/app/documents` | `/mnt/user/dst-submittals/documents` | Document library |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DST_GOTENBERG_URL` | `http://gotenberg:3000` | Gotenberg service URL |
| `DST_QUALITY_MODE` | `high` | PDF quality mode |
| `DST_MAX_OUTPUT_FILES` | `10` | Max files before cleanup |
| `DST_OUTPUT_RETENTION_DAYS` | `30` | Days to keep old files |
| `DST_CLEANUP_ON_STARTUP` | `true` | Run cleanup at startup |
| `DST_PERIODIC_CLEANUP_HOURS` | `24` | Hours between cleanups |

## 🔗 Networking

### Default Setup (Bridge Network)
- **DST Submittals**: Port 5000
- **Gotenberg**: Port 3000
- **Access**: `http://UNRAID-IP:5000`

### Custom Network (Advanced)
1. Create custom network: `dst-network`
2. Add both containers to the network
3. Use container names for internal communication

## 🌐 Reverse Proxy Setup

### Nginx Proxy Manager
```nginx
# Proxy Host Configuration
Domain Names: dst.yourdomain.com
Scheme: http
Forward Hostname/IP: UNRAID-IP
Forward Port: 5000

# SSL Certificate
Request SSL Certificate: Yes
Force SSL: Yes
```

### Swag/Letsencrypt
```nginx
# dst.subdomain.conf
server {
    listen 443 ssl;
    server_name dst.*;
    
    location / {
        proxy_pass http://UNRAID-IP:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔧 Troubleshooting

### Container Won't Start
1. **Check dependencies**: Ensure Gotenberg is running first
2. **Check ports**: Verify ports 5000 and 3000 aren't in use
3. **Check volumes**: Ensure host directories exist and have correct permissions
4. **Check logs**: Docker → DST-Submittals-V2 → Logs

### Cannot Access Web Interface
1. **Check firewall**: Ensure port 5000 is open
2. **Check container status**: Both containers should be "Started"
3. **Check network**: Verify containers can communicate
4. **Health check**: Visit `http://UNRAID-IP:5000/status-v2`

### PDF Generation Fails
1. **Gotenberg connection**: Check `DST_GOTENBERG_URL` setting
2. **File permissions**: Ensure write access to output directories
3. **Disk space**: Check available space in `/mnt/user/dst-submittals/`
4. **Service status**: Visit Gotenberg at `http://UNRAID-IP:3000/health`

### Common Error Messages

| Error | Solution |
|-------|----------|
| "Gotenberg service not available" | Start Gotenberg container first |
| "Permission denied" | Fix directory permissions: `chmod 755` |
| "No space left on device" | Free up disk space or increase retention |
| "Port already in use" | Change port or stop conflicting service |

## 📊 Monitoring & Maintenance

### Health Checks
- **DST Submittals**: `http://UNRAID-IP:5000/status-v2`
- **Gotenberg**: `http://UNRAID-IP:3000/health`

### Cleanup Management
- **Automatic**: Configured via environment variables
- **Manual**: Use web interface Cleanup Status section
- **API**: `POST http://UNRAID-IP:5000/api/cleanup/run`

### Log Files
- **Container logs**: Docker tab → Container → Logs
- **Application logs**: `/mnt/user/appdata/dst-submittals-v2/logs/`

## 🔄 Updates

### Automatic Updates (Watchtower)
Add these labels to enable Watchtower auto-updates:
```
com.centurylinklabs.watchtower.enable=true
```

### Manual Updates
1. **Stop containers**: DST Submittals → Gotenberg
2. **Update images**: Docker → Container → Force Update
3. **Start containers**: Gotenberg → DST Submittals

## 📝 Usage Examples

### Basic Workflow
1. **Access web interface**: `http://UNRAID-IP:5000`
2. **Upload documents**: Drag & drop HVAC files
3. **Preview structure**: Click "Get Tags & Preview"
4. **Generate PDF**: Click "Generate Submittal PDF"
5. **Download result**: Click download link when complete

### API Usage
```bash
# Check status
curl http://UNRAID-IP:5000/status-v2

# Trigger cleanup
curl -X POST http://UNRAID-IP:5000/api/cleanup/run

# Check cleanup status
curl http://UNRAID-IP:5000/api/cleanup/status
```

## 🛡️ Security Considerations

### Network Security
- **Internal only**: Keep containers on internal network
- **Reverse proxy**: Use SSL/TLS for external access
- **Authentication**: Consider adding auth proxy if needed

### File Security
- **Permissions**: Use appropriate file permissions
- **Cleanup**: Automatic cleanup prevents data accumulation
- **Backups**: Back up configuration and important outputs

## 💡 Tips & Best Practices

1. **Start Gotenberg first**: Always ensure dependencies are running
2. **Monitor disk usage**: Set appropriate retention policies  
3. **Use custom network**: Better container communication
4. **Regular backups**: Back up configuration and outputs
5. **Test updates**: Test in staging before production updates
6. **Monitor logs**: Regular log review for issues
7. **Resource allocation**: Ensure adequate CPU/RAM for PDF processing

## 📞 Support

- **GitHub Issues**: https://github.com/jacobe603/dst-submittals-v2/issues
- **Documentation**: https://github.com/jacobe603/dst-submittals-v2
- **Unraid Forums**: Tag @jacobe603 in relevant threads

---

**Version**: 2.0.0  
**Last Updated**: August 2024  
**Tested On**: Unraid 6.12+