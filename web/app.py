from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from core import runner
from core.config import settings
from core.errors import ChorusError, error_payload
from core.logging_utils import get_logger, log_event
from core.skills import STAGE_SKILLS
from db.database import create_db_and_tables, engine
from web import services as web_services
from web.schemas import RunRequest

WEB_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_ROOT / "templates"
STATIC_DIR = WEB_ROOT / "static"
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    create_db_and_tables()
    yield


app = FastAPI(title="Chorus API", lifespan=lifespan)

# CORS: same-origin only by default (UI is served by this app).
# To allow external clients set CHORUS_CORS_ORIGINS=http://localhost:3000,https://app.example.com
_cors_origins = [o.strip() for o in (settings.cors_origins or "").split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_db_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


_bearer = HTTPBearer(auto_error=False)


def require_api_key(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> None:
    """Enforce API key auth when CHORUS_API_KEY is configured. No-op in dev (key not set)."""
    if settings.api_key is None:
        return
    if credentials is None or credentials.credentials != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.exception_handler(ChorusError)
async def handle_chorus_error(_: Request, exc: ChorusError) -> JSONResponse:
    log_event(logger, logging.ERROR, "http_request_failed", error_code=exc.code, error_message=str(exc))
    status_code = 400 if exc.code == "validation_error" else 502 if exc.code == "provider_error" else 500
    return JSONResponse(status_code=status_code, content=error_payload(exc))


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


def create_run(request: RunRequest, background_tasks: BackgroundTasks | None = None) -> dict:
    if background_tasks is None:
        result = runner.run_chorus_pipeline(raw_input=request.idea, mode=request.mode)
        return web_services.build_sync_run_payload(result, request.mode)

    run_id = runner.create_run_record(mode=request.mode, current_stage="queued")
    background_tasks.add_task(runner.execute_run, run_id, request.idea, request.mode)
    return web_services.build_pending_run_payload(run_id=run_id, mode=request.mode, current_stage="queued")


@app.post("/api/runs", dependencies=[Depends(require_api_key)])
def create_run_endpoint(request: RunRequest, background_tasks: BackgroundTasks) -> dict:
    return create_run(request, background_tasks)


@app.get("/api/runs/{run_id}")
def get_run(run_id: int, session: Session = Depends(get_db_session)) -> dict:
    run = web_services.get_run_or_404(run_id, session)
    artifacts = web_services.get_artifacts_for_run(run_id, session)
    return web_services.build_run_payload(
        run=run, artifacts=artifacts, configured_skills=cast(dict[str, Any], STAGE_SKILLS)
    )


@app.get("/api/runs/{run_id}/download/output.json")
def download_output_json(run_id: int, session: Session = Depends(get_db_session)) -> JSONResponse:
    run = web_services.get_run_or_404(run_id, session)
    artifacts = web_services.get_artifacts_for_run(run_id, session)
    payload = web_services.build_run_payload(
        run=run, artifacts=artifacts, configured_skills=cast(dict[str, Any], STAGE_SKILLS)
    )
    return JSONResponse(content=payload)


@app.get("/api/runs/{run_id}/download/project-spec.md")
def download_project_spec_markdown(run_id: int, session: Session = Depends(get_db_session)) -> PlainTextResponse:
    return PlainTextResponse(web_services.render_project_markdown_for_run(run_id, session), media_type="text/markdown")


@app.get("/api/runs/{run_id}/download/implementation-spec.md")
def download_implementation_spec_markdown(run_id: int, session: Session = Depends(get_db_session)) -> PlainTextResponse:
    return PlainTextResponse(
        web_services.render_implementation_markdown_for_run(run_id, session), media_type="text/markdown"
    )
