# Nginx Proxy Manager Configuration for DST Submittals V2

## Quick Setup for submittals.jetools.net

### 1. Add Proxy Host in NPM

**Domain Names:**
```
submittals.jetools.net
```

**Scheme:** `http`  
**Forward Hostname/IP:** `YOUR-UNRAID-IP` (e.g., `192.168.1.100`)  
**Forward Port:** `5000` (or whatever port the script assigned)

**Block Common Exploits:** ✅ Enable  
**Websockets Support:** ✅ Enable (for real-time progress)  
**Access List:** None (or create one for security)

### 2. SSL Certificate

**SSL Certificate:** Request a new SSL Certificate  
**Domain Names:** `submittals.jetools.net`  
**Use a DNS Challenge:** ✅ Enable  
**DNS Provider:** Cloudflare  
**Credentials File Content:**
```ini
dns_cloudflare_api_token = YOUR_CLOUDFLARE_API_TOKEN
```

**Force SSL:** ✅ Enable  
**HTTP/2 Support:** ✅ Enable  
**HSTS Enabled:** ✅ Enable  

### 3. Advanced Configuration (Optional)

Add to the **Advanced** tab for better performance:

```nginx
# Increase timeouts for large file uploads
proxy_connect_timeout       300;
proxy_send_timeout          300; 
proxy_read_timeout          300;
send_timeout                300;

# Handle large file uploads (up to 500MB)
client_max_body_size        500M;
client_body_timeout         300;

# Real-time progress support (Server-Sent Events)
proxy_buffering             off;
proxy_cache                 off;

# WebSocket support for real-time updates
proxy_http_version          1.1;
proxy_set_header Upgrade    $http_upgrade;
proxy_set_header Connection "upgrade";

# Standard proxy headers
proxy_set_header Host                   $host;
proxy_set_header X-Real-IP              $remote_addr;
proxy_set_header X-Forwarded-For        $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto      $scheme;
proxy_set_header X-Forwarded-Host       $host;
proxy_set_header X-Forwarded-Server     $host;
```

### 4. Cloudflare DNS Configuration

In your Cloudflare dashboard for `jetools.net`:

**DNS Records:**
- **Type:** `A` or `CNAME`
- **Name:** `submittals`
- **Content:** Your public IP address or existing domain
- **Proxy status:** 🟠 Proxied (for CDN/security) or 🔘 DNS only

### 5. Test Configuration

After setup, test these URLs:
- `https://submittals.jetools.net` - Main interface
- `https://submittals.jetools.net/status-v2` - Service status
- Upload a small file to test the complete workflow

---

## Troubleshooting

### Common Issues:

**502 Bad Gateway:**
- Check that DST Submittals is running: `docker ps`
- Verify the internal port (usually 5000)
- Check nginx error logs

**SSL Certificate Issues:**
- Verify Cloudflare API token has DNS edit permissions
- Check DNS propagation: `nslookup submittals.jetools.net`

**File Upload Timeouts:**
- Ensure `client_max_body_size` is set to 500M
- Check proxy timeout settings

**Real-time Progress Not Working:**
- Verify WebSocket headers are configured
- Check that `proxy_buffering off` is set