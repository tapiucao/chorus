import logging
from unittest.mock import patch

import pytest
from langgraph.types import Interrupt

from core.errors import ChorusProviderError, ChorusValidationError
from core.graph_runtime import build_graph_config
from core.runner import execute_run, run_chorus_pipeline
from core.schemas import ImplementationSpec, ProjectSpec
from web.renderers import (
    build_documents,
    render_implementation_spec_markdown,
    render_project_spec_markdown,
)


def _mock_session(mock_session_cls):
    created_runs = []
    session_cm = mock_session_cls.return_value
    session = session_cm.__enter__.return_value

    def add(obj):
        created_runs.append(obj)

    def get(_model, _run_id):
        return created_runs[0] if created_runs else None

    session.add.side_effect = add
    session.commit.return_value = None
    session.refresh.side_effect = lambda obj: setattr(obj, "id", 7)
    session.get.side_effect = get
    return session


def test_run_chorus_pipeline_returns_completed_result():
    fake_state = {
        "project_spec": None,
        "implementation_spec": None,
        "pending_checkpoint": None,
        "current_stage": "done",
    }

    with (
        patch("core.runner.create_db_and_tables") as mock_create_db,
        patch("core.runner.build_chorus_graph") as mock_build,
        patch("core.runner.Session") as mock_session,
    ):
        session = _mock_session(mock_session)
        mock_build.return_value.invoke.return_value = fake_state

        result = run_chorus_pipeline(raw_input="Build a receipts app", mode="idea_spec")

    assert mock_create_db.call_count == 2
    mock_build.assert_called_once()
    mock_build.return_value.invoke.assert_called_once_with(
        {
            "run_id": 7,
            "mode": "idea_spec",
            "raw_input": "Build a receipts app",
            "loop_count": 0,
            "current_stage": "intake",
            "human_review_enabled": False,
        },
        config=build_graph_config(7),
    )
    session.get.assert_called()
    assert result["run_id"] == 7
    assert result["status"] == "completed"
    assert result["pending_checkpoint"] is None


def test_run_chorus_pipeline_marks_paused_runs():
    fake_state = {
        "project_spec": None,
        "implementation_spec": None,
        "current_stage": "mediator",
        "__interrupt__": [
            Interrupt(value={"message": "Review the generated project spec before continuing."}, id="abc123")
        ],
    }

    with (
        patch("core.runner.create_db_and_tables"),
        patch("core.runner.build_chorus_graph") as mock_build,
        patch("core.runner.Session") as mock_session,
    ):
        _mock_session(mock_session)
        mock_build.return_value.invoke.return_value = fake_state

        result = run_chorus_pipeline(raw_input="Build a receipts app", mode="full")

    assert result["run_id"] == 7
    assert result["status"] == "paused"
    assert result["pending_checkpoint"] == {
        "checkpoint_id": "abc123",
        "artifact_type": "project_spec",
        "current_stage": "human_review",
        "payload": {"message": "Review the generated project spec before continuing."},
    }
    assert result["current_stage"] == "human_review"


def test_run_chorus_pipeline_rejects_empty_input():
    with pytest.raises(ChorusValidationError, match="raw_input must not be empty"):
        run_chorus_pipeline(raw_input="   ", mode="idea_spec")


def test_execute_run_logs_start_and_completion(caplog):
    fake_state = {
        "project_spec": None,
        "implementation_spec": None,
        "pending_checkpoint": None,
        "current_stage": "done",
    }

    with (
        caplog.at_level(logging.INFO),
        patch("core.runner.create_db_and_tables"),
        patch("core.runner.build_chorus_graph") as mock_build,
        patch("core.runner.Session") as mock_session,
    ):
        _mock_session(mock_session)
        mock_build.return_value.invoke.return_value = fake_state

        result = execute_run(run_id=7, raw_input="Build a receipts app", mode="idea_spec")

    assert result["status"] == "completed"
    assert "event=run_started" in caplog.text
    assert "event=run_finished" in caplog.text


def test_execute_run_maps_provider_errors_to_failed_run_state(caplog):
    with (
        caplog.at_level(logging.ERROR),
        patch("core.runner.create_db_and_tables"),
        patch("core.runner.build_chorus_graph") as mock_build,
        patch("core.runner.Session") as mock_session,
    ):
        session = _mock_session(mock_session)
        mock_build.return_value.invoke.side_effect = RuntimeError("API timeout from provider")

        with pytest.raises(ChorusProviderError):
            execute_run(run_id=7, raw_input="Build a receipts app", mode="idea_spec")

    assert session.get.called
    assert "event=run_failed" in caplog.text


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


def test_render_project_spec_markdown_includes_key_sections():
    markdown = render_project_spec_markdown(_project_spec())

    assert "# Receipt AI" in markdown
    assert "## Problem Statement" in markdown
    assert "Users waste time on receipts" in markdown
    assert "- Upload receipt" in markdown


def test_render_implementation_spec_markdown_includes_key_sections():
    markdown = render_implementation_spec_markdown(_implementation_spec())

    assert "# Implementation Spec" in markdown
    assert "## Architecture Summary" in markdown
    assert "Single Python service with SQLite and a small web UI" in markdown
    assert "- Minimal monolith" in markdown


def test_build_documents_handles_optional_artifacts():
    docs = build_documents(_project_spec(), None)

    assert docs["project_spec_markdown"] is not None
    assert docs["implementation_spec_markdown"] is None
