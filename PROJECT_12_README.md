# Project 12 — MCP Integration for Research Digest Agent

## 🎯 Objective

Project 12 migrates research evidence retrieval from direct arXiv calls inside the backend service to MCP (Model Context Protocol), while preserving all existing product behavior:

- Frontend remains unchanged
- API contracts remain unchanged
- Streaming remains unchanged
- Agent decision logic remains unchanged
- Prompt architecture remains unchanged

The only behavior change is tool execution path.

---

## ✅ Final Execution Path

### Before

Agent → Direct Tool Logic in service → arXiv API

### After

Agent → MCP Client → MCP Server Tool → arXiv API

---

## 📁 Project 12 Files

### New Files

- backend/app/services/mcp_client.py
- mcp_server/server.py
- mcp_server/tools/arxiv_tool.py

### Updated Files

- backend/app/services/research_digest_service.py
- backend/app/core/settings.py
- backend/requirements.txt
- .env.example

### Not Modified (by design)

- frontend/**
- backend/app/api/** request/response contracts
- backend/app/schemas/**
- backend/app/agent/** logic
- backend/app/prompts/** files

---

## 📚 Documentation Map

- Project overview: PROJECT_12_README.md
- Setup and run: PROJECT_12_QUICK_START.md
- Technical deep dive: PROJECT_12_MCP_INTEGRATION_GUIDE.md
- Verification checklist: PROJECT_12_IMPLEMENTATION_CHECKLIST.md
- Delivered implementation summary: PROJECT_12_IMPLEMENTATION_SUMMARY.md

---

## 🧩 What Changed in Practice

1. Research digest service no longer performs direct HTTP arXiv calls.
2. Service now calls MCP tool via mcp_client.call_tool("search_arxiv", ...).
3. MCP server exposes search_arxiv over stdio transport.
4. MCP tool handles retry, timeout, and response normalization.
5. Existing scoring, evidence thresholds, digest generation, and NDJSON streaming remain as-is.

---

## 🔧 Dependency Note

MCP requires AnyIO 4+. To resolve dependency conflicts, backend requirements were aligned to:

- fastapi==0.115.0
- anyio>=4.5,<5
- mcp==1.12.4

This combination resolves the previous resolver conflict and keeps FastAPI and MCP compatible.

---

## 🚀 Getting Started

See PROJECT_12_QUICK_START.md for installation, run commands, and local validation steps.

---

## ✅ Completion Status

Project 12 MCP integration is implemented and integrated with existing architecture using minimal change scope.
