from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sleep_agent.agent.graph import AgentService
from sleep_agent.api.routes import chat, metrics, sessions
from sleep_agent.settings import load_settings
from sleep_agent.storage.database import initialize_database
from sleep_agent.storage.repository import Repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    initialize_database(settings.database_path)
    repository = Repository(settings.database_path)
    app.state.settings = settings
    app.state.repository = repository
    app.state.agent = AgentService(settings, repository)
    yield


app = FastAPI(title="Linka Sleep Health Agent", version="0.1.0", lifespan=lifespan)
app.include_router(sessions.router)
app.include_router(metrics.router)
app.include_router(chat.router)


@app.get("/health")
def health(request: Request):
    return {"status": "ok", "llm_configured": request.app.state.settings.llm_configured,
            "mode": "llm" if request.app.state.settings.llm_configured else "offline_demo"}


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={
        "error": "internal_error", "message": "The request could not be completed.",
        "request_id": str(uuid4()),
    })

