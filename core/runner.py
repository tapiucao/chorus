from __future__ import annotations

import logging
from typing import TypedDict, cast

from sqlmodel import Session

from core.errors import ChorusError, classify_exception
from core.graph_runtime import build_graph_config
from core.logging_utils import get_logger, log_event
from core.models import Run, RunStatus
from core.state import FinalChorusState, build_initial_chorus_state
from db.database import create_db_and_tables, engine
from graph import build_chorus_graph


class RunExecutionResult(TypedDict):
    run_id: int
    status: str
    project_spec: object | None
    implementation_spec: object | None
    pending_checkpoint: object | None
    current_stage: str | None


logger = get_logger(__name__)


def _extract_pending_checkpoint(result: object) -> object | None:
    if not isinstance(result, dict):
        return None

    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None

    first_interrupt = interrupts[0]
    return {
        "checkpoint_id": getattr(first_interrupt, "id", "pending"),
        "artifact_type": "project_spec",
        "current_stage": "human_review",
        "payload": getattr(first_interrupt, "value", None),
    }


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


def _build_run_result(run_id: int, status: str, final_state: FinalChorusState) -> RunExecutionResult:
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

    initial_state = build_initial_chorus_state(run_id=run_id, mode=mode, raw_input=raw_input)

    try:
        app = build_chorus_graph()
        raw_result = app.invoke(initial_state, config=build_graph_config(run_id))
        final_state = cast(FinalChorusState, raw_result)
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

    pending_checkpoint = _extract_pending_checkpoint(raw_result) or final_state.get("pending_checkpoint")

    if pending_checkpoint:
        _update_run_state(run_id, RunStatus.paused, "human_review")
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
        pending_checkpoint=bool(pending_checkpoint),
    )
    result = _build_run_result(run_id, status, final_state)
    result["pending_checkpoint"] = pending_checkpoint
    if pending_checkpoint:
        result["current_stage"] = "human_review"
    return result


def run_chorus_pipeline(raw_input: str, mode: str) -> RunExecutionResult:
    """Create a run, execute the Chorus graph, and return the resulting artifacts."""
    run_id = create_run_record(mode=mode, current_stage="intake")
    return execute_run(run_id=run_id, raw_input=raw_input, mode=mode)
