from typing import Any

from sqlmodel import Session

from core.models import Run, RunStatus
from db.database import create_db_and_tables, engine
from graph import build_chorus_graph


def _update_run(run_id: int, status: RunStatus, current_stage: str | None = None) -> None:
    """Persist the latest run status to SQLite."""
    with Session(engine) as session:
        db_run = session.get(Run, run_id)
        if not db_run:
            return

        db_run.status = status
        if current_stage is not None:
            db_run.current_stage = current_stage
        session.commit()


def create_run_record(mode: str, current_stage: str = "intake") -> int:
    """Create a persisted run record and return its identifier."""
    create_db_and_tables()

    with Session(engine) as session:
        run = Run(mode=mode, status=RunStatus.running, current_stage=current_stage)
        session.add(run)
        session.commit()
        session.refresh(run)
        return run.id


def execute_run(run_id: int, raw_input: str, mode: str) -> dict[str, Any]:
    """Execute the Chorus graph for an existing run identifier."""
    if not raw_input or not raw_input.strip():
        raise ValueError("raw_input must not be empty")

    create_db_and_tables()
    _update_run(run_id, RunStatus.running, "intake")

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
    except Exception:
        _update_run(run_id, RunStatus.failed)
        raise

    if final_state.get("pending_checkpoint"):
        _update_run(run_id, RunStatus.paused, final_state.get("current_stage"))
        status = "paused"
    else:
        _update_run(run_id, RunStatus.completed, "done")
        status = "completed"

    return {
        "run_id": run_id,
        "status": status,
        "project_spec": final_state.get("project_spec"),
        "implementation_spec": final_state.get("implementation_spec"),
        "pending_checkpoint": final_state.get("pending_checkpoint"),
        "current_stage": final_state.get("current_stage"),
    }


def run_chorus_pipeline(raw_input: str, mode: str) -> dict[str, Any]:
    """Create a run, execute the Chorus graph, and return the resulting artifacts."""
    run_id = create_run_record(mode=mode, current_stage="intake")
    return execute_run(run_id=run_id, raw_input=raw_input, mode=mode)
