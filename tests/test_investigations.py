import pytest

from devops_ai.guardrails import GuardrailError
from devops_ai.services.investigations import investigate_incident
from devops_ai.schemas import IncidentReport


def test_investigation_returns_a_structured_report():
    report = investigate_incident(
        description="Checkout requests are returning HTTP 500 errors.",
        log_sample=(
            "ERROR checkout-service request failed status=500"
        ),
        environment="staging",
    )

    assert isinstance(report, IncidentReport)
    assert report.incident_id
    assert report.severity == "unknown"
    assert report.confidence == 0.0
    assert report.requires_human_approval is True


def test_report_contains_incident_evidence():
    report = investigate_incident(
        description="Checkout requests are failing.",
        log_sample="ERROR checkout-service failed",
        environment="development",
    )

    assert len(report.evidence) >= 1
    assert any(
        "Checkout requests are failing." in item.observation
        for item in report.evidence
    )


def test_invalid_input_is_rejected():
    with pytest.raises(GuardrailError):
        investigate_incident(
            description="   ",
            log_sample="ERROR checkout-service failed",
        )


def test_secret_is_redacted_before_entering_report():
    secret = "abcdef1234567890"

    report = investigate_incident(
        description="The service has a credential error.",
        log_sample=f"api_key={secret} service failed",
    )

    report_text = report.model_dump_json()

    assert secret not in report_text
    assert "[REDACTED_SECRET]" in report_text