# Employee AI Copilot

A local employee copilot that uses Ollama and dynamically discovered MCP tools for Enigmatix OMS, Calendar, ClickUp, and Slack. The original OMS integration remains intact, and each external system lives in its own MCP server.

## Architecture

```text
Web Browser → Next.js Frontend → FastAPI Backend → AI Agent / Host
  → Ollama tool decision → MCP client
  → OMS MCP / Calendar MCP / ClickUp MCP / Slack MCP
  → tool results → Ollama → natural-language response
```

The assistant does not select tools with keyword routing. The host discovers tool schemas from registered MCP servers, sends those schemas to Ollama, and executes the tool calls Ollama returns. Credentials and tokens stay inside backend and MCP server processes.

## Prerequisites

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Ollama](https://ollama.com/download) running locally
- An Enigmatix OMS account with access to the personal attendance and leave endpoints
- Optional ClickUp API token/workspace/user id
- Optional calendar OAuth credentials for future Google/Microsoft providers
- Optional Slack app with bot token and least-privilege scopes

## Install and Configure

```bash
uv sync --extra dev
cp .env.example .env
```

Fill in `OMS_EMAIL` and `OMS_PASSWORD` in `.env`. Set `OLLAMA_MODEL` to a model that supports tool calls. Keep `OMS_REFRESH_PATH=` empty unless your deployment has a refresh endpoint; then set it to a path on the authentication host, such as `/api/v1/token/refresh/`.

For ClickUp, set:

```bash
CLICKUP_API_TOKEN=
CLICKUP_WORKSPACE_ID=
CLICKUP_USER_ID=
```

The Calendar MCP defaults to `CALENDAR_PROVIDER=local`, which gives a development calendar while preserving the provider adapter boundary for Google Calendar or Microsoft Outlook.

For Slack, set:

```bash
SLACK_BOT_TOKEN=
SLACK_APP_TOKEN=
SLACK_TEAM_ID=
SLACK_MAX_BULK_RECIPIENTS=20
```

Read scopes depend on enabled features, but commonly include `users:read`, `users:read.email`, `channels:read`, `groups:read`, `im:read`, `mpim:read`, `channels:history`, `groups:history`, `im:history`, and `mpim:history`. Write features need `chat:write`, `im:write`, and `mpim:write`. The Slack MCP returns permission errors when the app cannot access a conversation.

## Run

Start Ollama and pull the selected model:

```bash
ollama serve
ollama pull qwen3:8b
```

Start the FastAPI backend:

```bash
PYTHONPATH=src uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Start the Next.js frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Conversation Memory

Each browser is assigned a private conversation ID. The backend stores that
conversation's user, assistant, and tool context in SQLite, sends the retained
context with later questions, and restores visible chat history after a page or
backend restart. The trash button starts a new conversation and deletes the old
one from the backend.

Memory is bounded by `CHAT_MAX_CONTEXT_MESSAGES` per conversation and
`CHAT_MAX_CONVERSATIONS` overall. Set `CHAT_MEMORY_PATH` to choose the SQLite
database location. Docker Compose stores it in the `chat-memory` volume.

The CLI still works:

```bash
uv run python -m assistant.main
```

## MCP Servers

The MCP servers use stdio and normally start automatically as children of the backend/CLI. To start them directly for an MCP inspector or another host:

```bash
uv run python -m oms_mcp.server
uv run python -m calendar_mcp.server
uv run python -m clickup_mcp.server
uv run python -m slack_mcp.server
```

Inspector examples:

```bash
npx @modelcontextprotocol/inspector env PYTHONPATH=src python -m slack_mcp.server
npx @modelcontextprotocol/inspector env PYTHONPATH=src python -m calendar_mcp.server
```

## Available MCP Tools

OMS:

| Tool | Purpose |
| --- | --- |
| `get_my_attendance_stats()` | Personal attendance statistics |
| `get_my_leaves(page=1, size=10)` | Personal leave requests |
| `get_my_leave_summary()` | Leave counts or balance |

Calendar:

| Tool | Purpose |
| --- | --- |
| `list_my_meetings()` | Meetings/events for a date range |
| `get_meeting()` | Meeting details |
| `create_meeting()` | Create a meeting after backend confirmation |
| `check_calendar_availability()` | Conflict check for a time range |
| `find_free_slots()` | Free slots for a date and duration |

ClickUp:

| Tool | Purpose |
| --- | --- |
| `get_my_clickup_tasks()` | Assigned task list with filters |
| `get_clickup_task()` | Task details |
| `get_task_summary()` | Aggregated workload counts |
| `get_tasks_due_today()` | Tasks due today |
| `get_overdue_tasks()` | Overdue tasks |
| `get_high_priority_tasks()` | Urgent/high priority tasks |

Slack:

| Tool | Purpose |
| --- | --- |
| `list_slack_users()` | Visible Slack user directory |
| `find_slack_user()` | Resolve a Slack user by name or email |
| `prepare_slack_message()` | Resolve recipients and prepare a send preview |
| `send_slack_dm()` | Send one direct message after confirmation |
| `send_slack_message_to_users()` | Send separate individual DMs after confirmation |
| `send_slack_group_message()` | Send one group DM after confirmation |
| `post_slack_channel_message()` | Post to an existing channel after confirmation |
| `list_slack_conversations()` | Visible channels, DMs, and group DMs |
| `find_slack_conversation()` | Resolve a channel/conversation by name or id |
| `get_slack_messages()` | Conversation history with pagination |
| `list_slack_threads()` | Lightweight thread metadata |
| `get_slack_thread()` | Parent and replies for one thread |
| `search_slack_messages()` | Authorized Slack message search |
| `get_recent_slack_activity()` | Small recent activity sample for briefs |
| `summarize_slack_thread()` | Retrieve a thread for AI summarization |
| `get_slack_action_items()` | Retrieve a thread for action-item extraction |

Write tools are guarded in backend code. A natural-language request to create a meeting or send Slack messages produces a pending action first. The action executes only after explicit confirmation.

## Test

Unit tests use mocked external responses and do not contact a real account:

```bash
uv run pytest -q
```

If `uv` is unavailable in your environment, use the active virtualenv:

```bash
PYTHONPATH=src python -m pytest -q
```

## Docker

```bash
docker compose up --build
```

This starts backend, frontend, and an Ollama container. You can also point `OLLAMA_BASE_URL` at an existing Ollama instance.

## Security

`.env` is ignored by Git. Authentication is internal and is never exposed as an MCP tool. API tokens and OAuth secrets stay in backend/MCP server environment variables and are not sent to the frontend. The local Ollama process receives selected tool results to formulate answers, so run it in a trusted environment.

## Troubleshooting

- **Ollama unavailable:** start `ollama serve`, check `OLLAMA_BASE_URL`, and pull the configured model.
- **MCP server unavailable:** run `uv sync`, then use `/tools` or `GET /api/tools` to confirm discovery.
- **Authentication failed:** check credentials, tenant, and the login response mapping in `oms/auth.py`.
- **ClickUp unavailable:** check `CLICKUP_API_TOKEN`, `CLICKUP_WORKSPACE_ID`, and rate limits.
- **Slack unavailable:** check `SLACK_BOT_TOKEN`, app scopes, app membership in private channels, and Slack rate limits.
- **Calendar auth expired:** the provider boundary is ready for OAuth refresh handling; the local provider does not require OAuth.
