import argparse
import json
import os
import sys
from pathlib import Path

# Ensure local imports work regardless of execution directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.models import Artifact, Run, RunStatus
from core.skills import STAGE_SKILLS
from core.runner import run_chorus_pipeline
from db.database import create_db_and_tables, engine
from sqlmodel import Session, select

# Exit Codes
EXIT_SUCCESS = 0
EXIT_VALIDATION_ERR = 1
EXIT_PROVIDER_ERR = 2
EXIT_PAUSED = 3

def print_v(msg, verbose=False):
    if verbose:
        print(msg, file=sys.stderr)

def _status_value(value):
    return value.value if hasattr(value, "value") else value


def _read_raw_input(args) -> str:
    if args.input_file:
        try:
            with open(args.input_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as exc:
            print(f"Error reading file {args.input_file}: {exc}", file=sys.stderr)
            sys.exit(EXIT_VALIDATION_ERR)

    if not args.idea:
        print("Error: Must provide either 'idea' positional argument or --input-file", file=sys.stderr)
        sys.exit(EXIT_VALIDATION_ERR)

    return args.idea


def _print_pretty_run_start(mode: str, raw_input: str) -> None:
    print("[*] Starting Chorus Pipeline")
    print(f"[*] Mode: {mode}")
    print(f"[*] Input Length: {len(raw_input)} characters\n")


def _build_run_output(result: dict) -> dict:
    return {
        "run_id": result["run_id"],
        "project_spec": result["project_spec"].model_dump() if result["project_spec"] else None,
        "implementation_spec": result["implementation_spec"].model_dump() if result["implementation_spec"] else None,
    }


def _print_pretty_run_result(result: dict) -> None:
    run_id = result["run_id"]
    print(f"[*] Run ID: {run_id}")
    if result["status"] == "paused":
        print(f"\n[!] Pipeline Paused (HITL) - Run ID: {run_id}")
        return

    print("\n[*] Pipeline Completed Successfully!")

    if result["project_spec"]:
        print("\n=== PROJECT SPEC ===")
        print(result["project_spec"].model_dump_json(indent=2))

    if result["implementation_spec"]:
        print("\n=== IMPLEMENTATION SPEC ===")
        print(result["implementation_spec"].model_dump_json(indent=2))


def _serialize_artifacts(artifacts: list[Artifact]) -> list[dict]:
    return [
        {
            "type": _status_value(artifact.artifact_type),
            "version": artifact.schema_version,
            "payload": artifact.payload,
        }
        for artifact in artifacts
    ]


def _print_artifact_preview(artifact: Artifact) -> None:
    print(f"- Type: {artifact.artifact_type} (Schema: v{artifact.schema_version})")
    print(f"- Created: {artifact.created_at}")
    payload_str = json.dumps(artifact.payload, indent=2)
    if len(payload_str) > 500:
        print(payload_str[:500] + "\n  ...\n}")
    else:
        print(payload_str)
    print()


def run_pipeline(args):
    raw_input = _read_raw_input(args)

    if args.output == "pretty":
        _print_pretty_run_start(args.mode, raw_input)

    try:
        result = run_chorus_pipeline(raw_input=raw_input, mode=args.mode)
        print_v("[VERBOSE] Pipeline executed via shared runner.", args.verbose)

        if args.output == "pretty":
            _print_pretty_run_result(result)
        else:
            print(json.dumps(_build_run_output(result), indent=2))

        if result["status"] == "paused":
            sys.exit(EXIT_PAUSED)

        sys.exit(EXIT_SUCCESS)
            
    except Exception as e:
        err_msg = str(e)
        print_v(f"[VERBOSE] Exception trace: {err_msg}", args.verbose)
        if args.output == "pretty":
            print(f"\n[!] Pipeline Failed: {err_msg}", file=sys.stderr)

        # Simple heuristic to differentiate LLM errors from validation errors
        if "litellm" in err_msg.lower() or "timeout" in err_msg.lower() or "api" in err_msg.lower():
            sys.exit(EXIT_PROVIDER_ERR)
        else:
            sys.exit(EXIT_VALIDATION_ERR)

def inspect_run(args):
    create_db_and_tables()
    
    with Session(engine) as session:
        run = session.get(Run, args.run_id)
        if not run:
            print(f"Error: Run {args.run_id} not found.", file=sys.stderr)
            sys.exit(EXIT_VALIDATION_ERR)
            
        if args.output == "json":
            artifacts = session.exec(select(Artifact).where(Artifact.run_id == run.id)).all()
            out = {
                "id": run.id,
                "mode": run.mode,
                "status": _status_value(run.status),
                "configured_skills": STAGE_SKILLS,
                "artifacts": _serialize_artifacts(artifacts),
            }
            print(json.dumps(out, indent=2))
            sys.exit(EXIT_SUCCESS)
            
        print(f"Run ID: {run.id}")
        print(f"Mode: {run.mode}")
        print(f"Status: {_status_value(run.status)}")
        print(f"Created: {run.created_at}")
        print("\nConfigured Skills:")
        for stage, config in STAGE_SKILLS.items():
            print(f"- {stage}: {config['primary_skill']} (aux: {config['auxiliary_skill'] or 'none'})")
        
        artifacts = session.exec(select(Artifact).where(Artifact.run_id == run.id)).all()
        print(f"\nArtifacts ({len(artifacts)}):")
        for artifact in artifacts:
            _print_artifact_preview(artifact)
            
def resume_run(args):
    print("Error: Graph state checkpointing for HITL resume is not fully wired yet.", file=sys.stderr)
    print("This will require migrating LangGraph MemorySaver to SQLite in the next sprint.", file=sys.stderr)
    sys.exit(EXIT_VALIDATION_ERR)


def inspect_skills(args):
    if args.output == "json":
        print(json.dumps(STAGE_SKILLS, indent=2))
        sys.exit(EXIT_SUCCESS)

    print("Chorus Stage Skills")
    print()
    for stage, config in STAGE_SKILLS.items():
        print(f"{stage}:")
        print(f"  primary: {config['primary_skill']}")
        print(f"  auxiliary: {config['auxiliary_skill'] or 'none'}")
        print("  responsibilities:")
        for responsibility in config["responsibilities"]:
            print(f"    - {responsibility}")
        print()

    sys.exit(EXIT_SUCCESS)

def main():
    parser = argparse.ArgumentParser(description="Chorus - Idea Maturation Engine CLI")
    # Global args
    parser.add_argument("--output", choices=["json", "pretty"], default="pretty", help="Output format")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging to stderr")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Run command
    run_parser = subparsers.add_parser("run", help="Start a new Chorus pipeline run")
    run_parser.add_argument("--mode", choices=["idea_spec", "spec_impl", "full"], default="idea_spec", help="Pipeline mode")
    run_parser.add_argument("--input-file", type=str, help="Path to input text file")
    run_parser.add_argument("idea", type=str, nargs="?", help="Raw idea text")
    run_parser.set_defaults(func=run_pipeline)

    # Inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a specific run and its artifacts")
    inspect_parser.add_argument("--run-id", type=int, required=True, help="Run ID to inspect")
    inspect_parser.set_defaults(func=inspect_run)
    
    # Resume command
    resume_parser = subparsers.add_parser("resume", help="Resume a paused HITL run")
    resume_parser.add_argument("--run-id", type=int, required=True, help="Run ID to resume")
    resume_parser.set_defaults(func=resume_run)

    # Inspect skills command
    skills_parser = subparsers.add_parser("inspect-skills", help="Show the skill map used by each stage")
    skills_parser.set_defaults(func=inspect_skills)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
