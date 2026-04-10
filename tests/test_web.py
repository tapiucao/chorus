import json
import sys
import types

import pytest
from fastapi import HTTPException
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

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

    fake_runner = types.ModuleType("core.runner")
    fake_runner.run_chorus_pipeline = lambda raw_input, mode: fake_result
    monkeypatch.setitem(sys.modules, "core.runner", fake_runner)

    payload = create_run(RunRequest(mode="idea_spec", idea="Build a receipts app"))

    assert payload["run_id"] == 42
    assert payload["status"] == "completed"
    assert payload["documents"]["project_spec_markdown"].startswith("# Receipt AI")
    assert payload["documents"]["implementation_spec_markdown"] is None
    assert payload["mode"] == "idea_spec"


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
