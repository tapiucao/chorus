from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from core.models import Artifact, ArtifactType, Run
from core.schemas import ImplementationSpec, ProjectSpec
from db import database as db
from web.renderers import build_documents, render_implementation_spec_markdown, render_project_spec_markdown


def ensure_db() -> None:
    db.create_db_and_tables()


def artifact_payload_to_model(artifact: Artifact) -> ProjectSpec | ImplementationSpec | dict:
    if artifact.artifact_type == ArtifactType.project_spec:
        return ProjectSpec.model_validate(artifact.payload)
    if artifact.artifact_type == ArtifactType.implementation_spec:
        return ImplementationSpec.model_validate(artifact.payload)
    return artifact.payload


def get_run_or_404(run_id: int) -> Run:
    ensure_db()
    with Session(db.engine) as session:
        run = session.get(Run, run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return run


def get_artifacts_for_run(run_id: int) -> list[Artifact]:
    ensure_db()
    with Session(db.engine) as session:
        return session.exec(select(Artifact).where(Artifact.run_id == run_id)).all()


def extract_specs(artifacts: list[Artifact]) -> tuple[ProjectSpec | None, ImplementationSpec | None]:
    project_spec = next(
        (ProjectSpec.model_validate(artifact.payload) for artifact in artifacts if artifact.artifact_type == ArtifactType.project_spec),
        None,
    )
    implementation_spec = next(
        (
            ImplementationSpec.model_validate(artifact.payload)
            for artifact in artifacts
            if artifact.artifact_type == ArtifactType.implementation_spec
        ),
        None,
    )
    return project_spec, implementation_spec


def build_run_payload(run: Run, artifacts: list[Artifact], configured_skills: dict[str, object]) -> dict:
    project_spec, implementation_spec = extract_specs(artifacts)
    documents = build_documents(project_spec, implementation_spec)

    serialized_artifacts = []
    for artifact in artifacts:
        payload = artifact_payload_to_model(artifact)
        serialized_artifacts.append(
            {
                "id": artifact.id,
                "type": artifact.artifact_type.value if hasattr(artifact.artifact_type, "value") else artifact.artifact_type,
                "version": artifact.schema_version,
                "payload": payload.model_dump() if hasattr(payload, "model_dump") else payload,
            }
        )

    return {
        "run_id": run.id,
        "id": run.id,
        "mode": run.mode,
        "status": run.status.value if hasattr(run.status, "value") else run.status,
        "current_stage": run.current_stage,
        "configured_skills": configured_skills,
        "artifacts": serialized_artifacts,
        "documents": documents,
    }


def build_pending_run_payload(run_id: int, mode: str, current_stage: str = "queued") -> dict:
    return {
        "run_id": run_id,
        "status": "running",
        "mode": mode,
        "current_stage": current_stage,
        "project_spec": None,
        "implementation_spec": None,
        "documents": {
            "project_spec_markdown": None,
            "implementation_spec_markdown": None,
        },
    }


def render_project_markdown_for_run(run_id: int) -> str:
    artifacts = get_artifacts_for_run(run_id)
    project_spec, _ = extract_specs(artifacts)
    if not project_spec:
        raise HTTPException(status_code=404, detail=f"ProjectSpec not found for run {run_id}")
    return render_project_spec_markdown(project_spec)


def render_implementation_markdown_for_run(run_id: int) -> str:
    artifacts = get_artifacts_for_run(run_id)
    _, implementation_spec = extract_specs(artifacts)
    if not implementation_spec:
        raise HTTPException(status_code=404, detail=f"ImplementationSpec not found for run {run_id}")
    return render_implementation_spec_markdown(implementation_spec)
