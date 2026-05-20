# Quick Start Deployment Guide

Deploy your chatbot in 15 minutes using Docker Compose (recommended) or manual setup.

## Prerequisites

- Two Ubuntu 20.04+ servers (or one server for both)
- Docker & Docker Compose (optional, recommended)
- SSH access to servers
- Domain name (for HTTPS)

## Option 1: Docker Compose (Fastest - 5 Minutes)

### On Backend Server:

```bash
# SSH into backend server
ssh user@backend-server-ip

# Create deployment directory
mkdir -p ~/chatbot-deployment
cd ~/chatbot-deployment

# Copy files from your local machine
scp -r backend deployment/backend-server/* user@backend-server-ip:~/chatbot-deployment/

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Create .env file
cp .env.example .env
nano .env  # Edit with your API keys

# Start services
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:8000/health
```

### On Frontend Server:

```bash
# SSH into frontend server
ssh user@frontend-server-ip

# Create deployment directory
mkdir -p ~/chatbot-deployment
cd ~/chatbot-deployment

# Copy files
scp -r frontend deployment/frontend-server/* user@frontend-server-ip:~/chatbot-deployment/

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Update docker-compose.yml with backend IP
nano docker-compose.yml
# Change "backend-server:8000" to your backend server IP

# Start
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:80
```

## Option 2: Manual Installation (10 Minutes)

### On Backend Server:

```bash
# 1. SSH in
ssh user@backend-server-ip

# 2. Copy deployment files
mkdir -p /var/www/chatbot-backend
cp -r deployment/backend-server/* /var/www/chatbot-backend/

# 3. Run setup
cd /var/www/chatbot-backend
chmod +x setup.sh start.sh
sudo ./setup.sh

# 4. Configure
sudo nano .env  # Add your API keys and database URL

# 5. Copy source code
sudo cp -r backend/app /var/www/chatbot-backend/

# 6. Initialize database (if local PostgreSQL)
sudo -u postgres psql << 'EOF'
CREATE USER chatbot_user WITH PASSWORD 'secure_password';
CREATE DATABASE chatbot_db OWNER chatbot_user;
EOF

# 7. Start service
./start.sh

# 8. Check status
sudo systemctl status chatbot-backend
sudo journalctl -u chatbot-backend -f
```

### On Frontend Server:

```bash
# 1. SSH in
ssh user@frontend-server-ip

# 2. Copy deployment files
mkdir -p /var/www/chatbot-frontend
cp -r deployment/frontend-server/* /var/www/chatbot-frontend/

# 3. Run setup
cd /var/www/chatbot-frontend
chmod +x setup.sh build.sh
sudo ./setup.sh

# 4. Build frontend
./build.sh

# 5. Copy built files
sudo cp -r app/dist/* /var/www/chatbot-frontend/dist/

# 6. Update Nginx config with backend IP
sudo nano /etc/nginx/sites-available/chatbot-frontend
# Replace "backend-server:8000" with your backend IP

# 7. Restart Nginx
sudo systemctl restart nginx

# 8. Test
curl http://localhost
```

## Verification Checklist

- [ ] Backend service running: `sudo systemctl status chatbot-backend`
- [ ] Backend health check: `curl http://backend-ip:8000/health`
- [ ] Nginx running: `sudo systemctl status nginx`
- [ ] Frontend loads: `curl http://frontend-ip`
- [ ] API accessible: `curl http://frontend-ip/api/health`
- [ ] Can login to application
- [ ] Can send messages
- [ ] Database connected

## Post-Deployment

### 1. Enable HTTPS

```bash
# Frontend server
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot certonly --nginx -d your-domain.com
# Then update nginx.conf with certificate paths
```

See [SSL_SETUP.md](shared-config/SSL_SETUP.md) for detailed instructions.

### 2. Setup Monitoring

```bash
# Check logs
sudo journalctl -u chatbot-backend -f  # Backend
sudo tail -f /var/log/nginx/error.log  # Frontend

# Monitor resources
top  # CPU/Memory
df -h  # Disk space
```

### 3. Database Backup

```bash
# Automatic daily backups
sudo crontab -e
# Add: 0 2 * * * pg_dump -U chatbot_user chatbot_db | gzip > /backups/chatbot_$(date +\%Y\%m\%d).sql.gz
```

## Environment Variables

**Critical variables to set:**

Backend (.env):
```
DATABASE_URL=postgresql://user:password@host:5432/chatbot_db
LITELLM_API_KEY=your-key
GOOGLE_GEMINI_API_KEY=your-key
SECRET_KEY=generate-with: openssl rand -hex 32
```

Frontend (.env):
```
VITE_API_URL=http://your-backend-ip:8000/api
```

## Common Commands

```bash
# Backend
sudo systemctl start chatbot-backend
sudo systemctl stop chatbot-backend
sudo systemctl restart chatbot-backend
sudo systemctl status chatbot-backend
sudo journalctl -u chatbot-backend -f

# Frontend
sudo systemctl restart nginx
sudo nginx -t
sudo tail -f /var/log/nginx/error.log

# Docker
docker-compose up -d
docker-compose down
docker-compose ps
docker-compose logs -f
```

## Troubleshooting

See [TROUBLESHOOTING.md](shared-config/TROUBLESHOOTING.md) for detailed solutions.

**Quick checks:**
```bash
# Backend responding?
curl http://backend-ip:8000/health

# Nginx responding?
curl http://frontend-ip

# Database connected?
psql -h db-host -U chatbot_user -d chatbot_db -c "SELECT 1"

# Check logs
sudo journalctl -u chatbot-backend -n 50
sudo tail -f /var/log/nginx/error.log
```

## Performance Tuning

After deployment, optimize for production:

1. **Backend:** Increase uvicorn workers to match CPU cores
2. **Nginx:** Enable gzip compression (already enabled)
3. **Database:** Add indexes on frequently queried columns
4. **Caching:** Implement response caching for common queries

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for details.

## Next Steps

1. Configure monitoring and alerting
2. Setup automated backups
3. Configure log aggregation
4. Setup CDN for static assets
5. Implement rate limiting
6. Configure auto-scaling if needed

## Support Resources

- FastAPI: https://fastapi.tiangolo.com/
- Nginx: https://nginx.org/en/docs/
- PostgreSQL: https://www.postgresql.org/docs/
- Docker: https://docs.docker.com/

---

**Need Help?** Check TROUBLESHOOTING.md or DEPLOYMENT_GUIDE.md for comprehensive guides.

**Last Updated:** May 2026
