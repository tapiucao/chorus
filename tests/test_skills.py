from core.skills import STAGE_SKILLS, build_stage_system_prompt


def test_all_stages_have_primary_skills():
    expected_stages = {
        "intake",
        "exploration",
        "framing",
        "critic",
        "mediator",
        "implementation_debate",
    }

    assert set(STAGE_SKILLS) == expected_stages
    assert all(config["primary_skill"] for config in STAGE_SKILLS.values())
    assert all(config["anti_patterns"] for config in STAGE_SKILLS.values())


def test_stage_prompt_includes_skill_contract():
    prompt = build_stage_system_prompt("critic", "Base critic prompt.")

    assert "Base critic prompt." in prompt
    assert "Primary skill: risk-review" in prompt
    assert "Auxiliary skill: contradiction-audit" in prompt
    assert "This contract defines task scope and guardrails, not tone or personality." in prompt
    assert "Responsibilities:" in prompt
    assert "Anti-patterns:" in prompt
