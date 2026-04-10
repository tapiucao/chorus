from __future__ import annotations

from typing import TypedDict

from core.skills import StageName, build_stage_system_prompt
from core.state import CritiqueReport, ExplorationDraft, OptionsBundle, ProjectSpec


class PromptPackage(TypedDict):
    stage: StageName
    system_prompt: str
    messages: list[dict[str, str]]
    profile: str


def build_intake_prompt(raw_input: str) -> PromptPackage:
    stage: StageName = "intake"
    system_prompt = build_stage_system_prompt(
        stage,
        "You classify product specs. Return maturity as 'raw', 'partial', or 'mature'.",
    )
    return {
        "stage": stage,
        "system_prompt": system_prompt,
        "profile": "extraction",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Classify this input:\n\n{raw_input}"},
        ],
    }


def build_exploration_prompt(raw_input: str) -> PromptPackage:
    stage: StageName = "exploration"
    system_prompt = build_stage_system_prompt(
        stage,
        "Extract the core problem, target users, and implicit constraints from this raw idea. Do not solve the problem yet.",
    )
    return {
        "stage": stage,
        "system_prompt": system_prompt,
        "profile": "synthesis",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Idea:\n{raw_input}"},
        ],
    }


def build_framing_prompt(raw_input: str, exploration_draft: ExplorationDraft | None) -> PromptPackage:
    stage: StageName = "framing"
    exploration_context = ""
    if exploration_draft:
        exploration_context = f"\n\nExploration Findings:\n{exploration_draft.model_dump_json()}"
    system_prompt = build_stage_system_prompt(
        stage,
        "Generate exactly 3 distinct options: simplest_viable, scalable, and minimal_cost.",
    )
    return {
        "stage": stage,
        "system_prompt": system_prompt,
        "profile": "synthesis",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Raw Context:\n{raw_input}{exploration_context}"},
        ],
    }


def build_critic_prompt(options_bundle: OptionsBundle | None) -> PromptPackage:
    stage: StageName = "critic"
    options_json = "\n".join([opt.model_dump_json() for opt in options_bundle.as_list()]) if options_bundle else ""
    system_prompt = build_stage_system_prompt(
        stage,
        "Critique the provided implementation options. Be ruthless about complexity, assumptions, and edge cases. Status must be 'proceed', 'pivot', or 'reject'.",
    )
    return {
        "stage": stage,
        "system_prompt": system_prompt,
        "profile": "critic",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Options to critique:\n{options_json}"},
        ],
    }


def build_mediator_prompt(
    raw_input: str,
    exploration_draft: ExplorationDraft | None,
    options_bundle: OptionsBundle | None,
    critique_reports: list[CritiqueReport],
) -> PromptPackage:
    stage: StageName = "mediator"
    options_json = "\n".join([opt.model_dump_json() for opt in options_bundle.as_list()]) if options_bundle else ""
    critiques_json = "\n".join([report.model_dump_json() for report in critique_reports])
    exploration_context = exploration_draft.model_dump_json() if exploration_draft else "{}"
    system_prompt = build_stage_system_prompt(
        stage,
        "Synthesize the final Project Spec. Choose the best approach based on the Architect's options and the Critic's reports. Enforce MVP boundaries.",
    )
    return {
        "stage": stage,
        "system_prompt": system_prompt,
        "profile": "synthesis",
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Original Idea: {raw_input}\n"
                    f"Exploration: {exploration_context}\n"
                    f"Options:\n{options_json}\n"
                    f"Critiques:\n{critiques_json}"
                ),
            },
        ],
    }


def build_implementation_prompt(raw_input: str, project_spec: ProjectSpec | None) -> PromptPackage:
    stage: StageName = "implementation_debate"
    project_spec_json = project_spec.model_dump_json() if project_spec else raw_input
    system_prompt = build_stage_system_prompt(
        stage,
        "Translate the approved ProjectSpec into an ImplementationSpec. Detail architecture, boundaries, and delivery sequence.",
    )
    return {
        "stage": stage,
        "system_prompt": system_prompt,
        "profile": "synthesis",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Project Spec:\n{project_spec_json}"},
        ],
    }
