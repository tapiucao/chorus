from core.models import Artifact, ArtifactType, Run, RunStatus
from core.schemas import ProjectSpec
from web.services import (
    artifact_payload_to_model,
    build_pending_run_payload,
    build_run_payload,
    build_sync_run_payload,
    extract_specs,
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


def test_artifact_payload_to_model_round_trips_project_spec():
    spec = _project_spec()
    artifact = Artifact(artifact_type=ArtifactType.project_spec, payload=spec.model_dump(), run_id=1)

    model = artifact_payload_to_model(artifact)

    assert isinstance(model, ProjectSpec)
    assert model.title == "Receipt AI"


def test_build_sync_run_payload_serializes_models_and_documents():
    spec = _project_spec()
    payload = build_sync_run_payload(
        {
            "run_id": 7,
            "status": "completed",
            "project_spec": spec,
            "implementation_spec": None,
            "current_stage": "done",
        },
        mode="idea_spec",
    )

    assert payload["run_id"] == 7
    assert payload["project_spec"]["title"] == "Receipt AI"
    assert payload["documents"]["project_spec_markdown"].startswith("# Receipt AI")


def test_build_run_payload_serializes_artifacts_and_enum_values():
    spec = _project_spec()
    run = Run(id=9, mode="idea_spec", status=RunStatus.completed, current_stage="done")
    artifacts = [
        Artifact(
            id=11,
            run_id=9,
            artifact_type=ArtifactType.project_spec,
            schema_version="1.0",
            payload=spec.model_dump(),
        )
    ]

    payload = build_run_payload(run, artifacts, configured_skills={"mediator": {"primary_skill": "scope-control"}})

    assert payload["id"] == 9
    assert payload["status"] == "completed"
    assert payload["artifacts"][0]["type"] == "project_spec"
    assert payload["artifacts"][0]["payload"]["title"] == "Receipt AI"


def test_build_pending_run_payload_has_stable_shape():
    payload = build_pending_run_payload(run_id=5, mode="full")

    assert payload == {
        "run_id": 5,
        "status": "running",
        "mode": "full",
        "current_stage": "queued",
        "project_spec": None,
        "implementation_spec": None,
        "documents": {
            "project_spec_markdown": None,
            "implementation_spec_markdown": None,
        },
    }


def test_extract_specs_returns_missing_implementation_as_none():
    spec = _project_spec()
    artifacts = [
        Artifact(
            id=11,
            run_id=9,
            artifact_type=ArtifactType.project_spec,
            schema_version="1.0",
            payload=spec.model_dump(),
        )
    ]

    project_spec, implementation_spec = extract_specs(artifacts)

    assert project_spec is not None
    assert implementation_spec is None
