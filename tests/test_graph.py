from core.schemas import CritiqueFinding, CritiqueReport
from core.state import ChorusState
from graph import (
    route_after_critic,
    route_after_human_review,
    route_after_intake,
    route_after_mediator,
)


def test_route_after_intake():
    # If mature, go to implementation
    state = ChorusState(mode="idea_spec", input_maturity="mature")
    assert route_after_intake(state) == "implementation_debate"

    # If mode is spec_impl, skip to implementation regardless of maturity
    state = ChorusState(mode="spec_impl", input_maturity="raw")
    assert route_after_intake(state) == "implementation_debate"

    # Otherwise explore
    state = ChorusState(mode="idea_spec", input_maturity="raw")
    assert route_after_intake(state) == "exploration"


def test_route_after_critic_loopback():
    finding = CritiqueFinding(severity="high", challenged_assumption="A", description="A", mitigation="A")

    # All reject -> loopback to exploration
    report_reject = CritiqueReport(
        option_id="1",
        findings=[finding],
        implementation_hazards=[],
        dependency_risks=[],
        ambiguity_risks=[],
        recommendation_status="reject",
    )
    state = ChorusState(critique_reports=[report_reject, report_reject], loop_count=0)
    assert route_after_critic(state) == "exploration"

    # Prevent infinite loop (max 3)
    state["loop_count"] = 3
    assert route_after_critic(state) == "mediator"

    # Mixed results -> proceed to mediator
    report_proceed = CritiqueReport(
        option_id="2",
        findings=[finding],
        implementation_hazards=[],
        dependency_risks=[],
        ambiguity_risks=[],
        recommendation_status="proceed",
    )
    state = ChorusState(critique_reports=[report_reject, report_proceed], loop_count=0)
    assert route_after_critic(state) == "mediator"


def test_route_after_critic_with_no_reports_proceeds_to_mediator():
    state = ChorusState(critique_reports=[], loop_count=0)
    assert route_after_critic(state) == "mediator"


def test_route_after_mediator_human_review_takes_precedence():
    state = ChorusState(mode="full", human_review_enabled=True)
    assert route_after_mediator(state) == "human_review"


def test_route_after_human_review_matches_mode():
    assert route_after_human_review(ChorusState(mode="full")) == "implementation_debate"
