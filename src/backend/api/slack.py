from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Query

from assistant.mcp_client import MultiMCPClient
from assistant.tool_adapter import result_for_model
from backend.dependencies import mcp

router = APIRouter(prefix="/api/slack", tags=["slack"])


async def _call(client: MultiMCPClient, tool: str, args: dict) -> dict:
    try:
        result = await client.call_tool(tool, args)
        return json.loads(result_for_model(result) or "{}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Slack is unavailable") from exc


@router.get("/conversations")
async def conversations(
    filter: str = Query(default="all", pattern="^(all|channels|dm|mpim)$"),
    client: MultiMCPClient = Depends(mcp),
) -> dict:
    types = {
        "channels": ["public_channel", "private_channel"],
        "dm": ["im"],
        "mpim": ["mpim"],
    }.get(filter, ["public_channel", "private_channel", "im", "mpim"])
    return await _call(client, "list_slack_conversations", {"types": types, "limit": 100})


@router.get("/messages/{conversation_id}")
async def messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    client: MultiMCPClient = Depends(mcp),
) -> dict:
    return await _call(client, "get_slack_messages", {"conversation_id": conversation_id, "limit": limit, "cursor": cursor})


@router.get("/threads/{conversation_id}")
async def threads(
    conversation_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    client: MultiMCPClient = Depends(mcp),
) -> dict:
    return await _call(
        client,
        "list_slack_threads",
        {
            "conversation_id": conversation_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "limit": limit,
        },
    )


@router.get("/thread/{conversation_id}/{thread_ts}")
async def thread(conversation_id: str, thread_ts: str, client: MultiMCPClient = Depends(mcp)) -> dict:
    return await _call(client, "get_slack_thread", {"conversation_id": conversation_id, "thread_ts": thread_ts, "limit": 100})


@router.get("/search")
async def search(query: str, limit: int = Query(default=50, ge=1, le=100), client: MultiMCPClient = Depends(mcp)) -> dict:
    return await _call(client, "search_slack_messages", {"query": query, "limit": limit})
