from __future__ import annotations

from typing import Any

from langgraph.types import Command

from agents.nodes import (
    critic_node_with_runtime,
    exploration_node_with_runtime,
    framing_node_with_runtime,
    human_review_node,
    implementation_debate_node_with_runtime,
    intake_node_with_runtime,
    mediator_node_with_runtime,
)
from core.models import ArtifactType
from core.schemas import (
    CritiqueFinding,
    CritiqueReport,
    ImplementationSpec,
    OptionDraft,
    ProjectSpec,
)
from core.state import CritiquesList, ExplorationDraft, MaturityClassification, OptionsBundle


class FakeRuntime:
    def __init__(self, responses: dict[type[Any], Any]) -> None:
        self.responses = responses
        self.generate_calls: list[tuple[type[Any], str]] = []
        self.persist_calls: list[tuple[int, ArtifactType, object]] = []

    def generate(self, response_model: type[Any], messages: list[dict[str, str]], *, profile: str) -> Any:
        self.generate_calls.append((response_model, profile))
        return self.responses[response_model]

    def persist_artifact(self, run_id: int, artifact_type: ArtifactType, payload: object) -> None:
        self.persist_calls.append((run_id, artifact_type, payload))


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


def _implementation_spec() -> ImplementationSpec:
    return ImplementationSpec(
        implementation_goal="Turn approved spec into a working app",
        architecture_summary="Single Python service with SQLite and a small web UI",
        strategies_considered=["Minimal monolith", "API plus worker"],
        chosen_strategy="Minimal monolith",
        module_boundaries=["web", "core", "db"],
        integration_points=["FastAPI endpoint", "SQLite persistence"],
        error_handling_strategy="Fail fast on invalid inputs and provider errors",
        test_strategy="Unit tests for renderers and runner, API tests later",
        technical_debt_register=["Memory-backed resume is deferred"],
        delivery_sequence=["Runner", "API", "UI"],
        tie_breaker_heuristics=["Prefer the smallest change that keeps the flow intact"],
    )


def test_intake_node_uses_runtime_for_generation_and_prompt_contract():
    runtime = FakeRuntime({MaturityClassification: MaturityClassification(maturity="raw", summary="raw idea")})

    result = intake_node_with_runtime(
        {
            "run_id": 1,
            "raw_input": "Build a receipts app",
            "mode": "idea_spec",
            "loop_count": 0,
            "current_stage": "intake",
        },
        runtime,
    )

    assert result == {"current_stage": "intake", "input_maturity": "raw"}
    assert runtime.generate_calls == [(MaturityClassification, "extraction")]
    assert runtime.persist_calls[0][1] == ArtifactType.prompt_contract


def test_framing_and_critic_nodes_preserve_option_bundle_semantics():
    options_bundle = OptionsBundle(
        simplest_viable=_option("1", "simple"),
        scalable=_option("2", "scale"),
        minimal_cost=_option("3", "cheap"),
    )
    finding = CritiqueFinding(severity="high", challenged_assumption="A", description="A", mitigation="A")
    critiques = CritiquesList(
        reports=[
            CritiqueReport(
                option_id="1",
                findings=[finding],
                implementation_hazards=[],
                dependency_risks=[],
                ambiguity_risks=[],
                recommendation_status="reject",
            )
        ]
    )
    framing_runtime = FakeRuntime({OptionsBundle: options_bundle})
    critic_runtime = FakeRuntime({CritiquesList: critiques})

    framing_result = framing_node_with_runtime(
        {
            "run_id": 1,
            "raw_input": "Build a receipts app",
            "mode": "idea_spec",
            "loop_count": 0,
            "current_stage": "framing",
            "exploration_draft": ExplorationDraft(
                problem_statement="Receipt entry is slow",
                target_users=["freelancers"],
                constraints=["low cost"],
                success_criteria=["csv export"],
            ),
        },
        framing_runtime,
    )
    critic_result = critic_node_with_runtime(
        {
            "run_id": 1,
            "raw_input": "Build a receipts app",
            "mode": "idea_spec",
            "loop_count": 0,
            "current_stage": "critic",
            "options_bundle": options_bundle,
        },
        critic_runtime,
    )

    assert isinstance(critic_result, Command)
    assert critic_result.goto == "exploration"
    assert critic_result.update["current_stage"] == "critic"
    assert critic_result.update["critique_reports"] == critiques.reports
    assert critic_result.update["loop_count"] == 1
    assert framing_result["options_bundle"] == options_bundle


def test_mediator_and_implementation_nodes_persist_via_runtime():
    project_spec = _project_spec()
    implementation_spec = _implementation_spec()
    mediator_runtime = FakeRuntime({ProjectSpec: project_spec})
    implementation_runtime = FakeRuntime({ImplementationSpec: implementation_spec})
    options_bundle = OptionsBundle(
        simplest_viable=_option("1", "simple"),
        scalable=_option("2", "scale"),
        minimal_cost=_option("3", "cheap"),
    )

    mediator_result = mediator_node_with_runtime(
        {
            "run_id": 7,
            "raw_input": "Build a receipts app",
            "mode": "idea_spec",
            "loop_count": 0,
            "current_stage": "mediator",
            "options_bundle": options_bundle,
            "critique_reports": [],
            "exploration_draft": ExplorationDraft(
                problem_statement="Receipt entry is slow",
                target_users=["freelancers"],
                constraints=["low cost"],
                success_criteria=["csv export"],
            ),
        },
        mediator_runtime,
    )
    implementation_result = implementation_debate_node_with_runtime(
        {
            "run_id": 7,
            "raw_input": "Build a receipts app",
            "mode": "full",
            "loop_count": 0,
            "current_stage": "implementation_debate",
            "project_spec": project_spec,
        },
        implementation_runtime,
    )

    assert mediator_result["project_spec"] == project_spec
    assert implementation_result["implementation_spec"] == implementation_spec
    assert mediator_runtime.persist_calls[-1][1] == ArtifactType.project_spec
    assert implementation_runtime.persist_calls[-1][1] == ArtifactType.implementation_spec


def test_exploration_node_returns_typed_draft():
    draft = ExplorationDraft(
        problem_statement="Receipt entry is slow",
        target_users=["freelancers"],
        constraints=["low cost"],
        success_criteria=["csv export"],
    )
    runtime = FakeRuntime({ExplorationDraft: draft})

    result = exploration_node_with_runtime(
        {
            "run_id": 1,
            "raw_input": "Build a receipts app",
            "mode": "idea_spec",
            "loop_count": 0,
            "current_stage": "exploration",
        },
        runtime,
    )

    assert result["exploration_draft"] == draft


def test_human_review_node_returns_feedback_when_interrupt_resumes(monkeypatch):
    monkeypatch.setattr("agents.nodes.interrupt", lambda payload: {"decision": "approve", "notes": "looks good"})

    result = human_review_node(
        {
            "run_id": 1,
            "mode": "idea_spec",
            "raw_input": "Build a receipts app",
            "loop_count": 0,
            "current_stage": "human_review",
            "project_spec": _project_spec(),
        }
    )

    assert result == {
        "current_stage": "human_review",
        "human_feedback": {"decision": "approve", "notes": "looks good"},
    }
