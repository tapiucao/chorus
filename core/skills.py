from typing import Literal, TypedDict

StageName = Literal[
    "intake",
    "exploration",
    "framing",
    "critic",
    "mediator",
    "implementation_debate",
]


class StageSkillConfig(TypedDict):
    primary_skill: str
    auxiliary_skill: str | None
    responsibilities: tuple[str, ...]
    anti_patterns: tuple[str, ...]


STAGE_SKILLS: dict[StageName, StageSkillConfig] = {
    "intake": {
        "primary_skill": "requirement-extraction",
        "auxiliary_skill": "problem-framing",
        "responsibilities": (
            "Classify input maturity conservatively.",
            "Identify ambiguity instead of inventing certainty.",
            "Preserve the user's original wording and intent.",
        ),
        "anti_patterns": (
            "Do not rewrite the product idea into a solution proposal.",
            "Do not infer maturity from tone or confidence alone.",
        ),
    },
    "exploration": {
        "primary_skill": "problem-framing",
        "auxiliary_skill": "constraint-discovery",
        "responsibilities": (
            "Extract problem statement, users, constraints, and success criteria.",
            "Do not propose implementation or architecture yet.",
            "Surface missing information explicitly.",
        ),
        "anti_patterns": (
            "Do not converge on architecture early.",
            "Do not convert open questions into fake decisions.",
        ),
    },
    "framing": {
        "primary_skill": "option-framing",
        "auxiliary_skill": "tradeoff-analysis",
        "responsibilities": (
            "Generate exactly three distinct options.",
            "Cover simplest viable, scalable, and minimal-cost directions.",
            "Keep options comparable and aligned to the original vibe.",
        ),
        "anti_patterns": (
            "Do not produce three variants of the same option.",
            "Do not optimize one option so heavily that comparison becomes meaningless.",
        ),
    },
    "critic": {
        "primary_skill": "risk-review",
        "auxiliary_skill": "contradiction-audit",
        "responsibilities": (
            "Stress-test every option aggressively.",
            "Challenge assumptions, dependencies, and operational risks.",
            "Recommend proceed, pivot, or reject with concrete reasoning.",
        ),
        "anti_patterns": (
            "Do not soften valid risks to appear collaborative.",
            "Do not invent mitigations without tying them to a concrete failure mode.",
        ),
    },
    "mediator": {
        "primary_skill": "scope-control",
        "auxiliary_skill": "spec-writing",
        "responsibilities": (
            "Preserve intent while enforcing MVP boundaries.",
            "Reject overengineering and document deferred complexity.",
            "Produce a concrete ProjectSpec from the debate.",
        ),
        "anti_patterns": (
            "Do not re-expand scope for completeness or elegance.",
            "Do not add components that were not justified by the debate.",
        ),
    },
    "implementation_debate": {
        "primary_skill": "implementation-planning",
        "auxiliary_skill": "architecture-debate",
        "responsibilities": (
            "Translate the approved ProjectSpec into an ImplementationSpec.",
            "Define module boundaries, integration points, and sequencing.",
            "Prefer clear implementation trade-offs over abstract architecture prose.",
        ),
        "anti_patterns": (
            "Do not reopen settled product-scope decisions.",
            "Do not introduce implementation complexity that the ProjectSpec did not justify.",
        ),
    },
}


def build_stage_system_prompt(stage: StageName, base_prompt: str) -> str:
    """Attach an operational skill contract for a stage to the node's system prompt."""
    config = STAGE_SKILLS[stage]
    responsibilities = "\n".join(f"- {item}" for item in config["responsibilities"])
    anti_patterns = "\n".join(f"- {item}" for item in config["anti_patterns"])
    auxiliary = config["auxiliary_skill"] if config["auxiliary_skill"] is not None else "none"

    return (
        f"{base_prompt}\n\n"
        "Stage skill contract:\n"
        "- This contract defines task scope and guardrails, not tone or personality.\n"
        f"- Primary skill: {config['primary_skill']}\n"
        f"- Auxiliary skill: {auxiliary}\n"
        "Responsibilities:\n"
        f"{responsibilities}\n"
        "Anti-patterns:\n"
        f"{anti_patterns}"
    )


def get_stage_skill_snapshot(stage: StageName) -> dict[str, object]:
    """Return a JSON-serializable snapshot of the configured skill contract."""
    config = STAGE_SKILLS[stage]
    return {
        "stage": stage,
        "primary_skill": config["primary_skill"],
        "auxiliary_skill": config["auxiliary_skill"],
        "responsibilities": list(config["responsibilities"]),
        "anti_patterns": list(config["anti_patterns"]),
    }
