from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.agent.agent import build_chat
from backend.api import chat, dashboard, meetings, slack, tasks, tools
from backend.config import load_settings
from backend.mcp.manager import build_mcp_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    mcp = build_mcp_client()
    await mcp.__aenter__()
    app.state.settings = settings
    app.state.mcp = mcp
    app.state.chat = build_chat(settings, mcp)
    try:
        yield
    finally:
        app.state.chat.close()
        await mcp.__aexit__(None, None, None)


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[item.strip() for item in settings.cors_origins.split(",") if item.strip()],
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(chat.router)
    app.include_router(dashboard.router)
    app.include_router(meetings.router)
    app.include_router(slack.router)
    app.include_router(tasks.router)
    app.include_router(tools.router)
    return app


app = create_app()
