from __future__ import annotations

import logging
from typing import Any, TypedDict

from sqlmodel import Session

from core.errors import ChorusError, classify_exception
from core.logging_utils import get_logger, log_event
from core.models import Run, RunStatus
from db.database import create_db_and_tables, engine
from graph import build_chorus_graph


class RunExecutionResult(TypedDict):
    run_id: int
    status: str
    project_spec: Any
    implementation_spec: Any
    pending_checkpoint: Any
    current_stage: str | None


logger = get_logger(__name__)


def _update_run_state(run_id: int, status: RunStatus, current_stage: str | None = None) -> None:
    """Persist the latest run status to SQLite."""
    with Session(engine) as session:
        db_run = session.get(Run, run_id)
        if not db_run:
            return

        db_run.status = status
        if current_stage is not None:
            db_run.current_stage = current_stage
        session.commit()


def _build_run_result(run_id: int, status: str, final_state: dict[str, Any]) -> RunExecutionResult:
    return {
        "run_id": run_id,
        "status": status,
        "project_spec": final_state.get("project_spec"),
        "implementation_spec": final_state.get("implementation_spec"),
        "pending_checkpoint": final_state.get("pending_checkpoint"),
        "current_stage": final_state.get("current_stage"),
    }


def create_run_record(mode: str, current_stage: str = "intake") -> int:
    """Create a persisted run record and return its identifier."""
    create_db_and_tables()

    with Session(engine) as session:
        run = Run(mode=mode, status=RunStatus.running, current_stage=current_stage)
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id


def execute_run(run_id: int, raw_input: str, mode: str) -> RunExecutionResult:
    """Execute the Chorus graph for an existing run identifier."""
    if not raw_input or not raw_input.strip():
        raise classify_exception(ValueError("raw_input must not be empty"))

    create_db_and_tables()
    _update_run_state(run_id, RunStatus.running, "intake")
    log_event(logger, logging.INFO, "run_started", run_id=run_id, mode=mode, current_stage="intake")

    initial_state = {
        "run_id": run_id,
        "mode": mode,
        "raw_input": raw_input,
        "loop_count": 0,
        "current_stage": "intake",
    }

    try:
        app = build_chorus_graph()
        final_state = app.invoke(initial_state)
    except Exception as exc:
        classified_error = classify_exception(exc)
        _update_run_state(run_id, RunStatus.failed)
        log_event(
            logger,
            logging.ERROR,
            "run_failed",
            run_id=run_id,
            mode=mode,
            current_stage=initial_state["current_stage"],
            error_code=classified_error.code,
            error_message=str(classified_error),
        )
        raise classified_error from exc

    if final_state.get("pending_checkpoint"):
        _update_run_state(run_id, RunStatus.paused, final_state.get("current_stage"))
        status = "paused"
    else:
        _update_run_state(run_id, RunStatus.completed, "done")
        status = "completed"
    log_event(
        logger,
        logging.INFO,
        "run_finished",
        run_id=run_id,
        mode=mode,
        status=status,
        current_stage=final_state.get("current_stage"),
        pending_checkpoint=bool(final_state.get("pending_checkpoint")),
    )
    return _build_run_result(run_id, status, final_state)


def run_chorus_pipeline(raw_input: str, mode: str) -> RunExecutionResult:
    """Create a run, execute the Chorus graph, and return the resulting artifacts."""
    run_id = create_run_record(mode=mode, current_stage="intake")
    return execute_run(run_id=run_id, raw_input=raw_input, mode=mode)
