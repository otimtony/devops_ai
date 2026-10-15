from devops_ai.guardrails import validate_incident
from devops_ai.schemas import EvidenceItem, IncidentInput, IncidentReport


def create_preliminary_report(
    incident: IncidentInput,
) -> IncidentReport:
    """Create an initial report before AI-powered investigation begins."""

    return IncidentReport(
        incident_id=incident.incident_id,
        summary=(
            f"An incident was reported in the "
            f"{incident.environment} environment. "
            "Automated root-cause analysis has not run yet."
        ),
        severity="unknown",
        likely_causes=[],
        evidence=[
            EvidenceItem(
                observation=incident.description,
                source="User-provided incident description",
                evidence_type="fact",
            ),
            EvidenceItem(
                observation=incident.log_sample[:1_000],                 
                source="User-provided log sample",
                evidence_type="fact",
            ),
        ],
        recommended_actions=[
            "Review the supplied logs and identify relevant errors.",
            "Check service health metrics and recent deployments.",
            "Investigate possible causes before selecting remediation.",
        ],
        confidence=0.0,
        requires_human_approval=True,
    )

def investigate_incident(
    description: str,
    log_sample: str,
    environment: str = "unknown",
) -> IncidentReport:
    """Validate incident input and return a preliminary report."""

    incident = validate_incident(
        description=description,
        log_sample=log_sample,
        environment=environment,
    )

    return create_preliminary_report(incident)