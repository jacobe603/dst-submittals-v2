# DST Submittals V2 - Cloudflare + Nginx Setup Guide

Complete guide for exposing DST Submittals V2 via `submittals.jetools.net` using Cloudflare DNS and Nginx reverse proxy.

## 🌐 Cloudflare DNS Setup

### 1. Add DNS Record

In your Cloudflare dashboard for `jetools.net`:

**Create A Record:**
- **Type:** `A`
- **Name:** `submittals`
- **IPv4 address:** Your public IP address
- **Proxy status:** 🟠 **Proxied** (recommended for security)
- **TTL:** Auto

**Or Create CNAME Record** (if using existing subdomain):
- **Type:** `CNAME`
- **Name:** `submittals`
- **Target:** `yourdomain.com` (your existing domain)
- **Proxy status:** 🟠 **Proxied**

### 2. Cloudflare SSL/TLS Settings

**SSL/TLS Overview:**
- **SSL/TLS encryption mode:** Full (strict) ✅

**Edge Certificates:**
- **Always Use HTTPS:** On ✅
- **HTTP Strict Transport Security (HSTS):** Enable ✅
- **Minimum TLS Version:** 1.2 ✅
- **Opportunistic Encryption:** On ✅
- **TLS 1.3:** On ✅

### 3. Cloudflare Security Settings (Optional)

**Security → WAF:**
- **Web Application Firewall:** On ✅
- **Rate Limiting:** Configure for `/upload` endpoint

**Security → DDoS:**
- **DDoS Protection:** Automatic ✅

## 🔧 Nginx Configuration Options

Choose the configuration that matches your setup:

### Option 1: Nginx Proxy Manager (Easiest)

**Perfect for:** Unraid users, Docker-based setups

1. **Open Nginx Proxy Manager** web interface
2. **Add Proxy Host:**
   - **Domain Names:** `submittals.jetools.net`
   - **Scheme:** `http`
   - **Forward Hostname/IP:** `192.168.1.XXX` (your Unraid IP)
   - **Forward Port:** `5000` (your DST Submittals port)
   - **Websockets Support:** ✅ Enable
   - **Block Common Exploits:** ✅ Enable

3. **SSL Certificate:**
   - **Request a new SSL Certificate**
   - **Use DNS Challenge:** ✅ Enable
   - **DNS Provider:** Cloudflare
   - **Credentials:** Your Cloudflare API token
   - **Force SSL:** ✅ Enable

4. **Advanced Tab** (copy from `nginx-configs/nginx-proxy-manager.md`)

### Option 2: SWAG/LinuxServer Container

**Perfect for:** SWAG users, automated SSL

1. **Copy configuration:**
   ```bash
   cp nginx-configs/swag-nginx.conf /config/nginx/proxy-confs/submittals.subdomain.conf
   ```

2. **Edit the file:**
   - Replace `YOUR-UNRAID-IP` with your actual IP
   - Adjust port if needed (default 5000)

3. **Restart SWAG container**

### Option 3: Standalone Nginx

**Perfect for:** VPS, dedicated server setups

1. **Install certbot for SSL:**
   ```bash
   apt install certbot python3-certbot-nginx
   certbot --nginx -d submittals.jetools.net
   ```

2. **Copy configuration:**
   ```bash
   cp nginx-configs/standalone-nginx.conf /etc/nginx/sites-available/submittals.jetools.net
   ln -s /etc/nginx/sites-available/submittals.jetools.net /etc/nginx/sites-enabled/
   ```

3. **Edit configuration:**
   - Replace `YOUR-UNRAID-IP:5000` with your actual address
   - Adjust SSL certificate paths if needed

4. **Test and reload:**
   ```bash
   nginx -t
   systemctl reload nginx
   ```

## 🔍 Configuration Details

### Required Nginx Settings for DST Submittals V2:

```nginx
# Large file upload support (up to 500MB)
client_max_body_size 500M;
client_body_timeout 300s;

# Real-time progress support (Server-Sent Events)
proxy_buffering off;
proxy_cache off;

# WebSocket support for real-time updates  
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";

# Extended timeouts for document processing
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
proxy_read_timeout 300s;
```

### Security Headers:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options nosniff;
add_header X-Frame-Options DENY;
add_header X-XSS-Protection "1; mode=block";
```

## ✅ Testing Your Setup

### 1. DNS Propagation
```bash
# Check DNS resolution
nslookup submittals.jetools.net
dig submittals.jetools.net

# Should return your public IP or Cloudflare proxy IP
```

### 2. SSL Certificate
```bash
# Check SSL certificate
openssl s_client -connect submittals.jetools.net:443 -servername submittals.jetools.net
```

### 3. Service Accessibility
- **Main interface:** https://submittals.jetools.net
- **Health check:** https://submittals.jetools.net/status-v2
- **Upload test:** Try uploading a small HVAC document

### 4. Real-time Features
- Upload a document and verify progress updates work
- Check browser developer tools for WebSocket connections

## 🛠️ Troubleshooting

### Common Issues:

**502 Bad Gateway:**
```bash
# Check DST Submittals is running
docker ps | grep dst

# Check nginx can reach the service
curl http://192.168.1.XXX:5000/status-v2
```

**SSL Issues:**
- Verify Cloudflare SSL mode is "Full (strict)"
- Check certificate auto-renewal setup
- Ensure nginx SSL configuration is correct

**File Upload Failures:**
- Check `client_max_body_size` is set to 500M
- Verify proxy timeout settings
- Check available disk space

**Real-time Progress Not Working:**
- Ensure WebSocket headers are configured
- Check that proxy buffering is disabled
- Verify Server-Sent Events aren't blocked

**Cloudflare Issues:**
- Try setting DNS record to "DNS only" (🔘) temporarily
- Check Cloudflare security settings aren't blocking requests
- Verify API token has correct permissions

### Log Locations:

**Nginx Proxy Manager:** Docker logs  
**SWAG:** `/config/log/nginx/`  
**Standalone Nginx:** `/var/log/nginx/`  
**DST Submittals:** `docker logs dst-submittals-app`

## 🔒 Security Recommendations

1. **Use Cloudflare proxy** (🟠) for DDoS protection
2. **Enable rate limiting** for upload endpoints
3. **Set up access restrictions** if needed (IP whitelist, HTTP auth)
4. **Monitor logs** for suspicious activity
5. **Keep certificates auto-renewed**
6. **Regular security updates** for nginx and containers

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all configuration files have correct IP addresses
3. Test each component individually (DNS → SSL → Proxy → App)
4. Check logs for specific error messages

---

**Expected Result:** Fully functional DST Submittals V2 accessible at `https://submittals.jetools.net` with SSL, real-time progress, and file upload support up to 500MB.