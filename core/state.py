from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

from pydantic import BaseModel, Field

from core.schemas import CritiqueReport, ImplementationSpec, OptionDraft, ProjectSpec

PipelineMode = Literal["idea_spec", "spec_impl", "full"]
PipelineStage = Literal[
    "queued",
    "intake",
    "exploration",
    "framing",
    "critic",
    "mediator",
    "human_review",
    "implementation_debate",
    "done",
]
InputMaturity = Literal["raw", "partial", "mature"]


class MaturityClassification(BaseModel):
    maturity: InputMaturity = Field(..., description="Strict classification of input maturity.")
    summary: str


class ExplorationDraft(BaseModel):
    problem_statement: str
    target_users: list[str]
    constraints: list[str]
    success_criteria: list[str]


class OptionsBundle(BaseModel):
    simplest_viable: OptionDraft = Field(..., description="The absolute simplest viable approach.")
    scalable: OptionDraft = Field(..., description="A robust, scalable approach.")
    minimal_cost: OptionDraft = Field(..., description="An MVP approach optimizing for lowest immediate cost.")

    def as_list(self) -> list[OptionDraft]:
        return [self.simplest_viable, self.scalable, self.minimal_cost]


class CritiquesList(BaseModel):
    reports: list[CritiqueReport]


class CheckpointState(TypedDict, total=False):
    checkpoint_id: Required[str | int]
    status: Required[Literal["pending", "approved", "rejected", "steered"]]
    reason: Required[Literal["human_review_requested", "option_selection_required"]]
    artifact_type: Required[Literal["options_draft", "project_spec", "implementation_spec"]]
    expected_action: Required[Literal["approve_or_reject", "select_option", "steer"]]
    user_feedback: NotRequired[str | None]


class WorkflowControlState(TypedDict, total=False):
    """Execution control fields shared across the graph lifecycle."""

    run_id: Required[int]
    mode: Required[PipelineMode]
    raw_input: Required[str]
    loop_count: Required[int]
    current_stage: Required[PipelineStage]
    input_maturity: NotRequired[InputMaturity]
    pending_checkpoint: NotRequired[CheckpointState | None]
    human_review_enabled: NotRequired[bool]


class DebateState(TypedDict, total=False):
    """Intermediate artifacts produced while debating solution direction."""

    exploration_draft: NotRequired[ExplorationDraft]
    options_bundle: NotRequired[OptionsBundle]
    critique_reports: NotRequired[list[CritiqueReport]]
    human_feedback: NotRequired[str | dict[str, object] | None]


class DomainArtifactState(TypedDict, total=False):
    """Canonical deliverables produced by the graph."""

    project_spec: NotRequired[ProjectSpec]
    implementation_spec: NotRequired[ImplementationSpec]


class ChorusState(WorkflowControlState, DebateState, DomainArtifactState, total=False):
    """Typed LangGraph state split into control, debate, and domain artifacts."""


class InitialChorusState(WorkflowControlState):
    """Minimum valid state required to invoke the graph."""


class FinalChorusState(ChorusState):
    """Graph state shape at the end of execution."""


def build_initial_chorus_state(*, run_id: int, mode: PipelineMode, raw_input: str) -> InitialChorusState:
    return {
        "run_id": run_id,
        "mode": mode,
        "raw_input": raw_input,
        "loop_count": 0,
        "current_stage": "intake",
        "human_review_enabled": False,
    }
