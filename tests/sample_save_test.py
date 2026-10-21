from datetime import datetime, timezone
from uuid import uuid4

from devops_ai.schemas import IncidentInput, IncidentReport, EvidenceItem
from devops_ai.storage.database import save_incident, get_incident_report

incident_id = str(uuid4())

incident = IncidentInput(
    incident_id=incident_id,
    description="Checkout requests are intermittently failing with HTTP 500 errors after deployment.",
    log_sample="""
    2026-10-15T14:20:01Z ERROR checkout-service Database connection timeout
    2026-10-15T14:20:03Z ERROR checkout-service Request failed with status 500
    2026-10-15T14:20:08Z WARN checkout-service Connection pool utilization high
    2026-10-15T14:20:12Z ERROR checkout-service Database connection timeout
    """,
    environment="staging",
    created_at=datetime.now(timezone.utc),
)

report = IncidentReport(
    incident_id=incident_id,
    summary="Checkout requests are failing due to intermittent database timeouts after deployment.",
    severity="high",
    likely_causes=[
        "Database connection pool exhaustion",
        "Deployment-related configuration change"
    ],
    evidence=[
        EvidenceItem(
            observation="Database connection timeout observed in checkout-service logs.",
            source="application logs",
            evidence_type="fact",
        ),
        EvidenceItem(
            observation="Connection pool utilization high before the 500 response.",
            source="application logs",
            evidence_type="fact",
        ),
    ],
    recommended_actions=[
        "Review deployment config and database pool settings.",
        "Check database connection usage and timeout thresholds.",
        "Validate rollback options if the issue continues."
    ],
    confidence=0.82,
    requires_human_approval=True,
)

save_incident(incident, report)

saved = get_incident_report(incident_id)

print("Saved report:")
print(saved)
print("\nIncident id:", saved.incident_id if saved else "not found")
print("Summary:", saved.summary if saved else "not found")