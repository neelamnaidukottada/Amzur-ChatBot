# Project 12 — Quick Start

## 1) Install Backend Dependencies

From workspace root:

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If your environment has cached conflicting versions:

```bash
python -m pip install --no-cache-dir -r requirements.txt
```

---

## 2) Start Backend API

```bash
cd backend
venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Backend starts at:

- http://localhost:8000

---

## 3) Start Frontend (Unchanged)

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend starts at:

- http://localhost:5173

---

## 4) MCP Runtime Behavior

No separate MCP server terminal is required during normal backend usage.

The backend MCP client starts the MCP server over stdio automatically when research digest calls the tool.

Optional manual MCP server run (debug):

```bash
cd .
backend\venv\Scripts\python.exe mcp_server\server.py
```

---

## 5) Required Environment Variables

Add or verify in your env setup:

```env
RESEARCH_MCP_SERVER_COMMAND=
RESEARCH_MCP_SERVER_SCRIPT=./mcp_server/server.py
RESEARCH_MCP_SERVER_CWD=.
RESEARCH_MCP_TOOL_TIMEOUT_SECONDS=45
RESEARCH_MCP_LOG_LEVEL=INFO
RESEARCH_ARXIV_MAX_RETRIES=3
RESEARCH_ARXIV_BACKOFF_SECONDS=1.0
RESEARCH_ARXIV_MIN_REQUEST_INTERVAL_SECONDS=3.5
RESEARCH_ARXIV_TIMEOUT_SECONDS=30
RESEARCH_ARXIV_USER_AGENT=amzur-research-digest/1.0 (mailto:support@example.com)
```

---

## 6) Smoke Test

Trigger your existing Research Digest flow from UI or API.

Expected behavior:

- Same request shape as before
- Same streaming event structure as before
- Same digest output structure as before
- Evidence retrieval routed through MCP internally

---

## 7) Troubleshooting

### pip resolver conflict mentioning AnyIO

Use the pinned compatible stack in requirements:

- fastapi==0.115.0
- anyio>=4.5,<5
- mcp==1.12.4

Then reinstall with no cache.

### MCP tool call timeout

Increase:

- RESEARCH_MCP_TOOL_TIMEOUT_SECONDS

### arXiv rate limit warnings

Tune:

- RESEARCH_ARXIV_MAX_RETRIES
- RESEARCH_ARXIV_BACKOFF_SECONDS
- RESEARCH_ARXIV_MIN_REQUEST_INTERVAL_SECONDS

### MCP server path error

Verify:

- RESEARCH_MCP_SERVER_SCRIPT points to mcp_server/server.py
- RESEARCH_MCP_SERVER_CWD points to workspace root
