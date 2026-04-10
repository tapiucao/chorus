# Chorus

> **"When perspectives align, specs emerge"**

**Chorus** (formerly Vibe-to-Spec / Idea Maturation Engine) transforms raw product ideas into concrete, reviewable technical specs through a multi-agent orchestration pipeline. 

## Metaphor: Multiple voices in harmony
Each agent is a voice:
- **Explorer**: Extracts intent, identifies ambiguity.
- **Architect**: Produces plausible technical/product directions.
- **Critic**: Stress-tests options.
- **Mediator (Scope Guardian/Spec Writer)**: Synthesizes conflict into harmony (the final spec).

Individually they represent conflicting perspectives; in chorus, they converge into an executable melody (spec).

## Architecture Principles
1. **Typed Artifacts**: Conversation is not the source of truth; Pydantic/SQLModel artifacts are.
2. **Minimal State**: LangGraph state only holds canonical objects, stage statuses, and decisions.
3. **Task-based LLM Routing**: Fast models for extraction, reasoning models for critique/synthesis (LiteLLM adapter).
4. **Day 0 Persistence**: SQLite handles runs, versions, and human-in-the-loop checkpoints.

## CLI Usage

Run the existing CLI:

```bash
cd /home/tarun/.openclaw/workspace/projects/chorus
./venv/bin/python cli.py run --mode idea_spec "A tool that organizes receipts and exports CSV"
```

Inspect a persisted run:

```bash
./venv/bin/python cli.py inspect --run-id 1
./venv/bin/python cli.py --output json inspect --run-id 1
```

Inspect stage skills:

```bash
./venv/bin/python cli.py inspect-skills
```

## API Usage

Start the API server:

```bash
cd /home/tarun/.openclaw/workspace/projects/chorus
./venv/bin/python -m uvicorn web.app:app --reload
```

Create a run via HTTP:

```bash
curl -X POST http://127.0.0.1:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"mode":"idea_spec","idea":"A tool that organizes receipts and exports CSV"}'
```

Inspect a run via HTTP:

```bash
curl http://127.0.0.1:8000/api/runs/1
```

Download generated artifacts:

```bash
curl -OJ http://127.0.0.1:8000/api/runs/1/download/output.json
curl -OJ http://127.0.0.1:8000/api/runs/1/download/project-spec.md
curl -OJ http://127.0.0.1:8000/api/runs/1/download/implementation-spec.md
```

## Web UI

With the API server running, open:

```text
http://127.0.0.1:8000/
```

The UI supports:
- submitting a raw idea
- choosing `idea_spec` or `full`
- previewing `Project Spec` and `Implementation Spec` in tabs
- downloading `.json` and `.md` outputs

## Development

Install the local dev dependencies:

```bash
./venv/bin/pip install -r requirements-dev.txt
```

Run the full test suite:

```bash
./venv/bin/pytest -q
```

For a step-by-step local run and troubleshooting flow, see:

```text
docs/local-testing.md
```

Notes:
- `llm/routing.py` forces `LITELLM_LOCAL_MODEL_COST_MAP=true` by default so local and CI test runs do not block on LiteLLM network fetches in restricted environments.
- The current suite covers runner, CLI, routing, DB, graph, schema, skill, and web contracts.
