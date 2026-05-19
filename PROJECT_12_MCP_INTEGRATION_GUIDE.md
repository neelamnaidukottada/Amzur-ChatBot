# Project 12 — MCP Integration Technical Guide

## 1. Scope

This project introduces MCP for research evidence retrieval without changing existing product interfaces or user-facing behavior.

### In Scope

- Add MCP server with arXiv tool
- Add backend MCP client
- Route research digest evidence retrieval through MCP
- Keep existing scoring, analysis, and streaming logic intact

### Out of Scope

- Frontend redesign
- API contract changes
- Agent behavior redesign
- Prompt architecture rewrite

---

## 2. Architecture

## Before

ResearchDigestService
→ _search_arxiv direct HTTP calls
→ parse XML
→ apply constraints
→ score and analyze

## After

ResearchDigestService
→ MCPClient.call_tool(search_arxiv)
→ MCP server tool executes arXiv retrieval
→ normalized payload returned
→ apply constraints in service
→ score and analyze

---

## 3. File-by-File Breakdown

## backend/app/services/mcp_client.py

Responsibilities:

- Create and maintain stdio MCP client session
- Launch local MCP server process
- Call named tool with arguments
- Enforce tool call timeout
- Normalize returned payload to service-friendly shape

Key points:

- Uses mcp ClientSession + stdio transport
- Reads server command/script/cwd from settings
- Exposes call_tool(tool_name, arguments)

## mcp_server/server.py

Responsibilities:

- Bootstrap FastMCP server
- Register search_arxiv tool
- Run stdio transport for local backend client usage

Key points:

- Tool is async
- Server logging level uses RESEARCH_MCP_LOG_LEVEL

## mcp_server/tools/arxiv_tool.py

Responsibilities:

- Query arXiv Atom endpoint
- Handle retry, timeout, and min interval controls
- Parse Atom XML
- Return normalized papers

Normalized record shape:

- id
- title
- authors
- summary
- published
- url
- categories

## backend/app/services/research_digest_service.py

Changes made:

- Replaced direct arXiv HTTP logic inside _search_arxiv
- Added MCP client usage via self.mcp_client.call_tool(...)
- Preserved all downstream behavior:
  - constraints filtering
  - relevance and quality scoring
  - evidence threshold decision
  - paper analysis
  - digest assembly
  - NDJSON streaming events

---

## 4. Data Flow

1. Research endpoint triggers digest workflow.
2. Service computes search query and paging values.
3. Service calls MCP tool search_arxiv.
4. MCP tool fetches and normalizes arXiv records.
5. Service receives normalized papers and applies existing filters.
6. Existing embedding scoring and decision loops run unchanged.
7. Existing final digest payload and streaming are produced unchanged.

---

## 5. Reliability Controls

Implemented in MCP tool:

- Timeout control
- Exponential backoff
- Retry attempts
- Rate-limit aware empty-return fallback
- Logging for each retry/failure path

Implemented in MCP client:

- Tool-level timeout on call
- Session initialization logging
- Tool list introspection for diagnostics

---

## 6. Configuration

New settings consumed by backend:

- RESEARCH_MCP_SERVER_COMMAND
- RESEARCH_MCP_SERVER_SCRIPT
- RESEARCH_MCP_SERVER_CWD
- RESEARCH_MCP_TOOL_TIMEOUT_SECONDS
- RESEARCH_MCP_LOG_LEVEL

ArXiv behavior remains configurable via:

- RESEARCH_ARXIV_MAX_RETRIES
- RESEARCH_ARXIV_BACKOFF_SECONDS
- RESEARCH_ARXIV_MIN_REQUEST_INTERVAL_SECONDS
- RESEARCH_ARXIV_TIMEOUT_SECONDS
- RESEARCH_ARXIV_USER_AGENT

---

## 7. Dependency Compatibility

To support MCP and avoid resolver conflicts:

- mcp pinned to 1.12.4
- anyio moved to >=4.5,<5
- fastapi aligned to 0.115.0

This keeps MCP and FastAPI stack compatible.

---

## 8. Validation Strategy

Recommended checks:

1. Install dependencies in clean venv.
2. Start backend and frontend unchanged.
3. Trigger research digest endpoint with known query.
4. Confirm streaming responses are still emitted.
5. Confirm output schema remains unchanged.
6. Review logs for MCP tool invocation and arXiv fetch behavior.

---

## 9. Rollback Strategy

If rollback is needed:

1. Revert mcp_client integration in research_digest_service.py.
2. Restore direct arXiv retrieval implementation.
3. Remove MCP files and dependency pins.
4. Keep API and frontend untouched.

Because integration was isolated to service-tool boundary, rollback is low risk.
