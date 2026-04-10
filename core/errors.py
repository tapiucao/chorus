from __future__ import annotations

from typing import Any


class ChorusError(Exception):
    """Base application exception with a stable error code."""

    def __init__(self, message: str, *, code: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ChorusValidationError(ChorusError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_error", retryable=False)


class ChorusProviderError(ChorusError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="provider_error", retryable=True)


class ChorusInternalError(ChorusError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="internal_error", retryable=False)


def classify_exception(exc: Exception) -> ChorusError:
    """Map arbitrary exceptions to a stable application-level error type."""
    if isinstance(exc, ChorusError):
        return exc

    if isinstance(exc, ValueError):
        return ChorusValidationError(str(exc))

    module_name = type(exc).__module__.lower()
    class_name = type(exc).__name__.lower()
    message = str(exc).lower()
    provider_markers = (
        "litellm",
        "openai",
        "anthropic",
        "instructor",
        "api",
        "timeout",
        "rate limit",
        "provider",
        "connection",
    )

    if any(marker in module_name or marker in class_name or marker in message for marker in provider_markers):
        return ChorusProviderError(str(exc))

    return ChorusInternalError(str(exc) or "Unexpected internal error")


def error_payload(exc: ChorusError) -> dict[str, Any]:
    return {
        "error": {
            "code": exc.code,
            "message": str(exc),
            "retryable": exc.retryable,
        }
    }
