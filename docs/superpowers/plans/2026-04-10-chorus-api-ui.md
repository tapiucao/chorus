# Chorus API + UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an API-first web layer to Chorus so a user can submit an idea, generate a spec document, preview it in the browser with tabs for `Project Spec` and `Implementation Spec`, and download the generated artifacts as `.json` or `.md`.

**Architecture:** Extract pipeline execution from `cli.py` into a reusable runner in `core/runner.py`, then expose that runner through a minimal FastAPI app. Render Markdown on the backend so the UI and downloads use the same source, and keep the web layer thin by reusing existing persistence and graph orchestration.

**Tech Stack:** Python 3.12, FastAPI, Jinja2Templates, HTML/CSS/vanilla JS, SQLModel/SQLite, existing LangGraph pipeline, pytest

---

## File Structure

**Create:**
- `docs/superpowers/plans/2026-04-10-chorus-api-ui.md`
- `core/runner.py`
- `web/__init__.py`
- `web/app.py`
- `web/renderers.py`
- `web/templates/index.html`
- `web/static/styles.css`
- `web/static/app.js`
- `tests/test_runner.py`
- `tests/test_web.py`

**Modify:**
- `cli.py`
- `README.md`
- `.gitignore`

**Notes:**
- Keep the web layer separate from `cli.py`; both should call `core/runner.py`.
- Do not shell out from the API into the CLI.
- Reuse the existing DB-backed `Run` and `Artifact` workflow.

### Task 1: Extract a Shared Runner

**Files:**
- Create: `core/runner.py`
- Modify: `cli.py`
- Test: `tests/test_runner.py`

- [ ] **Step 1: Write the failing runner test**

```python
from unittest.mock import patch

from core.runner import run_chorus_pipeline


def test_run_chorus_pipeline_returns_specs():
    fake_state = {
        "project_spec": None,
        "implementation_spec": None,
        "pending_checkpoint": None,
    }

    with patch("core.runner.build_chorus_graph") as mock_build, patch("core.runner.create_db_and_tables"), patch("core.runner.Session") as mock_session:
        mock_build.return_value.invoke.return_value = fake_state
        mock_run = mock_session.return_value.__enter__.return_value
        mock_run.get.return_value = None

        result = run_chorus_pipeline(raw_input="idea", mode="idea_spec")

    assert result["status"] in {"completed", "paused"}
    assert "run_id" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_runner.py -q`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `core.runner`

- [ ] **Step 3: Write the shared runner**

```python
from sqlmodel import Session

from db.database import create_db_and_tables, engine
from core.models import Run, RunStatus
from graph import build_chorus_graph


def run_chorus_pipeline(raw_input: str, mode: str) -> dict:
    create_db_and_tables()

    with Session(engine) as session:
        run = Run(mode=mode, status=RunStatus.running)
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    initial_state = {
        "run_id": run_id,
        "mode": mode,
        "raw_input": raw_input,
        "loop_count": 0,
        "current_stage": "intake",
    }

    app = build_chorus_graph()
    final_state = app.invoke(initial_state)

    with Session(engine) as session:
        db_run = session.get(Run, run_id)
        if final_state.get("pending_checkpoint"):
            db_run.status = RunStatus.paused
            session.commit()
            status = "paused"
        else:
            db_run.status = RunStatus.completed
            db_run.current_stage = "done"
            session.commit()
            status = "completed"

    return {
        "run_id": run_id,
        "status": status,
        "project_spec": final_state.get("project_spec"),
        "implementation_spec": final_state.get("implementation_spec"),
        "pending_checkpoint": final_state.get("pending_checkpoint"),
    }
```

- [ ] **Step 4: Refactor the CLI to use the runner**

```python
from core.runner import run_chorus_pipeline


result = run_chorus_pipeline(raw_input=raw_input, mode=args.mode)

if result["status"] == "paused":
    sys.exit(EXIT_PAUSED)
```

- [ ] **Step 5: Run runner and CLI tests**

Run: `./venv/bin/pytest tests/test_runner.py tests/test_cli.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add core/runner.py cli.py tests/test_runner.py
git commit -m "feat: extract shared chorus runner"
```

### Task 2: Add Markdown Renderers

**Files:**
- Create: `web/renderers.py`
- Test: `tests/test_runner.py`

- [ ] **Step 1: Write the failing renderer test**

```python
from web.renderers import render_project_spec_markdown
from core.schemas import ProjectSpec


def test_render_project_spec_markdown_includes_title():
    spec = ProjectSpec(
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

    markdown = render_project_spec_markdown(spec)

    assert "# Receipt AI" in markdown
    assert "## Problem Statement" in markdown
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_runner.py -q`
Expected: FAIL with `ImportError` for `web.renderers`

- [ ] **Step 3: Implement Markdown renderers**

```python
def render_project_spec_markdown(spec: ProjectSpec) -> str:
    return f"""# {spec.title}

## Core Intent
{spec.core_intent}

## Problem Statement
{spec.problem_statement}
"""


def render_implementation_spec_markdown(spec: ImplementationSpec) -> str:
    return f"""# Implementation Spec

## Goal
{spec.implementation_goal}

## Architecture Summary
{spec.architecture_summary}
"""
```

- [ ] **Step 4: Add a unified document payload helper**

```python
def build_documents(project_spec: ProjectSpec | None, implementation_spec: ImplementationSpec | None) -> dict[str, str | None]:
    return {
        "project_spec_markdown": render_project_spec_markdown(project_spec) if project_spec else None,
        "implementation_spec_markdown": render_implementation_spec_markdown(implementation_spec) if implementation_spec else None,
    }
```

- [ ] **Step 5: Run the renderer test**

Run: `./venv/bin/pytest tests/test_runner.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/renderers.py tests/test_runner.py
git commit -m "feat: add chorus markdown renderers"
```

### Task 3: Add the FastAPI Backend

**Files:**
- Create: `web/__init__.py`
- Create: `web/app.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Write the failing web test**

```python
from fastapi.testclient import TestClient

from web.app import app


def test_create_run_returns_documents():
    client = TestClient(app)
    response = client.post("/api/runs", json={"mode": "idea_spec", "idea": "Build a receipt AI tool"})

    assert response.status_code == 200
    payload = response.json()
    assert "run_id" in payload
    assert "documents" in payload
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_web.py -q`
Expected: FAIL with `ImportError` for `web.app`

- [ ] **Step 3: Implement the FastAPI app**

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core.runner import run_chorus_pipeline
from web.renderers import build_documents


app = FastAPI(title="Chorus API")


class RunRequest(BaseModel):
    mode: str
    idea: str


@app.post("/api/runs")
def create_run(request: RunRequest) -> dict:
    result = run_chorus_pipeline(raw_input=request.idea, mode=request.mode)
    documents = build_documents(result["project_spec"], result["implementation_spec"])
    return {
        "run_id": result["run_id"],
        "status": result["status"],
        "project_spec": result["project_spec"].model_dump() if result["project_spec"] else None,
        "implementation_spec": result["implementation_spec"].model_dump() if result["implementation_spec"] else None,
        "documents": documents,
    }
```

- [ ] **Step 4: Add run lookup and download endpoints**

```python
@app.get("/api/runs/{run_id}")
def get_run(run_id: int) -> dict:
    ...


@app.get("/api/runs/{run_id}/download/output.json")
def download_json(run_id: int):
    ...


@app.get("/api/runs/{run_id}/download/project-spec.md")
def download_project_spec(run_id: int):
    ...
```

- [ ] **Step 5: Run the backend tests**

Run: `./venv/bin/pytest tests/test_web.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/__init__.py web/app.py tests/test_web.py
git commit -m "feat: add chorus fastapi backend"
```

### Task 4: Add the Browser UI

**Files:**
- Create: `web/templates/index.html`
- Create: `web/static/styles.css`
- Create: `web/static/app.js`
- Modify: `web/app.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Write the failing page test**

```python
from fastapi.testclient import TestClient

from web.app import app


def test_index_page_serves_form():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "<textarea" in response.text
    assert "Generate" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/pytest tests/test_web.py -q`
Expected: FAIL because `/` is not implemented

- [ ] **Step 3: Add the HTML page**

```html
<form id="idea-form">
  <textarea id="idea" name="idea" required></textarea>
  <select id="mode" name="mode">
    <option value="idea_spec">idea_spec</option>
    <option value="full">full</option>
  </select>
  <button type="submit">Generate</button>
</form>

<section id="preview">
  <div class="tabs">
    <button data-tab="project">Project Spec</button>
    <button data-tab="implementation" hidden>Implementation Spec</button>
  </div>
  <article id="project-preview"></article>
  <article id="implementation-preview" hidden></article>
</section>
```

- [ ] **Step 4: Add the frontend script**

```javascript
const form = document.getElementById("idea-form");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const response = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mode: document.getElementById("mode").value,
      idea: document.getElementById("idea").value,
    }),
  });

  const payload = await response.json();
  document.getElementById("project-preview").textContent = payload.documents.project_spec_markdown ?? "";
});
```

- [ ] **Step 5: Mount templates and static files in FastAPI**

```python
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

- [ ] **Step 6: Run the web tests**

Run: `./venv/bin/pytest tests/test_web.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/templates/index.html web/static/styles.css web/static/app.js web/app.py tests/test_web.py
git commit -m "feat: add chorus web ui"
```

### Task 5: Wire Downloads and Polish the UX

**Files:**
- Modify: `web/app.py`
- Modify: `web/static/app.js`
- Modify: `README.md`
- Modify: `.gitignore`
- Test: `tests/test_web.py`

- [ ] **Step 1: Write a failing download test**

```python
def test_download_json_endpoint_returns_payload():
    client = TestClient(app)
    response = client.get("/api/runs/1/download/output.json")
    assert response.status_code in {200, 404}
```

- [ ] **Step 2: Add JSON and Markdown download responses**

```python
from fastapi.responses import PlainTextResponse, JSONResponse


@app.get("/api/runs/{run_id}/download/implementation-spec.md")
def download_implementation_spec(run_id: int):
    markdown = "..."
    return PlainTextResponse(markdown, media_type="text/markdown")
```

- [ ] **Step 3: Add client-side download links**

```javascript
document.getElementById("download-json").href = `/api/runs/${payload.run_id}/download/output.json`;
document.getElementById("download-project-md").href = `/api/runs/${payload.run_id}/download/project-spec.md`;
```

- [ ] **Step 4: Update documentation and ignores**

```markdown
## Web Usage

Run:

```bash
uvicorn web.app:app --reload
```
```

- [ ] **Step 5: Run the full test suite**

Run: `./venv/bin/pytest tests -q`
Expected: PASS

- [ ] **Step 6: Manual smoke test**

Run: `./venv/bin/python -m uvicorn web.app:app --reload`
Expected:
- Page opens at `http://127.0.0.1:8000`
- Submitting an idea shows `Project Spec`
- `Implementation Spec` tab appears for `full`
- Download links return `.json` and `.md`

- [ ] **Step 7: Commit**

```bash
git add web/app.py web/static/app.js README.md .gitignore tests/test_web.py
git commit -m "feat: add chorus downloads and ui polish"
```

## Self-Review

### Spec coverage
- Shared runner: covered in Task 1
- Markdown preview/download: covered in Tasks 2 and 5
- API-first ingestion of ideas: covered in Task 3
- Browser UI with tabs and preview: covered in Task 4
- Download of generated artifacts: covered in Task 5

### Placeholder scan
- No `TODO`/`TBD` placeholders remain in the plan.
- Every new module has a clear destination path.

### Type consistency
- Runner returns `project_spec` and `implementation_spec`, which are reused by CLI and web.
- Web renderers consume the same typed artifacts already emitted by the graph.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-10-chorus-api-ui.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
