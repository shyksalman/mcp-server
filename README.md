# Enigmatix OMS Assistant

A local, read-only employee assistant. Ollama selects tools from schemas discovered through MCP. The MCP server handles authentication and calls only personal attendance and leave APIs.

## Architecture

```text
User → CLI → Ollama → tool decision → MCP client → stdio MCP server
  → OMS client → Authentication API / Employee OMS API
  → MCP result → Ollama → natural-language response
```

The CLI never selects tools by keywords. It sends every available MCP tool schema to Ollama, then executes only the tool calls Ollama returns. Credentials and tokens stay inside the MCP server process.

## Prerequisites

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Ollama](https://ollama.com/download) running locally
- An Enigmatix OMS account with access to the personal attendance and leave endpoints

## Install and configure

From this directory:

```bash
uv sync --extra dev
cp .env.example .env
```

Fill in `OMS_EMAIL` and `OMS_PASSWORD` in `.env`. Every setting is loaded from `.env` or an environment variable; the API hosts, tenant, and model shown in `.env.example` are example values, not code defaults. Set `OLLAMA_MODEL` to any Ollama model that supports tool calls. Keep `OMS_REFRESH_PATH=` empty unless your deployment has a refresh endpoint; then set it to a path on the authentication host, such as `/api/v1/token/refresh/`. When empty, a 401 causes a fresh login. The exact OMS login and result JSON formats have not been verified against a live account; their mappings are isolated in `oms/auth.py`, `oms/attendance.py`, and `oms/leave.py`.

Start Ollama and pull the selected model:

```bash
ollama serve
ollama pull qwen3:8b
```

`ollama serve` can run in another terminal. Adjust the pull command to match `OLLAMA_MODEL` if needed.

## Run

The MCP server uses stdio, so it normally starts automatically as a child of the CLI. To start it directly for an MCP inspector or another host:

```bash
uv run python -m oms_mcp.server
```

Start the chat application:

```bash
uv run python -m assistant.main
```

Commands: `/tools` lists discovered tools, `/clear` clears this session's conversation, and `/exit` or `/quit` exits. Follow-up questions use the current conversation history. No history is saved to disk.

## Available tools

| Tool | OMS API | Purpose |
| --- | --- | --- |
| `get_my_attendance_stats()` | `GET /api/v1/attendance/attendance_stats` | Personal attendance statistics |
| `get_my_leaves(page=1, size=10)` | `GET /api/v1/leave/leave` | Personal leave requests; size 1–100 |
| `get_my_leave_summary()` | `GET /api/v1/leave/get-leaves-count/?page=1` | Leave counts or balance |

The raw OMS payload is temporarily included with normalized fields because the real response shapes are not documented. After inspecting a live response, update only the normalizers; the MCP and Ollama layers need no changes. For paginated leave history, the assistant can retrieve additional pages when needed.

## Test

Unit tests use mocked OMS HTTP responses and do not contact a real account:

```bash
uv run pytest -q
```

With valid credentials, run the manual live API smoke test:

```bash
uv run python -m oms_mcp.integration
```

Then use the CLI to verify actual model behavior: ask about leave status, pending leaves, latest five requests, leave balance, attendance, combined summaries, and an unrelated joke. Tool selection quality depends on the selected model. `/tools` confirms MCP discovery.

## Security

`.env` is ignored by Git. Authentication is internal and is never exposed as an MCP tool. Tool output contains OMS attendance and leave data, but no credentials or tokens. Version 1 has no write tools, arbitrary HTTP requests, or other employees' data. The local Ollama process receives the selected tool results to formulate answers, so run it in a trusted environment.

## Troubleshooting

- **Ollama unavailable:** start `ollama serve`, check `OLLAMA_BASE_URL`, and pull the configured model.
- **MCP server unavailable:** run `uv sync`, then try `uv run python -m oms_mcp.server`. Use `/tools` to confirm discovery.
- **Authentication failed:** check credentials, tenant, and the login response mapping in `oms/auth.py`.
- **401 after retry:** the client refreshes or logs in once and retries once; check account access or configure a valid `OMS_REFRESH_PATH`.
- **Permission or resource error:** confirm that the account can use the three personal OMS endpoints.
- **Missing balance or dates:** inspect the live API response in a secure development environment and update the normalizers. Do not add credentials to prompts or test fixtures.
# mcp-server
