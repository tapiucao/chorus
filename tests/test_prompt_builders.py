from core.prompt_builders import (
    build_critic_prompt,
    build_exploration_prompt,
    build_framing_prompt,
    build_implementation_prompt,
    build_intake_prompt,
    build_mediator_prompt,
)
from core.schemas import CritiqueFinding, CritiqueReport, OptionDraft, ProjectSpec
from core.state import ExplorationDraft, OptionsBundle


def _option(option_id: str, title: str) -> OptionDraft:
    return OptionDraft(
        id=option_id,
        title=title,
        summary=title,
        benefits=[title],
        trade_offs=[title],
        complexity="low",
        operational_risk="low",
        implementation_effort="low",
        alignment_with_vibe="Good",
    )


def _project_spec() -> ProjectSpec:
    return ProjectSpec(
        title="Receipt AI",
        core_intent="Automate receipt handling",
        problem_statement="Users waste time on receipts",
        target_users=["freelancers"],
        user_value="Faster bookkeeping",
        success_criteria=["Exports CSV"],
        assumptions=["User uploads images"],
        decisions=["MVP is web-only"],
        constraints=["Low cost"],
        non_negotiables=["Preserve simplicity"],
        non_goals=["Mobile app"],
        options_considered=["Scalable option rejected due to cost"],
        chosen_approach="Low-cost MVP",
        functional_requirements=["Upload receipt"],
        non_functional_requirements=["Cheap to run"],
        data_model_outline=["Receipt(id, amount)"],
        interfaces=["POST /receipts"],
        in_scope=["Upload"],
        out_of_scope=["OCR training"],
        maybe_later=["Accounting integrations"],
        risks=["OCR quality"],
        open_questions=["Accepted file types"],
        acceptance_criteria=["User can download CSV"],
    )


def test_build_intake_prompt_has_expected_stage_and_profile():
    prompt = build_intake_prompt("Build a receipts app")

    assert prompt["stage"] == "intake"
    assert prompt["profile"] == "extraction"
    assert "Classify this input" in prompt["messages"][1]["content"]


def test_build_framing_prompt_includes_exploration_json():
    prompt = build_framing_prompt(
        "Build a receipts app",
        ExplorationDraft(
            problem_statement="Receipt entry is slow",
            target_users=["freelancers"],
            constraints=["low cost"],
            success_criteria=["csv export"],
        ),
    )

    assert prompt["stage"] == "framing"
    assert "Exploration Findings" in prompt["messages"][1]["content"]
    assert '"problem_statement":"Receipt entry is slow"' in prompt["messages"][1]["content"]


def test_build_critic_prompt_preserves_ordered_option_semantics():
    prompt = build_critic_prompt(
        OptionsBundle(
            simplest_viable=_option("1", "simple"),
            scalable=_option("2", "scale"),
            minimal_cost=_option("3", "cheap"),
        )
    )

    content = prompt["messages"][1]["content"]
    assert content.index('"id":"1"') < content.index('"id":"2"') < content.index('"id":"3"')


def test_build_mediator_prompt_includes_critiques_and_options():
    finding = CritiqueFinding(severity="high", challenged_assumption="A", description="A", mitigation="A")
    critiques = [
        CritiqueReport(
            option_id="1",
            findings=[finding],
            implementation_hazards=[],
            dependency_risks=[],
            ambiguity_risks=[],
            recommendation_status="reject",
        )
    ]
    prompt = build_mediator_prompt(
        "Build a receipts app",
        ExplorationDraft(
            problem_statement="Receipt entry is slow",
            target_users=["freelancers"],
            constraints=["low cost"],
            success_criteria=["csv export"],
        ),
        OptionsBundle(
            simplest_viable=_option("1", "simple"),
            scalable=_option("2", "scale"),
            minimal_cost=_option("3", "cheap"),
        ),
        critiques,
    )

    content = prompt["messages"][1]["content"]
    assert "Original Idea: Build a receipts app" in content
    assert "Critiques:" in content
    assert '"recommendation_status":"reject"' in content


def test_build_implementation_prompt_falls_back_to_raw_input_without_project_spec():
    prompt = build_implementation_prompt("Build a receipts app", None)

    assert prompt["stage"] == "implementation_debate"
    assert "Build a receipts app" in prompt["messages"][1]["content"]


def test_build_exploration_prompt_uses_synthesis_profile():
    prompt = build_exploration_prompt("Build a receipts app")

    assert prompt["profile"] == "synthesis"
    assert prompt["stage"] == "exploration"


def test_build_implementation_prompt_uses_serialized_project_spec_when_present():
    prompt = build_implementation_prompt("Build a receipts app", _project_spec())

    assert '"title":"Receipt AI"' in prompt["messages"][1]["content"]
