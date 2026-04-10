import os
from typing import Dict, List, Type

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "true")

import instructor
import litellm
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential


DEFAULT_MODELS = {
    "extraction": "anthropic/claude-sonnet-4-6",
    "synthesis": "anthropic/claude-sonnet-4-6",
    "critic": "anthropic/claude-sonnet-4-6",
}

DEFAULT_FALLBACKS = {
    "extraction": ["openai/gpt-4o-mini", "ollama/qwen2.5-coder:3b"],
    "synthesis": ["openai/gpt-4o", "ollama/qwen2.5-coder:3b"],
    "critic": ["openai/gpt-4o", "ollama/qwen2.5-coder:3b"],
}

DEFAULT_TEMPERATURES = {
    "extraction": 0.1,
    "synthesis": 0.5,
    "critic": 0.7,
    "default": 0.4,
}


def _parse_fallbacks(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    if raw.strip() == "":
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_model_config(profile: str) -> tuple[str, list[str], float]:
    """Returns the primary model, fallbacks, and temperature for a profile."""
    normalized_profile = profile if profile in DEFAULT_MODELS else "synthesis"
    upper_profile = normalized_profile.upper()

    model_name = os.getenv(
        f"CHORUS_MODEL_{upper_profile}",
        DEFAULT_MODELS[normalized_profile],
    )
    raw_fallbacks = _parse_fallbacks(
        os.getenv(f"CHORUS_MODEL_{upper_profile}_FALLBACKS")
    )
    fallbacks = (
        list(DEFAULT_FALLBACKS[normalized_profile])
        if raw_fallbacks is None
        else raw_fallbacks
    )
    temperature = DEFAULT_TEMPERATURES.get(
        normalized_profile,
        DEFAULT_TEMPERATURES["default"],
    )
    return model_name, fallbacks, temperature


def get_timeout_for_model(model_name: str) -> float:
    env_timeout = os.getenv("CHORUS_LLM_TIMEOUT_SECONDS")
    if env_timeout:
        try:
            return float(env_timeout)
        except ValueError:
            pass

    if model_name.startswith("ollama/"):
        return 180.0
    if model_name.startswith("anthropic/"):
        return 120.0
    return 45.0


def prepare_messages_for_model(
    model_name: str, messages: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    if not model_name.startswith("ollama/"):
        return messages

    json_only_instruction = (
        "Return only a concrete JSON object that matches the requested schema. "
        "Do not return a JSON Schema document. "
        "Do not include keys like 'properties', 'required', 'title', or 'type' unless the schema explicitly requires them. "
        "Do not wrap the answer in markdown fences."
    )

    prepared_messages = [message.copy() for message in messages]
    if prepared_messages and prepared_messages[0].get("role") == "system":
        prepared_messages[0]["content"] = (
            f"{prepared_messages[0]['content']}\n\n{json_only_instruction}"
        )
    else:
        prepared_messages.insert(0, {"role": "system", "content": json_only_instruction})

    return prepared_messages


def get_instructor_mode_for_model(model_name: str) -> instructor.Mode:
    if model_name.startswith("ollama/"):
        return instructor.Mode.JSON
    return instructor.Mode.TOOLS


def get_llm_client(model_name: str):
    """Returns an instructor-patched litellm client for seamless structured outputs."""
    return instructor.from_litellm(
        litellm.completion,
        mode=get_instructor_mode_for_model(model_name),
    )

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_structured_output(
    response_model: Type[BaseModel],
    messages: List[Dict[str, str]],
    profile: str = "synthesis"
) -> BaseModel:
    """
    Routes to the appropriate model based on task profile, with fallbacks and retries.
    """
    # 1. Environment-aware model routing & fallbacks
    model_name, fallbacks, temperature = get_model_config(profile)
    timeout = get_timeout_for_model(model_name)

    client = get_llm_client(model_name)
    prepared_messages = prepare_messages_for_model(model_name, messages)

    # 2. Resilient API Call
    response = client.chat.completions.create(
        model=model_name,
        fallbacks=fallbacks,
        response_model=response_model,
        messages=prepared_messages,
        temperature=temperature,
        timeout=timeout,
        max_retries=2 # LiteLLM level retries, in addition to tenacity
    )
    
    return response
