import re

from pydantic import ValidationError

from devops_ai.config import settings
from devops_ai.schemas import IncidentInput

SECRET_PATTERNS = [
    re.compile(r"(?i)\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(api[_-]?key|password|secret|access[_-]?token)"
        r"\s*[:=]\s*['\"]?([^\s,'\"]{8,})"
    ),
]


class GuardrailError(ValueError):
    """Raised when incident input fails a safety check."""

def redact_secrets(text: str) -> str:
    """Replace common secret patterns before sending text to an AI model."""

    redacted = text

    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)

    return redacted


def validate_incident(
    description: str,
    log_sample: str,
    environment: str = "unknown",
) -> IncidentInput:

    #************************** validate inputs **************************
    if not isinstance(description, str) or not isinstance(log_sample, str):
        raise GuardrailError("Description and log sample must be text.")

    description = description.strip()
    log_sample = log_sample.strip()

    if not description:
        raise GuardrailError("Please provide an incident description.")

    if not log_sample:
        raise GuardrailError("Please provide a sample of the relevant logs.")

    if len(description) > settings.max_incident_description_chars:
        raise GuardrailError(
            "Incident description exceeds the configured character limit."
        )

    if len(log_sample) > settings.max_log_sample_chars:
        raise GuardrailError(
            "Log sample exceeds the configured character limit."
        )

    # Redact common secret formats before the text reaches an AI agent.
    safe_description = redact_secrets(description)
    safe_logs = redact_secrets(log_sample)

    try:
        return IncidentInput(
            description=safe_description,
            log_sample=safe_logs,
            environment=environment,
        )
    except ValidationError as exc:
        raise GuardrailError(
            "Incident input is invalid. Check the description, log sample, "
            "and environment."
        ) from exc