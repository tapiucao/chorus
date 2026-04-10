from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ChorusSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHORUS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM — model names per profile
    model_extraction: str = "anthropic/claude-sonnet-4-6"
    model_synthesis: str = "anthropic/claude-sonnet-4-6"
    model_critic: str = "anthropic/claude-sonnet-4-6"

    # LLM — fallbacks per profile (comma-separated, empty string disables fallbacks)
    model_extraction_fallbacks: str = "openai/gpt-4o-mini,ollama/qwen2.5-coder:3b"
    model_synthesis_fallbacks: str = "openai/gpt-4o,ollama/qwen2.5-coder:3b"
    model_critic_fallbacks: str = "openai/gpt-4o,ollama/qwen2.5-coder:3b"

    # LLM — temperatures per profile
    llm_temperature_extraction: float = 0.1
    llm_temperature_synthesis: float = 0.5
    llm_temperature_critic: float = 0.7
    llm_temperature_default: float = 0.4

    # LLM — timeout override (None = auto-detect based on provider)
    llm_timeout_seconds: float | None = None

    # Database
    db_url: str = "sqlite:///chorus.db"
    checkpoint_db_path: str = "chorus_checkpoints.db"

    # Security — if None, authentication is disabled (safe for local dev)
    api_key: str | None = None

    # CORS — comma-separated list of allowed origins; empty = same-origin only
    cors_origins: str | None = None

    def get_model_config(self, profile: str) -> tuple[str, list[str], float]:
        """Return (primary_model, fallbacks, temperature) for the given profile."""
        normalized = profile if profile in ("extraction", "synthesis", "critic") else "synthesis"

        model_name = getattr(self, f"model_{normalized}")
        raw_fallbacks: str = getattr(self, f"model_{normalized}_fallbacks")
        fallbacks = [f.strip() for f in raw_fallbacks.split(",") if f.strip()] if raw_fallbacks.strip() else []
        temperature = getattr(self, f"llm_temperature_{normalized}", self.llm_temperature_default)

        return model_name, fallbacks, temperature

    def get_timeout_for_model(self, model_name: str) -> float:
        """Return timeout in seconds for the given model, respecting explicit override."""
        if self.llm_timeout_seconds is not None:
            return self.llm_timeout_seconds
        if model_name.startswith("ollama/"):
            return 180.0
        if model_name.startswith("anthropic/"):
            return 120.0
        return 45.0


settings = ChorusSettings()
