from typing import Any

from pydantic import BaseModel
from sqlmodel import Session

from core.models import Artifact, ArtifactType


def save_artifact(
    session: Session,
    run_id: int,
    artifact_type: ArtifactType,
    payload: BaseModel | dict[str, Any],
) -> Artifact:
    """Persists a typed Pydantic artifact or dict payload to the database."""
    serialized_payload = payload.model_dump() if isinstance(payload, BaseModel) else payload
    artifact = Artifact(
        run_id=run_id,
        artifact_type=artifact_type,
        payload=serialized_payload,
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return artifact
