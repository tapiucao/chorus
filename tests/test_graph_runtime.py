from core.graph_runtime import build_graph_config


def test_build_graph_config_uses_stable_thread_id():
    assert build_graph_config(42) == {"configurable": {"thread_id": "run:42"}}
