from langgraph.graph import StateGraph, END
from core.state import ChorusState
from agents.nodes import (
    intake_node, 
    exploration_node, 
    framing_node, 
    critic_node, 
    mediator_node, 
    implementation_debate_node
)

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
    
    if reports and all(r.recommendation_status == "reject" for r in reports):
        # Prevent infinite loops
        if state.get("loop_count", 0) >= 3:
            return "mediator" # Force synthesis with whatever we have
        return "exploration" # Loopback to rethink the problem
        
    return "mediator"

def route_after_mediator(state: ChorusState) -> str:
    """Decides if we stop at spec or continue to implementation debate."""
    if state["mode"] == "full":
        return "implementation_debate"
    return END

# -------------------------------------------------------------------
# Graph Compilation
# -------------------------------------------------------------------
def build_chorus_graph():
    workflow = StateGraph(ChorusState)
    
    # 1. Add Voices (Nodes)
    workflow.add_node("intake", intake_node)
    workflow.add_node("exploration", exploration_node)
    workflow.add_node("framing", framing_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("mediator", mediator_node)
    workflow.add_node("implementation_debate", implementation_debate_node)
    
    # 2. Define Flow
    workflow.set_entry_point("intake")
    
    # Intake branches out based on input maturity
    workflow.add_conditional_edges("intake", route_after_intake, {
        "exploration": "exploration",
        "implementation_debate": "implementation_debate"
    })
    
    workflow.add_edge("exploration", "framing")
    workflow.add_edge("framing", "critic")
    
    # Critic can force a loopback to exploration
    workflow.add_conditional_edges("critic", route_after_critic, {
        "exploration": "exploration",
        "mediator": "mediator"
    })
    
    # Mediator decides whether to stop or do full implementation debate
    workflow.add_conditional_edges("mediator", route_after_mediator, {
        "implementation_debate": "implementation_debate",
        END: END
    })
    
    workflow.add_edge("implementation_debate", END)
    
    return workflow.compile()
