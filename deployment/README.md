# Deployment Directory Structure Guide

## Overview

This deployment package is organized for two-server deployment:
- **Frontend Server**: Ubuntu with Nginx + React built files
- **Backend Server**: Ubuntu with Python + FastAPI + PostgreSQL

## Folder Structure

```
deployment/
├── DEPLOYMENT_GUIDE.md           # Complete deployment guide
├── QUICK_START.md                # Fast 5-minute setup
│
├── frontend-server/              # ⬅️ Deploy to Frontend Server
│   ├── setup.sh                  # Run this first: sudo ./setup.sh
│   ├── build.sh                  # Build React: ./build.sh
│   ├── nginx.conf                # Nginx web server config
│   ├── docker-compose.yml        # Optional: Docker setup
│   ├── .env.example              # Frontend environment variables
│   └── app/                      # Copy your frontend here
│       ├── src/
│       ├── public/
│       ├── package.json
│       └── vite.config.ts
│
├── backend-server/               # ⬅️ Deploy to Backend Server
│   ├── setup.sh                  # Run this first: sudo ./setup.sh
│   ├── start.sh                  # Start service: ./start.sh
│   ├── stop.sh                   # Stop service: ./stop.sh
│   ├── requirements.txt           # Python dependencies
│   ├── Dockerfile                # Optional: Docker image
│   ├── docker-compose.yml        # Optional: Docker with PostgreSQL
│   ├── .env.example              # Backend environment variables
│   └── app/                      # Copy your backend here
│       ├── main.py
│       ├── api/
│       ├── core/
│       ├── services/
│       └── schemas/
│
└── shared-config/                # Shared guides and tools
    ├── DATABASE_SETUP.md         # PostgreSQL setup
    ├── SSL_SETUP.md              # HTTPS/Let's Encrypt setup
    └── TROUBLESHOOTING.md        # Common issues & solutions
```

## Step-by-Step Deployment

### Step 1: Prepare Files

```bash
# On your development machine
# Copy project files to deployment folders

cd deployment/

# Frontend
cp -r ../frontend frontend-server/app

# Backend
cp -r ../backend backend-server/app
cp ../backend/requirements.txt backend-server/

# Verify
ls frontend-server/app/src/
ls backend-server/app/main.py
```

### Step 2: Deploy Frontend

```bash
# Transfer to frontend server
scp -r frontend-server/* user@frontend-server-ip:~/deploy/

# SSH into frontend server
ssh user@frontend-server-ip

# Run setup
cd ~/deploy
chmod +x setup.sh build.sh
sudo ./setup.sh

# Build
./build.sh

# Deploy
sudo cp -r app/dist/* /var/www/chatbot-frontend/dist/

# Configure
sudo nano /etc/nginx/sites-available/chatbot-frontend
# Update backend-server IP

# Restart
sudo systemctl restart nginx
```

### Step 3: Deploy Backend

```bash
# Transfer to backend server
scp -r backend-server/* user@backend-server-ip:~/deploy/

# SSH into backend server
ssh user@backend-server-ip

# Run setup
cd ~/deploy
chmod +x setup.sh start.sh
sudo ./setup.sh

# Configure
cd /var/www/chatbot-backend
sudo cp ~/deploy/.env.example .env
sudo nano .env  # Add API keys, database credentials, etc.

# Copy code
sudo cp -r ~/deploy/app/* /var/www/chatbot-backend/app/
sudo chown -R $USER:$USER /var/www/chatbot-backend

# Start
sudo systemctl start chatbot-backend
sudo systemctl status chatbot-backend
```

### Step 4: Configure Connectivity

Update backend IP in Nginx:
```bash
# On frontend server
sudo nano /etc/nginx/sites-available/chatbot-frontend

# Find:
# proxy_pass http://backend-server:8000;
# Replace with your backend server IP:
# proxy_pass http://192.168.1.100:8000;

sudo systemctl restart nginx
```

### Step 5: Verify Everything

```bash
# From frontend server
curl http://localhost:80/
curl http://backend-server-ip:8000/health

# From backend server
sudo systemctl status chatbot-backend
sudo journalctl -u chatbot-backend -n 20
```

## Using Docker (Recommended for Simple Setup)

### Backend with Docker:
```bash
cd deployment/backend-server
docker-compose up -d
```

### Frontend with Docker:
```bash
cd deployment/frontend-server
docker-compose up -d
```

## Configuration Files Explained

### Frontend (.env.example)
```
VITE_API_URL=http://your-backend-server-ip:8000/api
VITE_APP_NAME=Amzur Simple Chatbot
```

### Backend (.env.example)
- `DATABASE_URL`: PostgreSQL connection
- `LITELLM_API_KEY`: LLM proxy key
- `GOOGLE_GEMINI_API_KEY`: Google API key
- `SECRET_KEY`: JWT secret (generate fresh)

## Starting Services After Reboot

The systemd services are configured to auto-start:

```bash
# Backend auto-starts after reboot
sudo systemctl enable chatbot-backend

# Frontend (Nginx) auto-starts after reboot
sudo systemctl enable nginx

# Verify on reboot
sudo systemctl status chatbot-backend
sudo systemctl status nginx
```

## Monitoring & Logs

```bash
# Backend logs
sudo journalctl -u chatbot-backend -f

# Frontend logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Combined view
watch -n 1 "echo '=== BACKEND ===' && systemctl status chatbot-backend --no-pager && echo '' && echo '=== FRONTEND ===' && systemctl status nginx --no-pager"
```

## Backup & Recovery

### Backend Database Backup
```bash
pg_dump -h localhost -U chatbot_user chatbot_db | gzip > backup.sql.gz
```

### Restore
```bash
gunzip -c backup.sql.gz | psql -h localhost -U chatbot_user chatbot_db
```

## Production Checklist

- [ ] Updated all .env files with real credentials
- [ ] Generated new SECRET_KEY for JWT
- [ ] Configured PostgreSQL with strong password
- [ ] Set up database backups
- [ ] Enabled HTTPS (see SSL_SETUP.md)
- [ ] Configured firewall (see TROUBLESHOOTING.md)
- [ ] Set up monitoring and alerts
- [ ] Verified service auto-start on reboot
- [ ] Tested database failover
- [ ] Documented custom configurations

## Scaling (Multi-Server)

For large deployments:

1. **Load Balancing**: Put Nginx in front of multiple backend instances
2. **Database Clustering**: Use PostgreSQL replication
3. **Caching**: Add Redis for session/data caching
4. **CDN**: Distribute frontend assets globally
5. **Monitoring**: Add Prometheus/Grafana for metrics

See DEPLOYMENT_GUIDE.md for advanced configurations.

## Support & Documentation

- **Quick Deployment**: QUICK_START.md
- **Full Guide**: DEPLOYMENT_GUIDE.md
- **Database Setup**: shared-config/DATABASE_SETUP.md
- **SSL/HTTPS**: shared-config/SSL_SETUP.md
- **Troubleshooting**: shared-config/TROUBLESHOOTING.md

---

**Last Updated:** May 2026
**Version:** 1.0
