import instructor

from llm.routing import (
    get_instructor_mode_for_model,
    get_model_config,
    get_timeout_for_model,
    prepare_messages_for_model,
)


def test_get_model_config_includes_local_ollama_fallbacks_by_default(monkeypatch):
    monkeypatch.delenv("CHORUS_MODEL_EXTRACTION", raising=False)
    monkeypatch.delenv("CHORUS_MODEL_EXTRACTION_FALLBACKS", raising=False)

    model, fallbacks, temperature = get_model_config("extraction")

    assert model == "anthropic/claude-sonnet-4-6"
    assert "ollama/qwen2.5-coder:3b" in fallbacks
    assert temperature == 0.1


def test_get_model_config_respects_env_override_for_fallbacks(monkeypatch):
    monkeypatch.setenv(
        "CHORUS_MODEL_SYNTHESIS_FALLBACKS",
        "ollama/deepseek-coder:6.7b, openai/gpt-4o",
    )

    model, fallbacks, temperature = get_model_config("synthesis")

    assert model == "anthropic/claude-sonnet-4-6"
    assert fallbacks == ["ollama/deepseek-coder:6.7b", "openai/gpt-4o"]
    assert temperature == 0.5


def test_get_model_config_respects_empty_fallback_override(monkeypatch):
    monkeypatch.setenv("CHORUS_MODEL_CRITIC_FALLBACKS", "")

    _model, fallbacks, _temperature = get_model_config("critic")

    assert fallbacks == []


def test_get_timeout_for_model_prefers_longer_timeout_for_ollama():
    assert get_timeout_for_model("ollama/qwen2.5-coder:3b") == 180.0
    assert get_timeout_for_model("anthropic/claude-sonnet-4-6") == 120.0
    assert get_timeout_for_model("openai/gpt-4o-mini") == 45.0


def test_get_timeout_for_model_respects_env_override(monkeypatch):
    monkeypatch.setenv("CHORUS_LLM_TIMEOUT_SECONDS", "240")

    assert get_timeout_for_model("anthropic/claude-sonnet-4-6") == 240.0


def test_get_instructor_mode_for_model_uses_json_for_ollama():
    assert get_instructor_mode_for_model("ollama/qwen2.5-coder:3b") == instructor.Mode.JSON
    assert get_instructor_mode_for_model("openai/gpt-4o-mini") == instructor.Mode.TOOLS


def test_prepare_messages_for_model_adds_json_only_guardrail_for_ollama():
    messages = [{"role": "system", "content": "Return the result."}]

    prepared = prepare_messages_for_model("ollama/qwen2.5-coder:3b", messages)

    assert "Do not return a JSON Schema document" in prepared[0]["content"]


def test_prepare_messages_for_model_leaves_remote_messages_unchanged():
    messages = [{"role": "system", "content": "Return the result."}]

    prepared = prepare_messages_for_model("openai/gpt-4o-mini", messages)

    assert prepared == messages
