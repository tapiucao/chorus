from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from core.config import settings


def get_checkpointer() -> SqliteSaver:
    """Return a SQLite-backed checkpointer so HITL state survives server restarts."""
    conn = sqlite3.connect(settings.checkpoint_db_path, check_same_thread=False)
    return SqliteSaver(conn)


def build_graph_config(run_id: int) -> dict[str, dict[str, str]]:
    """Return the LangGraph execution config for a persisted run."""
    return {"configurable": {"thread_id": f"run:{run_id}"}}
