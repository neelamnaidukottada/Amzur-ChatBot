# Project 12 — Implementation Checklist

## Status: ✅ Completed

---

## A. MCP Server

- [x] Created mcp_server/server.py
- [x] Registered tool: search_arxiv(query, max_results)
- [x] Enabled async execution
- [x] Added logging setup
- [x] Configured stdio transport

## B. MCP Tool Logic

- [x] Created mcp_server/tools/arxiv_tool.py
- [x] Implemented arXiv HTTP retrieval
- [x] Implemented retry and exponential backoff
- [x] Implemented timeout handling
- [x] Implemented min request interval handling
- [x] Parsed Atom XML response
- [x] Normalized tool result shape

## C. Backend Service Layer

- [x] Created backend/app/services/mcp_client.py
- [x] Added session initialization and tool calling
- [x] Updated research_digest_service.py to use MCP call_tool
- [x] Removed direct arXiv HTTP path from research service
- [x] Preserved request/response schemas and API contract

## D. Agent and Prompt Preservation

- [x] Agent behavior preserved
- [x] Streaming behavior preserved
- [x] Frontend unchanged
- [x] Prompt files not rebuilt or redesigned

Note:

- Existing prompt-folder path for this feature is not explicitly present as backend/app/prompts in this repo layout; no prompt architecture rewrite was performed.

## E. Configuration and Dependencies

- [x] Added MCP settings in backend/app/core/settings.py
- [x] Added env examples in .env.example
- [x] Added MCP dependency to backend/requirements.txt
- [x] Resolved AnyIO/FastAPI/MCP version conflict with compatible pins

## F. Validation

- [x] Static checks on touched files passed
- [x] End-to-end MCP call probe returned normalized paper payload
- [x] Requirements resolver check passed after dependency alignment

---

## Final Flow Verification

- [x] Before: Agent → Direct Tool → arXiv
- [x] After: Agent → MCP Client → MCP Server → arXiv

---

## Open Risk Notes

- [ ] Add automated integration test for MCP tool path in CI (recommended)
- [ ] Add FastAPI lifespan hook for graceful MCP session shutdown (recommended)
