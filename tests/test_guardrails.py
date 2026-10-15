import pytest

from devops_ai.guardrails import (
    GuardrailError,
    validate_incident,
)


def test_valid_incident_is_accepted():
    incident = validate_incident(
        description="Checkout requests are returning HTTP 500 errors.",
        log_sample="ERROR checkout-service request failed status=500",
        environment="staging",
    )

    assert incident.environment == "staging"
    assert "HTTP 500" in incident.description
    assert "ERROR" in incident.log_sample


def test_empty_description_is_rejected():
    with pytest.raises(GuardrailError):
        validate_incident(
            description="   ",
            log_sample="ERROR checkout-service failed",
        )


def test_empty_logs_are_rejected():
    with pytest.raises(GuardrailError):
        validate_incident(
            description="Checkout requests are failing.",
            log_sample=" ",
        )


def test_oversized_description_is_rejected():
    with pytest.raises(GuardrailError):
        validate_incident(
            description="A" * 5_001,
            log_sample="ERROR service failed",
        )


def test_common_api_key_is_redacted():
    incident = validate_incident(
        description="The service failed with a credential error.",
        log_sample="api_key=abcdef1234567890 service failed",
    )

    assert "abcdef1234567890" not in incident.log_sample
    assert "[REDACTED_SECRET]" in incident.log_sample


def test_invalid_environment_is_rejected():
    with pytest.raises(GuardrailError):
        validate_incident(
            description="Checkout requests are failing.",
            log_sample="ERROR checkout failed",
            environment="my-laptop",
        )