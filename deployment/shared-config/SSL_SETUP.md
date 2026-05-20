# SSL/HTTPS Setup with Let's Encrypt

## Prerequisites

- Domain name pointing to your server
- Ubuntu with Nginx installed
- Open ports 80 and 443

## Step 1: Install Certbot

```bash
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx
```

## Step 2: Obtain SSL Certificate

### Option A: Using Certbot with Nginx Plugin (Recommended)

```bash
sudo certbot certonly --nginx -d your-domain.com -d www.your-domain.com
```

### Option B: Using Standalone (if Nginx not available yet)

```bash
# Stop Nginx
sudo systemctl stop nginx

# Get certificate
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Start Nginx
sudo systemctl start nginx
```

## Step 3: Update Nginx Configuration

Edit `/etc/nginx/sites-available/chatbot-frontend`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Root directory
    root /var/www/chatbot-frontend/dist;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_min_length 1000;

    # Browser caching for static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API proxy
    location /api {
        proxy_pass http://backend-server-ip:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # React Router handling
    location / {
        try_files $uri $uri/ /index.html;
        expires -1;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # Deny hidden files
    location ~ /\. {
        deny all;
    }
}
```

## Step 4: Verify and Enable

```bash
# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Test HTTPS
curl -I https://your-domain.com
```

## Step 5: Auto-Renewal

Let's Encrypt certificates expire after 90 days. Certbot automatically sets up renewal:

```bash
# Check renewal schedule
sudo systemctl status certbot.timer

# Enable auto-renewal
sudo systemctl enable certbot.timer

# Test renewal (dry run)
sudo certbot renew --dry-run

# Manual renewal
sudo certbot renew
```

## Troubleshooting

### Certificate Not Renewing

```bash
# Check renewal logs
sudo journalctl -u certbot.service -f

# Force renewal
sudo certbot renew --force-renewal

# Increase log verbosity
sudo certbot renew -v
```

### DNS/Domain Issues

```bash
# Check DNS resolution
nslookup your-domain.com

# Check certificate details
openssl s_client -connect your-domain.com:443
```

### Renewal Failures

```bash
# Common issue: port 80 blocked
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Restart Nginx
sudo systemctl restart nginx

# Try renewal again
sudo certbot renew
```

## Advanced: Certificate Monitoring

Monitor certificate expiration:

```bash
# Create script: /usr/local/bin/check_ssl_cert.sh
#!/bin/bash
DOMAIN="your-domain.com"
CERT_FILE="/etc/letsencrypt/live/$DOMAIN/cert.pem"
EXPIRY_DATE=$(openssl x509 -enddate -noout -in $CERT_FILE | cut -d= -f2)
echo "Certificate for $DOMAIN expires: $EXPIRY_DATE"

# Add to crontab for weekly check
0 0 * * 0 /usr/local/bin/check_ssl_cert.sh | mail -s "SSL Certificate Status" admin@example.com
```

## Security Best Practices

1. **Always use HTTPS in production**
   - Redirect all HTTP to HTTPS
   - Use HSTS header (already in config above)

2. **Keep certificates updated**
   - Certbot auto-renewal handles this
   - Monitor renewal status

3. **Use strong cipher suites**
   - Config above uses TLSv1.2+ only
   - Disables weak ciphers

4. **Implement security headers**
   - HSTS, X-Frame-Options, CSP
   - Already included in config

## Mixed Content Issues

If HTTPS is enabled but resources fail to load:

```bash
# Check browser console for mixed content warnings
# Update nginx.conf to ensure all internal links use https

# For proxied backend:
location /api {
    proxy_set_header X-Forwarded-Proto $scheme;
    # This tells backend the real protocol
}
```

---

**Last Updated:** May 2026
