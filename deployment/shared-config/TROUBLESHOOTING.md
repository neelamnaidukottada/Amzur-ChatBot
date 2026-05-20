# Troubleshooting Guide

## Common Issues and Solutions

---

## Frontend Issues

### 1. Nginx Not Starting

**Error:** `systemctl status nginx` shows failed

**Solutions:**
```bash
# Check syntax
sudo nginx -t

# View detailed errors
sudo systemctl status nginx -l

# Check logs
sudo tail -f /var/log/nginx/error.log

# Common fixes:
# - Port 80 already in use: sudo lsof -i :80
# - Fix permissions: sudo chown -R www-data:www-data /var/www/chatbot-frontend
```

### 2. CORS Errors in Browser Console

**Error:** `Access to XMLHttpRequest blocked by CORS policy`

**Solutions:**
```bash
# Verify backend URL in nginx.conf
# Location section should have:
location /api {
    proxy_pass http://backend-server-ip:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Restart nginx
sudo systemctl restart nginx
```

### 3. 404 Not Found on Refresh

**Error:** Page works on initial load but 404 on refresh of nested routes

**Solutions:**
```bash
# In nginx.conf, ensure React Router handling:
location / {
    try_files $uri $uri/ /index.html;
}

# The 'try_files' directive is critical for SPA routing
```

### 4. CSS/JS Files Returning 404

**Error:** Styles not applied, console shows 404 for /dist/assets/...

**Solutions:**
```bash
# Verify files exist
sudo ls -la /var/www/chatbot-frontend/dist/

# Check file permissions
sudo chmod -R 644 /var/www/chatbot-frontend/dist/

# Check root directory in nginx.conf
root /var/www/chatbot-frontend/dist;

# Test direct access
curl -I http://localhost/assets/main.xxx.js
```

### 5. Build Process Fails

**Error:** `npm run build` fails

**Solutions:**
```bash
# Clear node_modules and cache
rm -rf node_modules package-lock.json
npm cache clean --force

# Reinstall
npm install

# Try build again
npm run build

# If TypeScript errors occur:
npm run build -- --verbose
```

### 6. High Memory Usage

**Error:** Nginx consuming excessive memory

**Solutions:**
```bash
# Check worker processes
ps aux | grep nginx

# Optimize nginx.conf:
worker_processes auto;  # Set to number of CPU cores
worker_connections 1024;  # Adjust based on traffic

# Monitor
top -p $(pgrep -d',' nginx)
```

---

## Backend Issues

### 1. Backend Service Won't Start

**Error:** `systemctl status chatbot-backend` shows failed

**Solutions:**
```bash
# Check service logs
sudo journalctl -u chatbot-backend -n 50

# Verify .env file exists and is readable
ls -la /var/www/chatbot-backend/.env

# Check Python version
python3 --version  # Should be 3.8+

# Verify virtual environment
source /var/www/chatbot-backend/venv/bin/activate
python -c "import fastapi; print(fastapi.__version__)"

# Try starting manually for detailed errors
cd /var/www/chatbot-backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Database Connection Error

**Error:** `psycopg2.OperationalError: could not connect to server`

**Solutions:**
```bash
# Verify DATABASE_URL in .env
# Format: postgresql://user:password@host:port/database

# Test connection manually
psql -h localhost -U chatbot_user -d chatbot_db -c "SELECT 1"

# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify credentials
# List users: sudo -u postgres psql -c "\du"
# List databases: sudo -u postgres psql -c "\l"

# If remote database:
# - Check firewall allows port 5432 from backend server
# - Verify pg_hba.conf allows connection
# - Test connectivity: nc -zv db-host 5432
```

### 3. LLM API Key Invalid

**Error:** `401 Unauthorized` or `Invalid API key`

**Solutions:**
```bash
# Verify keys in .env
grep -E "LITELLM_API_KEY|GOOGLE_GEMINI_API_KEY" /var/www/chatbot-backend/.env

# Check .env is readable by the service user
sudo -u <service-user> cat /var/www/chatbot-backend/.env

# Restart service after updating .env
sudo systemctl restart chatbot-backend

# Test manually
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### 4. Out of Memory

**Error:** Backend crashes with `MemoryError` or kernel kills process

**Solutions:**
```bash
# Check memory usage
free -h
ps aux | grep uvicorn

# Reduce uvicorn workers
# Edit /etc/systemd/system/chatbot-backend.service
# ExecStart=/path/venv/bin/uvicorn app.main:app --workers 2

# Implement request timeouts
# Update nginx.conf:
proxy_read_timeout 30s;
proxy_connect_timeout 30s;

# Monitor over time
watch -n 1 'ps aux | grep uvicorn | grep -v grep'
```

### 5. Slow Response Times

**Error:** API responses take 10+ seconds

**Solutions:**
```bash
# Check backend logs for bottlenecks
sudo journalctl -u chatbot-backend -f

# Profile database queries
# Add to .env:
SQLALCHEMY_ECHO=true

# Check database performance
sudo -u postgres psql -d chatbot_db << 'EOF'
SELECT * FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
EOF

# Increase workers if CPU available
ExecStart=/path/venv/bin/uvicorn app.main:app --workers 8 --worker-class uvicorn.workers.UvicornWorker

# Enable caching
# Update chat service to cache common responses
```

### 6. Import Errors or Missing Dependencies

**Error:** `ModuleNotFoundError: No module named 'X'`

**Solutions:**
```bash
# Verify virtual environment is activated
source /var/www/chatbot-backend/venv/bin/activate

# Reinstall requirements
pip install --upgrade pip
pip install -r requirements.txt

# Check if new requirements not in old requirements.txt
pip freeze > current_requirements.txt
diff current_requirements.txt requirements.txt

# Try manual import
python -c "import langchain; print(langchain.__version__)"
```

### 7. Timeout Errors

**Error:** `requests.exceptions.Timeout` or similar

**Solutions:**
```bash
# Increase timeouts in .env (if application supports)
# Or in request code

# Check upstream services are responding
timeout 10 curl -v http://litellm.amzur.com/health

# Increase OS timeouts
# Edit /etc/sysctl.conf:
net.ipv4.tcp_fin_timeout = 60
sudo sysctl -p

# Review service dependencies:
# - LiteLLM proxy availability
# - Database connectivity
# - External API availability
```

---

## Deployment Issues

### 1. Files Not in Correct Location

**Error:** 404 errors after deployment

**Solutions:**
```bash
# Verify frontend dist location
ls -la /var/www/chatbot-frontend/dist/

# Verify backend location
ls -la /var/www/chatbot-backend/app/

# Check symlinks
ls -la /var/www/

# Verify ownership
ls -la /var/www/ | grep chatbot
```

### 2. Permission Denied Errors

**Error:** `Permission denied` when accessing files

**Solutions:**
```bash
# Fix frontend permissions
sudo chown -R $USER:$USER /var/www/chatbot-frontend
sudo chmod -R 755 /var/www/chatbot-frontend

# Fix backend permissions
sudo chown -R $USER:$USER /var/www/chatbot-backend
sudo chmod -R 755 /var/www/chatbot-backend

# Fix service user permissions
sudo chown -R www-data:www-data /var/www/chatbot-frontend
sudo chown -R chatbot-user:chatbot-user /var/www/chatbot-backend
```

### 3. Port Already in Use

**Error:** `Address already in use` when starting services

**Solutions:**
```bash
# Find what's using port
sudo lsof -i :80      # Frontend
sudo lsof -i :8000    # Backend
sudo lsof -i :5432    # Database

# Kill process
sudo kill -9 <PID>

# Or use different port (update configuration)
```

### 4. DNS/Hostname Resolution

**Error:** `Cannot resolve backend-server` or similar

**Solutions:**
```bash
# Test DNS
nslookup backend-server-ip
ping backend-server-ip
curl http://backend-server-ip:8000/health

# Update hosts file if needed (temporary)
echo "backend-server-ip backend-server" | sudo tee -a /etc/hosts

# Or use IP addresses directly in configuration
```

---

## Network Issues

### 1. Can't Connect from Frontend to Backend

**Error:** Frontend gets connection refused

**Solutions:**
```bash
# Verify backend is running
sudo systemctl status chatbot-backend

# Test locally on backend server
curl http://localhost:8000/health

# Test from frontend server
curl http://backend-server-ip:8000/health

# Check firewall
sudo ufw status
sudo ufw allow 8000/tcp

# Check nginx routing
sudo nginx -t
# Check proxy_pass in /etc/nginx/sites-available/chatbot-frontend
```

### 2. Firewall Blocking Connections

**Error:** Connection times out or refused

**Solutions:**
```bash
# Check firewall status
sudo ufw status

# Allow necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # Backend (optional if internal)
sudo ufw allow 5432/tcp  # Database (optional if internal)

# Reload firewall
sudo ufw reload

# Test with telnet/nc
nc -zv backend-server-ip 8000
```

---

## General Debugging

### Enable Debug Logging

**Backend:**
```bash
# Update .env
LOG_LEVEL=DEBUG

# Restart service
sudo systemctl restart chatbot-backend

# View logs
sudo journalctl -u chatbot-backend -f --priority=debug
```

**Nginx:**
```bash
# Update error_log level in nginx.conf
error_log /var/log/nginx/error.log debug;

# Test and reload
sudo nginx -t
sudo systemctl reload nginx

# View logs
sudo tail -f /var/log/nginx/error.log
```

### Useful Diagnostic Commands

```bash
# System info
uname -a
lsb_release -a

# Resource usage
top -b -n 1 | head -20
free -h
df -h

# Service status
systemctl list-units --type=service --all

# Network
ss -tlnp
netstat -an | grep LISTEN

# Logs
sudo journalctl -n 100 -f
dmesg | tail -20
```

---

## Getting Help

1. Check this guide first
2. Review service logs
3. Check system resources
4. Verify network connectivity
5. Test each component independently
6. Create minimal reproducible example

**Useful log locations:**
- Backend: `sudo journalctl -u chatbot-backend -f`
- Nginx: `/var/log/nginx/error.log` and `/var/log/nginx/access.log`
- PostgreSQL: `/var/log/postgresql/postgresql-*.log`
- System: `/var/log/syslog`

---

**Last Updated:** May 2026
