# Deployment Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           DEPLOYMENT ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────────────┘

                              INTERNET / DNS
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
           ┌─────────────────────┐      ┌──────────────────────┐
           │                     │      │                      │
           │  FRONTEND SERVER    │      │  BACKEND SERVER      │
           │  (Ubuntu 20.04+)    │      │  (Ubuntu 20.04+)     │
           │  IP: x.x.x.x:80     │      │  IP: y.y.y.y:8000    │
           │                     │      │                      │
       ┌───┼─────────────────────┼──────┼──────────────────────┼───┐
       │   │   ┌──────────────┐  │      │   ┌──────────────────┤   │
       │   │   │   Nginx      │  │◄─────┼──►│   Uvicorn        │   │
       │   │   │ :80 / :443   │  │      │   │ :8000            │   │
       │   │   │              │  │      │   │                  │   │
       │   │   │  React App   │  │      │   │ FastAPI App      │   │
       │   │   │  dist/       │  │      │   │ /app/main.py     │   │
       │   │   │              │  │      │   │                  │   │
       │   │   │ Compress:    │  │      │   │ Authentication   │   │
       │   │   │ - GZip       │  │      │   │ Chat Logic       │   │
       │   │   │ - Caching    │  │      │   │ Data Processing  │   │
       │   │   │              │  │      │   │                  │   │
       │   │   └──────────────┘  │      │   │ Workers: 4       │   │
       │   │         │           │      │   │ Max Connections: │   │
       │   │         │(HTTP/API) │      │   │ Dynamic          │   │
       │   │         │           │      │   │                  │   │
       │   │    ┌────►───────────┼──────┼──►└──────────────────┼───┘
       │   │    │               │      │
       │   └────┼───────────────┘      │
       │        │                      │
       │        │  HTTP Requests       │   ┌──────────────────┐
       │        │  /api/*              │   │  PostgreSQL DB   │
       │        │                      │   │  :5432           │
       │        │                      ├──►│                  │
       │        │                      │   │ - Users          │
       │        │                      │   │ - Conversations  │
       │        │                      │   │ - Messages       │
       │        │                      │   │                  │
       │        │                      │   └──────────────────┘
       │        │                      │
       │        │                      │   ┌──────────────────┐
       │        │                      │   │  ChromaDB        │
       │        │                      ├──►│  Vector Store    │
       │        │                      │   │                  │
       │        │                      │   │ - Embeddings     │
       │        │                      │   │ - RAG Vector DB  │
       │        │                      │   │                  │
       │        │                      │   └──────────────────┘
       │        │                      │
       │        └──────────────────────┤   ┌──────────────────┐
       │                               │   │  External APIs   │
       │                               ├──►│                  │
       │                               │   │ - OpenAI         │
       │                               │   │ - Google Gemini  │
       │                               │   │ - LiteLLM Proxy  │
       │                               │   │                  │
       │                               │   └──────────────────┘
       │                               │
       └───────────────────────────────┘
```

## Directory Structure on Servers

### Frontend Server

```
/var/www/chatbot-frontend/
├── dist/                    # Built React application (nginx serves)
│   ├── index.html
│   ├── assets/              # JS/CSS bundles
│   │   ├── main.xxx.js
│   │   ├── main.xxx.css
│   │   └── ...
│   └── favicon.ico
│
/etc/nginx/
├── sites-available/
│   └── chatbot-frontend     # Nginx virtual host config
└── sites-enabled/
    └── chatbot-frontend     # Symlink to available config

/var/log/nginx/
├── access.log               # HTTP request logs
└── error.log                # Nginx error logs
```

### Backend Server

```
/var/www/chatbot-backend/
├── venv/                    # Python virtual environment
│   ├── bin/
│   │   ├── python
│   │   ├── pip
│   │   └── uvicorn
│   └── lib/
│       └── python3.11/
│           └── site-packages/
│
├── app/                     # Application source code
│   ├── main.py              # FastAPI entry point
│   ├── ai/                  # LLM logic
│   ├── api/                 # API endpoints
│   ├── core/                # Core functionality
│   ├── schemas/             # Request/response schemas
│   └── services/            # Business logic
│
├── chroma_db/               # Vector database storage
│   └── [embeddings]
│
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
│
/etc/systemd/system/
└── chatbot-backend.service  # Systemd service config

/var/log/
└── journal/                 # Systemd logs (journalctl)
```

## Deployment Workflow

### Initial Setup

```
1. Clone/Copy Code
   ├── Frontend source → deployment/frontend-server/app
   └── Backend source  → deployment/backend-server/app

2. Configure Deployment Files
   ├── Update .env files with credentials
   ├── Update IP addresses
   └── Review configurations

3. Transfer to Servers
   ├── Frontend files → Frontend Server
   └── Backend files  → Backend Server

4. Run Setup Scripts
   ├── Frontend: sudo ./setup.sh (installs Node, Nginx)
   └── Backend:  sudo ./setup.sh (installs Python, services)

5. Build & Deploy
   ├── Frontend: npm build → copy to /var/www/
   └── Backend:  source activate → start service

6. Verify & Test
   ├── Frontend endpoint: http://frontend-ip
   ├── Backend endpoint: http://backend-ip:8000/health
   └── Integration: Frontend → Backend communication
```

## Data Flow

### User Registration/Login

```
Client Browser
    │
    ├─ POST /api/auth/register
    │       │
    │       ▼
    │   Nginx (proxy_pass)
    │       │
    │       ▼
    │   FastAPI /api/auth/register
    │       │
    │       ├─ Validate input (Pydantic schema)
    │       ├─ Hash password (bcrypt)
    │       ├─ Create user record
    │       │       │
    │       │       ▼
    │       │   PostgreSQL
    │       │       │
    │       ├─ Generate JWT token
    │       │
    │       ▼
    │   Return token + user info
    │       │
    │       ▼
    │   Browser stores token (localStorage/sessionStorage)
```

### Chat Message Flow

```
Client Browser
    │
    ├─ POST /api/chat
    │   Headers: Authorization: Bearer <token>
    │   Body: { message: "Hello" }
    │       │
    │       ▼
    │   Nginx (routes to backend)
    │       │
    │       ▼
    │   FastAPI
    │       ├─ Verify JWT token
    │       ├─ Load conversation from PostgreSQL
    │       ├─ Add message to chat history
    │       │       │
    │       │       ▼
    │       │   PostgreSQL
    │       │
    │       ├─ Generate embedding (LangChain)
    │       ├─ Store in ChromaDB vector store
    │       │       │
    │       │       ▼
    │       │   ChromaDB
    │       │
    │       ├─ Call LLM (via LiteLLM proxy)
    │       │       │
    │       │       ▼
    │       │   OpenAI / Google Gemini
    │       │       │
    │       │       ▼
    │       │   LLM response
    │       │
    │       ├─ Store response in PostgreSQL
    │       │       │
    │       │       ▼
    │       │   PostgreSQL
    │       │
    │       ▼
    │   Return response to frontend
    │       │
    │       ▼
    Browser displays message
```

## Service Dependencies

```
Frontend Service
    └── Nginx
        └── Depends on: port 80 available
        └── Serves: React dist files
        └── Proxies: /api → Backend

Backend Service
    ├── Python Virtual Environment
    ├── Uvicorn Application Server
    ├── FastAPI Framework
    │
    ├─► PostgreSQL Database
    │   ├── User data
    │   ├── Conversation history
    │   └── Message storage
    │
    ├─► ChromaDB Vector Store
    │   ├── Embeddings
    │   └── RAG data
    │
    ├─► External LLM APIs
    │   ├── OpenAI
    │   ├── Google Gemini
    │   └── LiteLLM Proxy
    │
    └─► Environment Configuration
        ├── .env file
        ├── API keys
        └── Database credentials
```

## Network Flows

### Port Usage

```
Frontend Server:
├── :22   (SSH) - restricted to admin IPs
├── :80   (HTTP) - public, redirects to HTTPS if enabled
├── :443  (HTTPS) - public, uses Let's Encrypt cert
└── :3000 (dev only) - not in production

Backend Server:
├── :22    (SSH) - restricted to admin IPs
├── :8000  (FastAPI) - internal or restricted to frontend server only
├── :5432  (PostgreSQL) - internal only, no remote access
└── localhost:3000 (dev only) - not in production
```

### Firewall Configuration

```
Frontend Server (UFW):
    sudo ufw allow 22/tcp      # SSH
    sudo ufw allow 80/tcp      # HTTP
    sudo ufw allow 443/tcp     # HTTPS
    sudo ufw enable

Backend Server (UFW):
    sudo ufw allow 22/tcp              # SSH
    sudo ufw allow 8000/tcp from a.a.a.a  # Only from frontend
    sudo ufw deny 5432/tcp             # No remote DB access
    sudo ufw enable
```

## High Availability Considerations

### Current Single-Instance Setup
```
1 Frontend Server (single point of failure)
1 Backend Server (single point of failure)
1 Database (single point of failure)
```

### Scaling to HA (future)
```
Load Balancer (HAProxy/nginx)
    │
    ├─► Frontend Server 1
    ├─► Frontend Server 2
    └─► Frontend Server 3

Load Balancer (HAProxy/nginx)
    │
    ├─► Backend Server 1
    ├─► Backend Server 2
    └─► Backend Server 3

Database Cluster
    ├─► Primary PostgreSQL
    ├─► Replica PostgreSQL (hot standby)
    └─► Backup PostgreSQL
```

## Security Model

```
1. Network Layer
   ├── Firewall (UFW) - port-based
   └── SSH key-based auth only (no passwords)

2. Application Layer
   ├── JWT token validation
   ├── HTTPS/SSL encryption
   ├── CORS policy configured
   └── Input validation (Pydantic)

3. Database Layer
   ├── PostgreSQL authentication
   ├── Role-based access control
   ├── Encrypted connections (optional)
   └── Regular backups

4. Secrets Management
   ├── .env files (not in git)
   ├── Environment variables
   ├── Systemd service isolation
   └── File permission restrictions (0600 for .env)
```

## Monitoring Points

```
Frontend:
├── Nginx process status
├── Nginx error logs
├── Nginx access logs
├── Disk space (dist files)
├── HTTP response times
└── HTTPS certificate expiry

Backend:
├── Uvicorn process status
├── Service logs (journalctl)
├── Database connectivity
├── Response times
├── CPU/Memory usage
├── Database connection pool
└── Disk space (ChromaDB)

Database:
├── PostgreSQL service status
├── Connection count
├── Query performance
├── Disk space
├── Backup status
└── Replication lag (if HA)
```

---

**Version:** 1.0
**Last Updated:** May 2026
**Architecture Type:** Monolithic (Single Backend)
**Recommended For:** Up to 1000 concurrent users
