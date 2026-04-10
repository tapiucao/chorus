# General Code Hygiene Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen Chorus with clearer layer boundaries, structured logging, better error treatment, and test-backed cleanup across runner, web, DB, and orchestration paths.

**Architecture:** Keep `core` responsible for execution and domain lifecycle, `db` focused on persistence, `web` as a thin transport layer, and `graph`/`agents` focused on orchestration. Add a small shared observability/error layer that can be reused by CLI, runner, and API without changing the product architecture.

**Tech Stack:** Python, FastAPI, SQLModel, LangGraph, Pydantic, pytest, SQLite

---

### Task 1: Stabilize the test environment

**Files:**
- Create: `requirements-dev.txt`
- Modify: `README.md`
- Test: `tests/test_cli.py`
- Test: `tests/test_runner.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Add an explicit dependency manifest**

```text
fastapi
uvicorn
jinja2
sqlmodel
sqlalchemy
langgraph
litellm
instructor
tenacity
pytest
httpx
```

- [ ] **Step 2: Install the dependencies in the local virtualenv**

Run: `./venv/bin/pip install -r requirements-dev.txt`
Expected: install completes without `No matching distribution found`

- [ ] **Step 3: Run the current priority suite to establish baseline**

Run: `./venv/bin/pytest tests/test_cli.py tests/test_runner.py tests/test_web.py tests/test_graph.py tests/test_routing.py -q`
Expected: current failures identify missing behavior or dependency/setup issues, not import errors

- [ ] **Step 4: Document the local test bootstrap command**

```md
## Development

Install dev dependencies:

```bash
./venv/bin/pip install -r requirements-dev.txt
```

Run the core test suite:

```bash
./venv/bin/pytest tests/test_cli.py tests/test_runner.py tests/test_web.py tests/test_graph.py tests/test_routing.py -q
```
```

- [ ] **Step 5: Commit**

```bash
git add requirements-dev.txt README.md
git commit -m "chore: add explicit dev dependencies"
```

### Task 2: Add shared error and logging primitives

**Files:**
- Create: `core/errors.py`
- Create: `core/logging_utils.py`
- Modify: `core/models.py`
- Test: `tests/test_runner.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Write failing tests for failure classification and persisted error metadata**

```python
def test_execute_run_marks_failed_and_persists_error_details():
    ...

def test_web_error_payload_uses_standard_shape():
    ...
```

- [ ] **Step 2: Add explicit application error types**

```python
class ChorusError(Exception):
    def __init__(self, message: str, *, code: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ValidationError(ChorusError):
    ...


class ProviderError(ChorusError):
    ...


class InternalError(ChorusError):
    ...
```

- [ ] **Step 3: Add a tiny structured logger helper**

```python
def get_logger(name: str) -> logging.Logger:
    ...


def log_event(logger: logging.Logger, event: str, **context: object) -> None:
    ...
```

- [ ] **Step 4: Extend the run model with failure metadata if absent**

```python
error_code: str | None = Field(default=None)
error_message: str | None = Field(default=None)
```

- [ ] **Step 5: Run targeted tests**

Run: `./venv/bin/pytest tests/test_runner.py tests/test_web.py -q`
Expected: new tests fail only until runner and web integration are updated in later tasks

- [ ] **Step 6: Commit**

```bash
git add core/errors.py core/logging_utils.py core/models.py tests/test_runner.py tests/test_web.py
git commit -m "feat: add shared error and logging primitives"
```

### Task 3: Refactor runner lifecycle and observability

**Files:**
- Modify: `core/runner.py`
- Modify: `tests/test_runner.py`
- Test: `tests/test_runner.py`

- [ ] **Step 1: Add failing tests for status transitions and error classification**

```python
def test_execute_run_logs_start_and_completion(caplog):
    ...

def test_execute_run_maps_provider_errors_to_failed_run_state():
    ...
```

- [ ] **Step 2: Replace loose lifecycle helpers with explicit status transition helpers**

```python
def _update_run_state(...):
    ...


def _build_run_result(...):
    ...
```

- [ ] **Step 3: Instrument execution with structured logs**

```python
log_event(logger, "run_started", run_id=run_id, mode=mode, stage="intake")
...
log_event(logger, "run_completed", run_id=run_id, status=status, current_stage=current_stage)
...
log_event(logger, "run_failed", run_id=run_id, error_code=error.code)
```

- [ ] **Step 4: Persist error code and message on failure**

```python
except ChorusError as exc:
    _update_run_state(..., status=RunStatus.failed, error_code=exc.code, error_message=str(exc))
    raise
except Exception as exc:
    _update_run_state(..., status=RunStatus.failed, error_code="internal_error", error_message=str(exc))
    raise InternalError("Run execution failed", code="internal_error") from exc
```

- [ ] **Step 5: Run focused tests**

Run: `./venv/bin/pytest tests/test_runner.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add core/runner.py tests/test_runner.py
git commit -m "refactor: improve runner lifecycle and observability"
```

### Task 4: Thin the web layer and standardize API error treatment

**Files:**
- Modify: `web/app.py`
- Modify: `web/services.py`
- Modify: `tests/test_web.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Add failing tests for consistent HTTP error responses and create-run behavior**

```python
def test_get_run_404_uses_standard_error_detail():
    ...

def test_create_run_sync_path_uses_runner_without_dynamic_import_side_effects(monkeypatch):
    ...
```

- [ ] **Step 2: Remove unnecessary dynamic import and dependency syncing where practical**

```python
from core import runner

def create_run(...):
    ...
```

- [ ] **Step 3: Move payload assembly to service helpers and add exception handlers**

```python
@app.exception_handler(ChorusError)
async def chorus_error_handler(...):
    ...
```

- [ ] **Step 4: Keep endpoints transport-thin**

```python
@app.post("/api/runs")
def create_run_endpoint(...):
    return web_services.create_run_payload(...)
```

- [ ] **Step 5: Run focused tests**

Run: `./venv/bin/pytest tests/test_web.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/app.py web/services.py tests/test_web.py
git commit -m "refactor: simplify web layer and standardize API errors"
```

### Task 5: Clean persistence and orchestration edges

**Files:**
- Modify: `db/operations.py`
- Modify: `db/database.py`
- Modify: `graph.py`
- Modify: `agents/nodes.py`
- Modify: `tests/test_graph.py`
- Test: `tests/test_graph.py`

- [ ] **Step 1: Add failing tests for routing edge behavior if needed**

```python
def test_route_after_critic_handles_empty_reports_without_loopback():
    ...
```

- [ ] **Step 2: Normalize persistence helper style and signatures**

```python
def save_artifact(
    session: Session,
    run_id: int,
    artifact_type: ArtifactType,
    payload: BaseModel | dict[str, Any],
) -> Artifact:
    ...
```

- [ ] **Step 3: Replace `print`-based node tracing with logger-based events**

```python
log_event(logger, "node_started", run_id=state.get("run_id"), stage="critic")
```

- [ ] **Step 4: Tighten graph routing readability without semantic rewrite**

```python
def route_after_critic(state: ChorusState) -> str:
    reports = state.get("critique_reports", [])
    if not reports:
        return "mediator"
    ...
```

- [ ] **Step 5: Run focused tests**

Run: `./venv/bin/pytest tests/test_graph.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add db/operations.py db/database.py graph.py agents/nodes.py tests/test_graph.py
git commit -m "refactor: clean persistence and orchestration edges"
```

### Task 6: Strengthen CLI behavior and end-to-end priority tests

**Files:**
- Modify: `cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_routing.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_routing.py`

- [ ] **Step 1: Add failing tests for CLI error classification**

```python
def test_run_pipeline_returns_provider_exit_code_for_provider_error():
    ...

def test_run_pipeline_returns_validation_exit_code_for_validation_error():
    ...
```

- [ ] **Step 2: Replace string heuristics with error-type-based exit logic**

```python
except ProviderError:
    sys.exit(EXIT_PROVIDER_ERR)
except ValidationError:
    sys.exit(EXIT_VALIDATION_ERR)
```

- [ ] **Step 3: Preserve useful stderr output under `--verbose`**

```python
print_v("[VERBOSE] event=run_failed code=provider_error", args.verbose)
```

- [ ] **Step 4: Run the full priority suite**

Run: `./venv/bin/pytest tests/test_cli.py tests/test_runner.py tests/test_web.py tests/test_graph.py tests/test_routing.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cli.py tests/test_cli.py tests/test_routing.py
git commit -m "refactor: improve cli error handling and test coverage"
```

### Task 7: Final review and regression pass

**Files:**
- Modify: `README.md`
- Modify: `docs/handoff-2026-04-10.md`

- [ ] **Step 1: Run any remaining project tests**

Run: `./venv/bin/pytest -q`
Expected: PASS, or a short explicit list of any remaining failures outside the scope of this cleanup

- [ ] **Step 2: Review changed files for dead code and redundant comments**

```text
Check for:
- leftover dynamic imports
- `print` statements used as tracing
- stale MVP comments
- duplicated payload building
```

- [ ] **Step 3: Update handoff notes with observability and test bootstrap details**

```md
- Added structured logging primitives
- Standardized error classification
- Added explicit dev dependency manifest
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/handoff-2026-04-10.md
git commit -m "docs: record hygiene and observability updates"
```
