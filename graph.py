from langgraph.graph import END, StateGraph

from agents.nodes import build_node_handlers
from core.graph_runtime import GRAPH_CHECKPOINTER
from core.node_runtime import DefaultNodeRuntime, NodeRuntime
from core.state import ChorusState

# -------------------------------------------------------------------
# Conditional Edge Routers
# -------------------------------------------------------------------
def route_after_intake(state: ChorusState) -> str:
    """Decides if we need to explore a raw idea or skip to implementation debate."""
    if state["mode"] == "spec_impl" or state["input_maturity"] == "mature":
        return "implementation_debate"
    return "exploration"


def route_after_critic(state: ChorusState) -> str:
    """
    Evaluates the Critic's report. 
    Triggers a loopback if ALL options were rejected and risk is too high.
    """
    reports = state.get("critique_reports", [])
    if not reports:
        return "mediator"

    if reports and all(r.recommendation_status == "reject" for r in reports):
        # Prevent infinite loops
        if state.get("loop_count", 0) >= 3:
            return "mediator"  # Force synthesis with whatever we have
        return "exploration"  # Loopback to rethink the problem

    return "mediator"


def route_after_mediator(state: ChorusState) -> str:
    """Decides if we stop at spec or continue to implementation debate."""
    if state.get("human_review_enabled"):
        return "human_review"
    if state["mode"] == "full":
        return "implementation_debate"
    return END


def route_after_human_review(state: ChorusState) -> str:
    """Continue from human review to implementation or finish at spec."""
    if state["mode"] == "full":
        return "implementation_debate"
    return END

# -------------------------------------------------------------------
# Graph Compilation
# -------------------------------------------------------------------
def build_chorus_graph(runtime: NodeRuntime | None = None):
    handlers = build_node_handlers(runtime or DefaultNodeRuntime())
    workflow = StateGraph(ChorusState)

    # 1. Add Voices (Nodes)
    workflow.add_node("intake", handlers.intake)
    workflow.add_node("exploration", handlers.exploration)
    workflow.add_node("framing", handlers.framing)
    workflow.add_node("critic", handlers.critic, destinations=("exploration", "mediator"))
    workflow.add_node("mediator", handlers.mediator)
    workflow.add_node("human_review", handlers.human_review)
    workflow.add_node("implementation_debate", handlers.implementation_debate)

    # 2. Define Flow
    workflow.set_entry_point("intake")

    # Intake branches out based on input maturity
    workflow.add_conditional_edges("intake", route_after_intake, {
        "exploration": "exploration",
        "implementation_debate": "implementation_debate",
    })

    workflow.add_edge("exploration", "framing")
    workflow.add_edge("framing", "critic")

    workflow.add_edge("critic", "mediator")

    # Mediator decides whether to stop or do full implementation debate
    workflow.add_conditional_edges("mediator", route_after_mediator, {
        "human_review": "human_review",
        "implementation_debate": "implementation_debate",
        END: END,
    })

    workflow.add_conditional_edges("human_review", route_after_human_review, {
        "implementation_debate": "implementation_debate",
        END: END,
    })

    workflow.add_edge("implementation_debate", END)

    return workflow.compile(checkpointer=GRAPH_CHECKPOINTER)
