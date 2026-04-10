from datetime import UTC, datetime
from enum import StrEnum

from sqlmodel import JSON, Column, DateTime, Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class RunStatus(StrEnum):
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"


class CheckpointStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    steered = "steered"


class ArtifactType(StrEnum):
    project_spec = "project_spec"
    implementation_spec = "implementation_spec"
    options_draft = "options_draft"
    prompt_contract = "prompt_contract"


class ExpectedAction(StrEnum):
    approve_or_reject = "approve_or_reject"
    select_option = "select_option"
    steer = "steer"


class Run(SQLModel, table=True):
    """A single execution pipeline run (idea_spec, spec_impl, or full)."""

    id: int | None = Field(default=None, primary_key=True)
    mode: str = Field(default="idea_spec")
    status: RunStatus = Field(default=RunStatus.running)
    current_stage: str = Field(default="intake")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    )


class Artifact(SQLModel, table=True):
    """Persisted versions of our Pydantic schemas tied to a Run."""

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    artifact_type: ArtifactType = Field(..., description="e.g., 'project_spec', 'implementation_spec'")
    schema_version: str = Field(default="1.0", description="Tracks schema mutations")
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=utc_now)


class Checkpoint(SQLModel, table=True):
    """Stores HITL pending actions and approvals."""

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id")
    stage: str
    status: CheckpointStatus = Field(default=CheckpointStatus.pending)
    reason: str = Field(default="human_review_requested")
    artifact_type: ArtifactType = Field(..., description="The artifact pending review")
    expected_action: ExpectedAction = Field(default=ExpectedAction.approve_or_reject)
    user_feedback: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = Field(default=None)
