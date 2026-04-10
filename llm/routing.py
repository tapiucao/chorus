import os

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "true")

import instructor
import litellm
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import ChorusSettings


# Module-level wrappers kept for backward compatibility and test isolation.
# They create a fresh ChorusSettings() so monkeypatch.setenv works in tests.
def get_model_config(profile: str) -> tuple[str, list[str], float]:
    """Return (primary_model, fallbacks, temperature) for the given profile."""
    return ChorusSettings().get_model_config(profile)


def get_timeout_for_model(model_name: str) -> float:
    """Return timeout in seconds, respecting CHORUS_LLM_TIMEOUT_SECONDS override."""
    return ChorusSettings().get_timeout_for_model(model_name)


def prepare_messages_for_model(model_name: str, messages: list[dict[str, str]]) -> list[dict[str, str]]:
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
        prepared_messages[0]["content"] = f"{prepared_messages[0]['content']}\n\n{json_only_instruction}"
    else:
        prepared_messages.insert(0, {"role": "system", "content": json_only_instruction})

    return prepared_messages


def get_instructor_mode_for_model(model_name: str) -> instructor.Mode:
    if model_name.startswith("ollama/"):
        return instructor.Mode.JSON
    return instructor.Mode.TOOLS


def get_llm_client(model_name: str) -> instructor.Instructor:
    """Returns an instructor-patched litellm client for seamless structured outputs."""
    return instructor.from_litellm(
        litellm.completion,
        mode=get_instructor_mode_for_model(model_name),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_structured_output(
    response_model: type[BaseModel],
    messages: list[dict[str, str]],
    profile: str = "synthesis",
) -> BaseModel:
    """Routes to the appropriate model based on task profile, with fallbacks and retries."""
    model_name, fallbacks, temperature = get_model_config(profile)
    timeout = get_timeout_for_model(model_name)

    client = get_llm_client(model_name)
    prepared_messages = prepare_messages_for_model(model_name, messages)

    response = client.chat.completions.create(
        model=model_name,
        fallbacks=fallbacks,
        response_model=response_model,
        messages=prepared_messages,  # type: ignore[arg-type]
        temperature=temperature,
        timeout=timeout,
        max_retries=2,  # LiteLLM level retries, in addition to tenacity
    )

    return response
