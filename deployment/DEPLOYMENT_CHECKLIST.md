# Deployment Checklist

Use this checklist to ensure your deployment is complete and correct.

## Pre-Deployment

### Repository Preparation
- [ ] Cloned/copied latest code
- [ ] All source files present
- [ ] No sensitive data in code (API keys, passwords)
- [ ] `.env.example` files created with defaults
- [ ] `requirements.txt` up to date
- [ ] `package.json` present and correct
- [ ] README files with setup instructions

### Server Preparation
- [ ] Two Ubuntu 20.04+ servers provisioned
- [ ] SSH access verified
- [ ] Public IPs assigned or DNS configured
- [ ] Sufficient disk space (10GB frontend, 20GB backend)
- [ ] Sufficient RAM (1GB frontend, 2GB backend minimum)
- [ ] Internet connectivity tested
- [ ] Firewall rules planned

## Frontend Deployment

### Setup Phase
- [ ] Copied deployment files to frontend server
- [ ] Ran `sudo ./setup.sh` successfully
- [ ] Node.js installed: `node --version`
- [ ] npm installed: `npm --version`
- [ ] Nginx installed: `nginx -v`
- [ ] Nginx is running: `sudo systemctl status nginx`

### Build Phase
- [ ] Copied frontend source to `frontend-server/app/`
- [ ] Ran `./build.sh` successfully
- [ ] No build errors
- [ ] `dist/` folder created
- [ ] Built files copied to `/var/www/chatbot-frontend/dist/`

### Configuration Phase
- [ ] `.env` file created from `.env.example`
- [ ] `VITE_API_URL` points to backend server IP
- [ ] `nginx.conf` updated with backend IP
- [ ] Backend IP replaced in `proxy_pass` directive
- [ ] Nginx config tested: `sudo nginx -t` (should pass)
- [ ] Nginx restarted: `sudo systemctl restart nginx`

### Verification Phase
- [ ] Frontend loads: `curl http://localhost/`
- [ ] Static files accessible: `curl http://localhost/assets/main.js`
- [ ] API routing works: `curl http://localhost/api/health`
- [ ] React routes work (test in browser)
- [ ] Console has no CORS errors
- [ ] Console has no 404 errors

## Backend Deployment

### Setup Phase
- [ ] Copied deployment files to backend server
- [ ] Ran `sudo ./setup.sh` successfully
- [ ] Python 3.11+ installed: `python3 --version`
- [ ] Virtual environment created: `ls -la venv/bin/python`
- [ ] Dependencies installed: `pip list | grep fastapi`
- [ ] PostgreSQL client installed: `psql --version`
- [ ] Systemd service created: `ls -la /etc/systemd/system/chatbot-backend.service`

### Database Phase
- [ ] PostgreSQL installed and running
- [ ] Database created: `chatbot_db`
- [ ] Database user created: `chatbot_user`
- [ ] User has correct permissions
- [ ] Connection test successful: `psql -h localhost -U chatbot_user -d chatbot_db -c "SELECT 1"`
- [ ] Connection string correct in `.env`

### Configuration Phase
- [ ] `.env` file created from `.env.example`
- [ ] `DATABASE_URL` set correctly
- [ ] `LITELLM_API_KEY` set and valid
- [ ] `GOOGLE_GEMINI_API_KEY` set and valid
- [ ] `SECRET_KEY` generated fresh: `openssl rand -hex 32`
- [ ] File permissions correct: `ls -la /var/www/chatbot-backend/`
- [ ] `.env` readable by service user

### Deployment Phase
- [ ] Backend source copied to `/var/www/chatbot-backend/app/`
- [ ] File ownership correct: `sudo chown -R $USER:$USER /var/www/chatbot-backend`
- [ ] File permissions correct: `sudo chmod -R 755 /var/www/chatbot-backend`

### Service Phase
- [ ] Service started: `sudo systemctl start chatbot-backend`
- [ ] Service running: `sudo systemctl status chatbot-backend` (should show active)
- [ ] Service enabled: `sudo systemctl enable chatbot-backend`
- [ ] No startup errors: `sudo journalctl -u chatbot-backend -n 20`

### Verification Phase
- [ ] Health endpoint works: `curl http://localhost:8000/health`
- [ ] Can connect from frontend server: `curl http://backend-ip:8000/health`
- [ ] Database connected (check logs)
- [ ] API endpoints accessible
- [ ] No errors in logs: `sudo journalctl -u chatbot-backend -f`

## Integration Testing

### Frontend-Backend Communication
- [ ] Frontend loads: http://frontend-ip
- [ ] Can access API: http://frontend-ip/api/health
- [ ] No CORS errors
- [ ] API response time < 5 seconds
- [ ] Can successfully complete login flow (if applicable)
- [ ] Can send test message and get response

### Full Application Flow
- [ ] User registration works
- [ ] User login works
- [ ] Chat message sending works
- [ ] Chat message storage works
- [ ] Chat history loading works
- [ ] Logout works
- [ ] Database persistence verified

## Security Configuration

### Credentials & Keys
- [ ] No API keys in git repository
- [ ] `.env` files excluded from version control
- [ ] All `.env` files have strong random values
- [ ] API keys rotate on schedule plan
- [ ] Database password is strong (12+ chars, mixed case, numbers, symbols)
- [ ] JWT SECRET_KEY is cryptographically random

### Network Security
- [ ] Firewall rules configured
  - [ ] Port 22 (SSH) restricted to known IPs
  - [ ] Port 80 (HTTP) open to public
  - [ ] Port 443 (HTTPS) open to public if enabled
  - [ ] Port 8000 restricted (backend only internal or specific IPs)
  - [ ] Port 5432 restricted (database only internal)
- [ ] Fail2ban or similar configured (optional)

### HTTPS/SSL (if applicable)
- [ ] SSL certificate obtained from Let's Encrypt
- [ ] Certificate paths correct in nginx.conf
- [ ] HTTP redirects to HTTPS
- [ ] HSTS header enabled
- [ ] SSL test passes: https://www.ssllabs.com/

## Monitoring & Logging

### Service Monitoring
- [ ] Backend service auto-restarts on failure
- [ ] Frontend (Nginx) auto-restarts on failure
- [ ] Services start on server reboot
- [ ] Logs are readable: `sudo journalctl -u chatbot-backend`
- [ ] Log rotation configured (if needed)

### Performance Baseline
- [ ] Response time baseline recorded
- [ ] CPU usage baseline recorded
- [ ] Memory usage baseline recorded
- [ ] Disk usage baseline recorded
- [ ] Database query performance checked

## Backup & Recovery

### Backup Configuration
- [ ] Database backup script created
- [ ] Backup automation scheduled (cron)
- [ ] First backup completed successfully
- [ ] Backups stored securely
- [ ] Backup retention policy defined
- [ ] Backup restoration tested (at least once)

### Disaster Recovery Plan
- [ ] Data loss recovery procedure documented
- [ ] Service failure recovery procedure documented
- [ ] Contact escalation path defined
- [ ] RTO/RPO targets documented

## Documentation

### Deployment Documentation
- [ ] Deployment guide read and verified
- [ ] Configuration documented
- [ ] Custom changes documented
- [ ] Server access information documented
- [ ] Backup procedures documented
- [ ] Troubleshooting guide reviewed

### Knowledge Transfer
- [ ] Operations team trained
- [ ] Runbooks created/updated
- [ ] Known issues documented
- [ ] Contact info for support documented

## Post-Deployment

### Day 1
- [ ] Services running without errors for 24 hours
- [ ] No log warnings or errors
- [ ] Basic functionality tested
- [ ] Users can access application

### Week 1
- [ ] Monitor for edge cases
- [ ] Check backup integrity
- [ ] Verify auto-scaling (if applicable)
- [ ] Monitor resource usage trends
- [ ] Collect performance metrics

### Month 1
- [ ] Security audit completed
- [ ] Performance optimization completed
- [ ] Documentation updated
- [ ] Lessons learned documented
- [ ] Incident response testing completed

## Sign-off

- [ ] Deployment Lead: _________________ Date: _______
- [ ] DevOps/Infrastructure: __________ Date: _______
- [ ] QA/Testing: __________________ Date: _______
- [ ] Product Owner: ________________ Date: _______

---

## Quick Command Reference

```bash
# Verify services
sudo systemctl status chatbot-backend
sudo systemctl status nginx

# View logs
sudo journalctl -u chatbot-backend -f
sudo tail -f /var/log/nginx/error.log

# Test connectivity
curl http://localhost:80              # Frontend
curl http://localhost:8000/health   # Backend

# Check resources
top -n 1 | head -10
free -h
df -h

# Restart services
sudo systemctl restart chatbot-backend
sudo systemctl restart nginx

# Database backup
pg_dump -U chatbot_user chatbot_db | gzip > backup.sql.gz
```

---

**Last Updated:** May 2026
**Created By:** ________________
**Reviewed By:** ________________
