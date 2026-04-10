import pytest
from pydantic import ValidationError

from agents.nodes import MaturityClassification, OptionsList
from core.schemas import OptionDraft
from core.state import ChorusState, ExplorationDraft, build_initial_chorus_state


def test_maturity_classification_strict_literal():
    # Valid
    valid = MaturityClassification(maturity="raw", summary="test")
    assert valid.maturity == "raw"

    # Invalid
    with pytest.raises(ValidationError):
        MaturityClassification(maturity="semi-mature", summary="test")


def test_options_list_enforces_three_categories():
    draft = OptionDraft(
        id="1",
        title="A",
        summary="A",
        benefits=["A"],
        trade_offs=["A"],
        complexity="low",
        operational_risk="low",
        implementation_effort="low",
        alignment_with_vibe="Good",
    )

    # Missing scalable and minimal_cost
    with pytest.raises(ValidationError):
        OptionsList(simplest_viable=draft)

    # Valid
    valid = OptionsList(simplest_viable=draft, scalable=draft, minimal_cost=draft)
    assert valid.simplest_viable.id == "1"


def test_options_list_preserves_named_roles_and_list_order():
    simplest = OptionDraft(
        id="1",
        title="Simple",
        summary="A",
        benefits=["A"],
        trade_offs=["A"],
        complexity="low",
        operational_risk="low",
        implementation_effort="low",
        alignment_with_vibe="Good",
    )
    scalable = OptionDraft(
        id="2",
        title="Scale",
        summary="B",
        benefits=["B"],
        trade_offs=["B"],
        complexity="medium",
        operational_risk="medium",
        implementation_effort="medium",
        alignment_with_vibe="Good",
    )
    low_cost = OptionDraft(
        id="3",
        title="Cheap",
        summary="C",
        benefits=["C"],
        trade_offs=["C"],
        complexity="low",
        operational_risk="low",
        implementation_effort="low",
        alignment_with_vibe="Good",
    )

    bundle = OptionsList(simplest_viable=simplest, scalable=scalable, minimal_cost=low_cost)

    assert [option.id for option in bundle.as_list()] == ["1", "2", "3"]


def test_chorus_state_accepts_partial_stage_specific_fields():
    state = ChorusState(
        mode="idea_spec",
        raw_input="Build a receipts app",
        loop_count=0,
        current_stage="exploration",
        run_id=1,
        exploration_draft=ExplorationDraft(
            problem_statement="Receipt entry is slow",
            target_users=["freelancers"],
            constraints=["low cost"],
            success_criteria=["csv export"],
        ),
    )

    assert state["current_stage"] == "exploration"
    assert state["exploration_draft"].problem_statement == "Receipt entry is slow"


def test_build_initial_chorus_state_returns_minimum_graph_input():
    state = build_initial_chorus_state(run_id=7, mode="idea_spec", raw_input="Build a receipts app")

    assert state == {
        "run_id": 7,
        "mode": "idea_spec",
        "raw_input": "Build a receipts app",
        "loop_count": 0,
        "current_stage": "intake",
        "human_review_enabled": False,
    }
