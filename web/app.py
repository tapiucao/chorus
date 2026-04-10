from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core import runner
from core.errors import ChorusError, error_payload
from core.logging_utils import get_logger, log_event
from core.skills import STAGE_SKILLS
from db import database as db
from db.database import create_db_and_tables
from web.schemas import RunRequest
from web import services as web_services


WEB_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_ROOT / "templates"
STATIC_DIR = WEB_ROOT / "static"
engine = db.engine
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Chorus API", lifespan=lifespan)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _sync_service_dependencies() -> None:
    web_services.db.engine = engine
    web_services.db.create_db_and_tables = create_db_and_tables


@app.exception_handler(ChorusError)
async def handle_chorus_error(_: Request, exc: ChorusError) -> JSONResponse:
    log_event(logger, logging.ERROR, "http_request_failed", error_code=exc.code, error_message=str(exc))
    status_code = 400 if exc.code == "validation_error" else 502 if exc.code == "provider_error" else 500
    return JSONResponse(status_code=status_code, content=error_payload(exc))


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


def create_run(request: RunRequest, background_tasks: BackgroundTasks | None = None) -> dict:
    _sync_service_dependencies()

    if background_tasks is None:
        result = runner.run_chorus_pipeline(raw_input=request.idea, mode=request.mode)
        return web_services.build_sync_run_payload(result, request.mode)

    run_id = runner.create_run_record(mode=request.mode, current_stage="queued")
    background_tasks.add_task(runner.execute_run, run_id, request.idea, request.mode)
    return web_services.build_pending_run_payload(run_id=run_id, mode=request.mode, current_stage="queued")


@app.post("/api/runs")
def create_run_endpoint(request: RunRequest, background_tasks: BackgroundTasks) -> dict:
    return create_run(request, background_tasks)


@app.get("/api/runs/{run_id}")
def get_run(run_id: int) -> dict:
    _sync_service_dependencies()
    run = web_services.get_run_or_404(run_id)
    artifacts = web_services.get_artifacts_for_run(run_id)
    return web_services.build_run_payload(run=run, artifacts=artifacts, configured_skills=STAGE_SKILLS)


@app.get("/api/runs/{run_id}/download/output.json")
def download_output_json(run_id: int) -> JSONResponse:
    payload = get_run(run_id)
    return JSONResponse(content=payload)


@app.get("/api/runs/{run_id}/download/project-spec.md")
def download_project_spec_markdown(run_id: int) -> PlainTextResponse:
    _sync_service_dependencies()
    return PlainTextResponse(web_services.render_project_markdown_for_run(run_id), media_type="text/markdown")


@app.get("/api/runs/{run_id}/download/implementation-spec.md")
def download_implementation_spec_markdown(run_id: int) -> PlainTextResponse:
    _sync_service_dependencies()
    return PlainTextResponse(web_services.render_implementation_markdown_for_run(run_id), media_type="text/markdown")
