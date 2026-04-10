from __future__ import annotations

from collections.abc import Iterable

from core.schemas import ImplementationSpec, ProjectSpec


def _format_list(items: Iterable[str]) -> str:
    lines = [f"- {item}" for item in items]
    return "\n".join(lines) if lines else "- None"


def render_project_spec_markdown(spec: ProjectSpec) -> str:
    """Render a ProjectSpec as a human-readable Markdown document."""
    return "\n".join(
        [
            f"# {spec.title}",
            "",
            "## Core Intent",
            spec.core_intent,
            "",
            "## Problem Statement",
            spec.problem_statement,
            "",
            "## Target Users",
            _format_list(spec.target_users),
            "",
            "## User Value",
            spec.user_value,
            "",
            "## Success Criteria",
            _format_list(spec.success_criteria),
            "",
            "## Assumptions",
            _format_list(spec.assumptions),
            "",
            "## Decisions",
            _format_list(spec.decisions),
            "",
            "## Constraints",
            _format_list(spec.constraints),
            "",
            "## Non-Negotiables",
            _format_list(spec.non_negotiables),
            "",
            "## Non-Goals",
            _format_list(spec.non_goals),
            "",
            "## Options Considered",
            _format_list(spec.options_considered),
            "",
            "## Chosen Approach",
            spec.chosen_approach,
            "",
            "## Functional Requirements",
            _format_list(spec.functional_requirements),
            "",
            "## Non-Functional Requirements",
            _format_list(spec.non_functional_requirements),
            "",
            "## Data Model Outline",
            _format_list(spec.data_model_outline),
            "",
            "## Interfaces",
            _format_list(spec.interfaces),
            "",
            "## In Scope",
            _format_list(spec.in_scope),
            "",
            "## Out of Scope",
            _format_list(spec.out_of_scope),
            "",
            "## Maybe Later",
            _format_list(spec.maybe_later),
            "",
            "## Risks",
            _format_list(spec.risks),
            "",
            "## Open Questions",
            _format_list(spec.open_questions),
            "",
            "## Acceptance Criteria",
            _format_list(spec.acceptance_criteria),
        ]
    )


def render_implementation_spec_markdown(spec: ImplementationSpec) -> str:
    """Render an ImplementationSpec as a human-readable Markdown document."""
    return "\n".join(
        [
            "# Implementation Spec",
            "",
            "## Implementation Goal",
            spec.implementation_goal,
            "",
            "## Architecture Summary",
            spec.architecture_summary,
            "",
            "## Strategies Considered",
            _format_list(spec.strategies_considered),
            "",
            "## Chosen Strategy",
            spec.chosen_strategy,
            "",
            "## Module Boundaries",
            _format_list(spec.module_boundaries),
            "",
            "## Integration Points",
            _format_list(spec.integration_points),
            "",
            "## Error Handling Strategy",
            spec.error_handling_strategy,
            "",
            "## Test Strategy",
            spec.test_strategy,
            "",
            "## Technical Debt Register",
            _format_list(spec.technical_debt_register),
            "",
            "## Delivery Sequence",
            _format_list(spec.delivery_sequence),
            "",
            "## Tie-Breaker Heuristics",
            _format_list(spec.tie_breaker_heuristics),
        ]
    )


def build_documents(
    project_spec: ProjectSpec | None,
    implementation_spec: ImplementationSpec | None,
) -> dict[str, str | None]:
    """Build Markdown documents for the available artifacts."""
    return {
        "project_spec_markdown": render_project_spec_markdown(project_spec) if project_spec else None,
        "implementation_spec_markdown": render_implementation_spec_markdown(implementation_spec)
        if implementation_spec
        else None,
    }
