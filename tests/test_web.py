import asyncio
import json

import pytest
from fastapi import BackgroundTasks
from fastapi import HTTPException
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from core.errors import ChorusValidationError
from core.models import Artifact, ArtifactType, Run, RunStatus
from core.schemas import ProjectSpec
import web.app as web_app
from web.app import RunRequest, create_run, download_implementation_spec_markdown, download_output_json, download_project_spec_markdown, get_run, index


def test_index_endpoint_returns_html():
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    response = index(request)
    body = response.body.decode("utf-8")

    assert "<form id=\"idea-form\"" in body
    assert "Project Spec" in body
    assert "Implementation Spec" in body
    assert "Download JSON" in body


def test_create_run_returns_documents(monkeypatch: pytest.MonkeyPatch):
    fake_project_spec = ProjectSpec(
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

    fake_result = {
        "run_id": 42,
        "status": "completed",
        "project_spec": fake_project_spec,
        "implementation_spec": None,
        "pending_checkpoint": None,
        "current_stage": "done",
    }

    monkeypatch.setattr(web_app.runner, "run_chorus_pipeline", lambda raw_input, mode: fake_result)

    payload = create_run(RunRequest(mode="idea_spec", idea="Build a receipts app"))

    assert payload["run_id"] == 42
    assert payload["status"] == "completed"
    assert payload["documents"]["project_spec_markdown"].startswith("# Receipt AI")
    assert payload["documents"]["implementation_spec_markdown"] is None
    assert payload["mode"] == "idea_spec"


def test_create_run_with_background_tasks_returns_pending_payload(monkeypatch: pytest.MonkeyPatch):
    background_tasks = BackgroundTasks()
    captured_calls: list[tuple[object, tuple[object, ...], dict[str, object]]] = []

    monkeypatch.setattr(web_app.runner, "create_run_record", lambda mode, current_stage="queued": 99)
    monkeypatch.setattr(
        background_tasks,
        "add_task",
        lambda func, *args, **kwargs: captured_calls.append((func, args, kwargs)),
    )

    payload = create_run(
        RunRequest(mode="idea_spec", idea="Build a receipts app"),
        background_tasks=background_tasks,
    )

    assert payload == {
        "run_id": 99,
        "status": "running",
        "mode": "idea_spec",
        "current_stage": "queued",
        "project_spec": None,
        "implementation_spec": None,
        "documents": {
            "project_spec_markdown": None,
            "implementation_spec_markdown": None,
        },
    }
    assert len(captured_calls) == 1
    assert captured_calls[0][0] is web_app.runner.execute_run
    assert captured_calls[0][1] == (99, "Build a receipts app", "idea_spec")


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _seed_run_and_artifacts(engine):
    with Session(engine) as session:
        run = Run(mode="full", status=RunStatus.completed, current_stage="done")
        session.add(run)
        session.commit()
        session.refresh(run)

        artifact = Artifact(
            run_id=run.id,
            artifact_type=ArtifactType.project_spec,
            schema_version="1.0",
            payload={
                "title": "Receipt AI",
                "core_intent": "Automate receipt handling",
                "problem_statement": "Users waste time on receipts",
                "target_users": ["freelancers"],
                "user_value": "Faster bookkeeping",
                "success_criteria": ["Exports CSV"],
                "assumptions": ["User uploads images"],
                "decisions": ["MVP is web-only"],
                "constraints": ["Low cost"],
                "non_negotiables": ["Preserve simplicity"],
                "non_goals": ["Mobile app"],
                "options_considered": ["Scalable option rejected due to cost"],
                "chosen_approach": "Low-cost MVP",
                "functional_requirements": ["Upload receipt"],
                "non_functional_requirements": ["Cheap to run"],
                "data_model_outline": ["Receipt(id, amount)"],
                "interfaces": ["POST /receipts"],
                "in_scope": ["Upload"],
                "out_of_scope": ["OCR training"],
                "maybe_later": ["Accounting integrations"],
                "risks": ["OCR quality"],
                "open_questions": ["Accepted file types"],
                "acceptance_criteria": ["User can download CSV"],
            },
        )
        session.add(artifact)
        session.commit()
        return run.id


def test_run_lookup_and_download_endpoints(monkeypatch: pytest.MonkeyPatch, test_engine):
    run_id = _seed_run_and_artifacts(test_engine)

    monkeypatch.setattr(web_app, "engine", test_engine)
    monkeypatch.setattr(web_app, "create_db_and_tables", lambda: SQLModel.metadata.create_all(test_engine))

    payload = get_run(run_id)
    assert payload["id"] == run_id
    assert payload["documents"]["project_spec_markdown"].startswith("# Receipt AI")
    assert payload["configured_skills"]["mediator"]["primary_skill"] == "scope-control"

    json_response = download_output_json(run_id)
    assert json.loads(json_response.body.decode("utf-8"))["id"] == run_id

    md_response = download_project_spec_markdown(run_id)
    assert md_response.body.decode("utf-8").startswith("# Receipt AI")

    with pytest.raises(HTTPException):
        download_implementation_spec_markdown(run_id)


def test_create_run_endpoint_returns_standard_error_payload():
    request = Request({"type": "http", "method": "GET", "path": "/boom", "headers": []})
    response = asyncio.run(web_app.handle_chorus_error(request, ChorusValidationError("bad input")))

    assert response.status_code == 400
    assert json.loads(response.body.decode("utf-8")) == {
        "error": {
            "code": "validation_error",
            "message": "bad input",
            "retryable": False,
        }
    }


def test_handle_chorus_error_maps_provider_to_502():
    request = Request({"type": "http", "method": "GET", "path": "/boom", "headers": []})
    response = asyncio.run(web_app.handle_chorus_error(request, web_app.ChorusError("upstream failed", code="provider_error", retryable=True)))

    assert response.status_code == 502


def test_handle_chorus_error_maps_internal_to_500():
    request = Request({"type": "http", "method": "GET", "path": "/boom", "headers": []})
    response = asyncio.run(web_app.handle_chorus_error(request, web_app.ChorusError("unexpected failure", code="internal_error")))

    assert response.status_code == 500

