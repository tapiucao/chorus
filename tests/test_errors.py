from core.errors import (
    ChorusInternalError,
    ChorusProviderError,
    ChorusValidationError,
    classify_exception,
    error_payload,
)


def test_classify_exception_maps_value_error_to_validation_error():
    error = classify_exception(ValueError("missing input"))

    assert isinstance(error, ChorusValidationError)
    assert error.code == "validation_error"
    assert error.retryable is False


def test_classify_exception_maps_provider_like_runtime_error():
    error = classify_exception(RuntimeError("API timeout from provider"))

    assert isinstance(error, ChorusProviderError)
    assert error.code == "provider_error"
    assert error.retryable is True


def test_classify_exception_defaults_to_internal_error():
    error = classify_exception(RuntimeError("unexpected local failure"))

    assert isinstance(error, ChorusInternalError)
    assert error.code == "internal_error"
    assert error.retryable is False


def test_error_payload_uses_standard_shape():
    payload = error_payload(ChorusProviderError("upstream timeout"))

    assert payload == {
        "error": {
            "code": "provider_error",
            "message": "upstream timeout",
            "retryable": True,
        }
    }


def test_classify_exception_uses_module_name_for_provider_detection():
    ProviderLikeError = type("ProviderLikeError", (Exception,), {"__module__": "openai.transport"})

    error = classify_exception(ProviderLikeError("connection closed"))

    assert isinstance(error, ChorusProviderError)
