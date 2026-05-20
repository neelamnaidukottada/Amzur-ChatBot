# Chatbot Application Deployment Guide

This deployment package contains everything needed to deploy the Amzur Chatbot on two separate Ubuntu servers.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   DEPLOYMENT ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  FRONTEND SERVER (Ubuntu)        BACKEND SERVER (Ubuntu)     │
│  ├─ Node.js 20                   ├─ Python 3.11              │
│  ├─ React 18                     ├─ FastAPI                  │
│  ├─ Nginx Web Server             ├─ Uvicorn ASGI Server      │
│  ├─ Port: 80/443                 ├─ Port: 8000               │
│  └─ /dist/ built files           ├─ PostgreSQL (optional)    │
│                                  └─ ChromaDB Vector Store    │
│                                                               │
│  Client Browser <──HTTP──> Nginx <──API──> FastAPI Backend   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
deployment/
├── frontend-server/          # Frontend deployment files
│   ├── app/                  # Copy your frontend source here
│   ├── build.sh              # Build script
│   ├── setup.sh              # Ubuntu setup script
│   ├── nginx.conf            # Nginx web server config
│   ├── docker-compose.yml    # Optional Docker setup
│   └── .env.example          # Environment variables template
│
├── backend-server/           # Backend deployment files
│   ├── app/                  # Copy your backend source here
│   ├── setup.sh              # Ubuntu setup script
│   ├── start.sh              # Start service script
│   ├── stop.sh               # Stop service script
│   ├── requirements.txt       # Copy from backend/requirements.txt
│   ├── Dockerfile            # For Docker deployment
│   ├── docker-compose.yml    # Complete stack with PostgreSQL
│   └── .env.example          # Environment variables template
│
└── shared-config/            # Shared configuration
    ├── DATABASE_SETUP.md     # PostgreSQL setup guide
    ├── SSL_SETUP.md          # HTTPS/SSL certificate setup
    └── TROUBLESHOOTING.md    # Common issues and solutions
```

## Prerequisites

### Frontend Server Requirements
- Ubuntu 20.04 LTS or later
- At least 1 GB RAM
- At least 10 GB disk space
- Internet connectivity

### Backend Server Requirements
- Ubuntu 20.04 LTS or later
- At least 2 GB RAM
- At least 20 GB disk space
- PostgreSQL 12+ (if not using Docker)
- Internet connectivity

## Deployment Steps

### Step 1: Prepare Deployment Files

1. Copy frontend source:
   ```bash
   cp -r frontend deployment/frontend-server/app
   ```

2. Copy backend source:
   ```bash
   cp -r backend deployment/backend-server/app
   ```

3. Copy requirements.txt to backend deployment:
   ```bash
   cp backend/requirements.txt deployment/backend-server/
   ```

### Step 2: Deploy Frontend Server

1. SSH into frontend server:
   ```bash
   ssh user@frontend-server-ip
   ```

2. Copy deployment files:
   ```bash
   scp -r deployment/frontend-server/* user@frontend-server-ip:/tmp/frontend-deploy/
   ```

3. Run setup script:
   ```bash
   cd /tmp/frontend-deploy
   chmod +x setup.sh build.sh
   sudo ./setup.sh
   ```

4. Build frontend:
   ```bash
   ./build.sh
   ```

5. Deploy built files:
   ```bash
   sudo cp -r deployment/frontend-server/app/dist/* /var/www/chatbot-frontend/dist/
   ```

6. Update nginx configuration with backend URL:
   ```bash
   sudo nano /etc/nginx/sites-available/chatbot-frontend
   # Replace 'backend-server:8000' with your backend server IP:8000
   ```

7. Restart Nginx:
   ```bash
   sudo systemctl restart nginx
   ```

### Step 3: Deploy Backend Server

1. SSH into backend server:
   ```bash
   ssh user@backend-server-ip
   ```

2. Copy deployment files:
   ```bash
   scp -r deployment/backend-server/* user@backend-server-ip:/tmp/backend-deploy/
   ```

3. Run setup script:
   ```bash
   cd /tmp/backend-deploy
   chmod +x setup.sh start.sh stop.sh
   sudo ./setup.sh
   ```

4. Configure environment:
   ```bash
   cd /var/www/chatbot-backend
   sudo cp /tmp/backend-deploy/.env.example .env
   sudo nano .env  # Edit with your API keys and database credentials
   ```

5. Copy source code:
   ```bash
   sudo cp -r deployment/backend-server/app/* /var/www/chatbot-backend/
   sudo chown -R $USER:$USER /var/www/chatbot-backend
   ```

6. Start backend service:
   ```bash
   sudo systemctl start chatbot-backend
   sudo systemctl status chatbot-backend
   ```

## Configuration

### Required Environment Variables

**Frontend (.env):**
```
VITE_API_URL=http://backend-server-ip:8000/api
VITE_APP_NAME=Amzur Simple Chatbot
```

**Backend (.env):**
```
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db
LITELLM_API_KEY=your-api-key
GOOGLE_GEMINI_API_KEY=your-gemini-key
SECRET_KEY=generate-with: openssl rand -hex 32
```

See `.env.example` files in each deployment folder for all available options.

## Docker Alternative (Recommended for Quick Deployment)

Both servers support Docker deployment. If you have Docker installed:

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

## Service Management

### Backend Service Commands

```bash
# Start service
sudo systemctl start chatbot-backend

# Stop service
sudo systemctl stop chatbot-backend

# Restart service
sudo systemctl restart chatbot-backend

# Check status
sudo systemctl status chatbot-backend

# View logs
sudo journalctl -u chatbot-backend -f

# Enable on startup
sudo systemctl enable chatbot-backend
```

### Nginx Commands

```bash
# Test configuration
sudo nginx -t

# Start Nginx
sudo systemctl start nginx

# Stop Nginx
sudo systemctl stop nginx

# Restart Nginx
sudo systemctl restart nginx

# View Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

## Monitoring and Logs

### Backend Logs
```bash
sudo journalctl -u chatbot-backend -f
```

### Nginx Logs
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Check Services
```bash
# Frontend
curl http://localhost:80

# Backend
curl http://localhost:8000/health

# Full flow
curl http://localhost:80/api/health
```

## Security Best Practices

1. **Change Default Credentials:**
   - Update `SECRET_KEY` in backend .env
   - Use strong database passwords
   - Protect API keys

2. **Enable HTTPS:**
   - See `SSL_SETUP.md` for Let's Encrypt setup
   - Update Nginx configuration
   - Redirect HTTP to HTTPS

3. **Firewall Configuration:**
   ```bash
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 80/tcp   # HTTP
   sudo ufw allow 443/tcp  # HTTPS
   sudo ufw allow 8000/tcp # Backend API (if needed for direct access)
   sudo ufw enable
   ```

4. **Database Security:**
   - Keep PostgreSQL on private network
   - Use strong passwords
   - Enable backups
   - Regular security updates

## Troubleshooting

See `TROUBLESHOOTING.md` for common issues and solutions.

## Database Setup

See `DATABASE_SETUP.md` for PostgreSQL configuration and initialization.

## Backup and Recovery

### Backend Database Backup
```bash
pg_dump -h localhost -U chatbot_user chatbot_db > backup.sql
```

### Backend Vector Database Backup
```bash
cp -r /var/www/chatbot-backend/chroma_db /backups/
```

### Restore
```bash
psql -h localhost -U chatbot_user chatbot_db < backup.sql
```

## Performance Tuning

- Uvicorn workers: 4 (adjust based on CPU cores)
- Nginx worker processes: auto
- Enable gzip compression in Nginx (enabled in config)
- Implement caching strategies
- Use CDN for static assets

## Support and Additional Resources

- FastAPI Docs: https://fastapi.tiangolo.com/
- Nginx Docs: https://nginx.org/en/docs/
- PostgreSQL Docs: https://www.postgresql.org/docs/
- React Docs: https://react.dev/

---

**Last Updated:** May 2026
**Version:** 1.0
