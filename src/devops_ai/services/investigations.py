import time
from collections.abc import Callable

from crewai.tasks.task_output import TaskOutput
from litellm.exceptions import RateLimitError

from devops_ai.guardrails import validate_incident
from devops_ai.schemas import EvidenceItem, IncidentInput, IncidentReport
from devops_ai.crew import DevopsAi
from devops_ai.storage.database import save_incident

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

def run_ai_investigation(
    description: str,
    log_sample: str,
    environment: str = "unknown",
    on_task_complete: Callable[[TaskOutput], None] | None = None,
    ) -> IncidentReport:
    """Validate an incident and run the CrewAI investigation.

    on_task_complete is called with each task's output as the crew progresses.
    """

    # Validate input and redact secrets before sending anything to the LLM.
    incident = validate_incident(
        description=description,
        log_sample=log_sample,
        environment=environment,
    )

    # Pass only validated, sanitized data to the agents.
    inputs = {
        "incident_id": incident.incident_id,
        "description": incident.description,
        "log_sample": incident.log_sample,
        "environment": incident.environment,
    }

    for attempt in range(3):
        try:
            crew = DevopsAi().crew()
            if on_task_complete:
                crew.task_callback = on_task_complete
            result = crew.kickoff(inputs=inputs)
            break
        except RateLimitError as exc:
            if attempt == 2:
                raise
            wait_seconds = 30 * (attempt + 1)
            print(
                f"Groq rate limit hit while running the investigation. "
                f"Retrying in {wait_seconds} seconds (attempt {attempt + 2}/3)."
            )
            time.sleep(wait_seconds)
    else:
        raise RuntimeError("Investigation failed after retrying for rate limits.")

    if result.pydantic is None:
        raise RuntimeError(
            "CrewAI did not produce a valid structured incident report."
        )

    
    report = result.pydantic

    if report is None:
        raise RuntimeError(
            "The investigation completed without producing a valid structured IncidentReport."
        )

    save_incident(incident, report)

    return report