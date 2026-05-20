# PostgreSQL Database Setup Guide

## Installation on Ubuntu

### Step 1: Install PostgreSQL

```bash
# Update packages
sudo apt-get update
sudo apt-get upgrade -y

# Install PostgreSQL and client
sudo apt-get install -y postgresql postgresql-contrib
```

### Step 2: Start PostgreSQL Service

```bash
# Start service
sudo systemctl start postgresql

# Enable on startup
sudo systemctl enable postgresql

# Check status
sudo systemctl status postgresql
```

### Step 3: Create Database and User

```bash
# Connect to PostgreSQL as root
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE USER chatbot_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE chatbot_db OWNER chatbot_user;

# Grant permissions
ALTER ROLE chatbot_user SET client_encoding TO 'utf8';
ALTER ROLE chatbot_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE chatbot_user SET default_transaction_deferrable TO on;
ALTER ROLE chatbot_user SET default_transaction_read_committed TO on;

# Exit PostgreSQL
\q
```

### Step 4: Test Connection

```bash
# From backend server
psql -h localhost -U chatbot_user -d chatbot_db
```

## Remote Connection (If Database on Different Server)

### Allow Remote Connections

1. Edit PostgreSQL configuration:
```bash
sudo nano /etc/postgresql/*/main/postgresql.conf

# Find and uncomment:
listen_addresses = '*'
```

2. Edit host-based authentication:
```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf

# Add line for backend server:
host    chatbot_db    chatbot_user    backend-server-ip/32    md5
```

3. Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

## Database URL Formats

### Local Connection (Backend on same server as DB)
```
postgresql://chatbot_user:password@localhost:5432/chatbot_db
```

### Remote Connection
```
postgresql://chatbot_user:password@db-server-ip:5432/chatbot_db
```

### Docker Compose Connection
```
postgresql://chatbot_user:password@postgres:5432/chatbot_db
```

## Backup and Restore

### Full Database Backup
```bash
pg_dump -h localhost -U chatbot_user -d chatbot_db > chatbot_backup.sql
```

### Full Database with Compression
```bash
pg_dump -h localhost -U chatbot_user -d chatbot_db | gzip > chatbot_backup.sql.gz
```

### Restore from Backup
```bash
psql -h localhost -U chatbot_user -d chatbot_db < chatbot_backup.sql
```

### Restore from Compressed Backup
```bash
gunzip -c chatbot_backup.sql.gz | psql -h localhost -U chatbot_user -d chatbot_db
```

## Scheduled Backups

Create a backup script:

```bash
#!/bin/bash
BACKUP_DIR="/backups/postgresql"
DB_USER="chatbot_user"
DB_NAME="chatbot_db"
DB_HOST="localhost"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACKUP_DIR

pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME | gzip > $BACKUP_DIR/chatbot_$TIMESTAMP.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "chatbot_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/chatbot_$TIMESTAMP.sql.gz"
```

Add to crontab:
```bash
# Backup daily at 2 AM
0 2 * * * /usr/local/bin/backup_postgres.sh
```

## Monitoring

### Check Database Size
```bash
sudo -u postgres psql -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database WHERE datname = 'chatbot_db';"
```

### Active Connections
```bash
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE datname = 'chatbot_db';"
```

### Connection Limits
```bash
# Check current limit
sudo -u postgres psql -c "SHOW max_connections;"

# Increase if needed (in postgresql.conf)
sudo nano /etc/postgresql/*/main/postgresql.conf
# max_connections = 200  # Increase as needed
sudo systemctl restart postgresql
```

## Performance Tuning

### Shared Buffers
```bash
# In postgresql.conf
shared_buffers = 256MB  # 25% of RAM for dedicated server
```

### Work Memory
```bash
# In postgresql.conf
work_mem = 16MB  # Per sort/hash operation
```

### Effective Cache Size
```bash
# In postgresql.conf
effective_cache_size = 1GB  # 50-75% of RAM
```

## Troubleshooting

### Connection Refused
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check if listening on correct port
sudo ss -tlnp | grep postgres

# Check logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Authentication Failed
```bash
# Verify user exists
sudo -u postgres psql -c "\du"

# Verify database exists
sudo -u postgres psql -c "\l"

# Test connection
psql -h localhost -U chatbot_user -d chatbot_db
```

### Out of Disk Space
```bash
# Check disk usage
df -h

# Analyze table sizes
sudo -u postgres psql -d chatbot_db << 'EOF'
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
EOF
```

## Database Migrations (Alembic)

If your application uses Alembic for migrations:

```bash
cd /var/www/chatbot-backend
source venv/bin/activate

# Create migration
alembic revision --autogenerate -m "your migration description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Advanced: Connection Pooling

For production with many connections, consider PgBouncer:

```bash
sudo apt-get install -y pgbouncer

# Configure /etc/pgbouncer/pgbouncer.ini
# See documentation for connection pool settings
```

---

**Last Updated:** May 2026
