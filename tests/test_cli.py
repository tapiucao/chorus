import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlmodel import Session

import cli
from core.errors import ChorusProviderError, ChorusValidationError
from core.models import Run, RunStatus
from db.database import create_db_and_tables, engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_inspect_skills_json_output():
    result = subprocess.run(
        [sys.executable, "cli.py", "--output", "json", "inspect-skills"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "intake" in payload
    assert payload["critic"]["primary_skill"] == "risk-review"


def test_inspect_run_json_includes_configured_skills():
    create_db_and_tables()
    with Session(engine) as session:
        run = Run(mode="idea_spec", status=RunStatus.completed)
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    result = subprocess.run(
        [sys.executable, "cli.py", "--output", "json", "inspect", "--run-id", str(run_id)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["id"] == run_id
    assert "configured_skills" in payload
    assert payload["configured_skills"]["mediator"]["primary_skill"] == "scope-control"


def test_run_pipeline_returns_provider_exit_code_for_provider_error(capsys):
    args = Namespace(mode="idea_spec", idea="Build a receipts app", input_file=None, output="pretty", verbose=False)

    with patch("cli.run_chorus_pipeline", side_effect=ChorusProviderError("provider timeout")), pytest.raises(SystemExit) as exc_info:
        cli.run_pipeline(args)

    assert exc_info.value.code == cli.EXIT_PROVIDER_ERR
    assert "Pipeline Failed: provider timeout" in capsys.readouterr().err


def test_run_pipeline_returns_validation_exit_code_for_validation_error(capsys):
    args = Namespace(mode="idea_spec", idea="Build a receipts app", input_file=None, output="pretty", verbose=False)

    with patch("cli.run_chorus_pipeline", side_effect=ChorusValidationError("bad input")), pytest.raises(SystemExit) as exc_info:
        cli.run_pipeline(args)

    assert exc_info.value.code == cli.EXIT_VALIDATION_ERR
    assert "Pipeline Failed: bad input" in capsys.readouterr().err
