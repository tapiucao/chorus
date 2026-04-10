from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel
from sqlmodel import Session

from core.models import ArtifactType
from db.database import engine
from db.operations import save_artifact
from llm.routing import generate_structured_output

StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)
Message = dict[str, str]


class NodeRuntime(Protocol):
    def generate(
        self,
        response_model: type[StructuredOutputT],
        messages: list[Message],
        *,
        profile: str,
    ) -> StructuredOutputT:
        ...

    def persist_artifact(
        self,
        run_id: int,
        artifact_type: ArtifactType,
        payload: BaseModel | dict[str, object],
    ) -> None:
        ...


class DefaultNodeRuntime:
    """Production runtime for node inference and artifact persistence."""

    def generate(
        self,
        response_model: type[StructuredOutputT],
        messages: list[Message],
        *,
        profile: str,
    ) -> StructuredOutputT:
        return generate_structured_output(response_model, messages, profile=profile)

    def persist_artifact(
        self,
        run_id: int,
        artifact_type: ArtifactType,
        payload: BaseModel | dict[str, object],
    ) -> None:
        with Session(engine) as session:
            save_artifact(session, run_id, artifact_type, payload)
