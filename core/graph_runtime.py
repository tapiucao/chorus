from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver


GRAPH_CHECKPOINTER = InMemorySaver()


def build_graph_config(run_id: int) -> dict[str, dict[str, str]]:
    """Return the LangGraph execution config for a persisted run."""
    return {"configurable": {"thread_id": f"run:{run_id}"}}
