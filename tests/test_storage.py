
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from devops_ai.schemas import IncidentInput, IncidentReport, EvidenceItem
from devops_ai.storage.database import (
    get_incident_report,
    initialize_database,
    list_incidents,
    save_incident,
)


@pytest.fixture
def incident_and_report():
    incident_id = str(uuid4())

    incident = IncidentInput(
        incident_id=incident_id,
        description="Checkout requests are returning HTTP 500 errors.",
        log_sample="ERROR: CheckoutService returned HTTP 500",
        environment="staging",
        created_at=datetime.now(timezone.utc),
    )

    report = IncidentReport(
        incident_id=incident_id,
        summary="Checkout requests are failing with HTTP 500 errors.",
        severity="high",
        likely_causes=["Possible regression after deployment"],
        evidence=[
            EvidenceItem(
                observation="CheckoutService returned HTTP 500",
                source="User-provided logs",
                evidence_type="fact",
            )
        ],
        recommended_actions=[
            "Review the latest deployment and application logs."
        ],
        confidence=0.75,
        requires_human_approval=True,
    )

    return incident, report


def test_initialize_database(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)

    assert database_path.exists()


def test_save_and_retrieve_report(tmp_path, incident_and_report):
    incident, report = incident_and_report
    database_path = tmp_path / "test.db"

    save_incident(incident, report, database_path)

    retrieved = get_incident_report(
        incident.incident_id,
        database_path,
    )

    assert retrieved is not None
    assert retrieved.incident_id == report.incident_id
    assert retrieved.summary == report.summary
    assert retrieved.severity == "high"
    assert retrieved.evidence[0].evidence_type == "fact"


def test_missing_report_returns_none(tmp_path):
    database_path = tmp_path / "test.db"

    result = get_incident_report(
        "missing-incident",
        database_path,
    )

    assert result is None


def test_list_incidents(tmp_path, incident_and_report):
    incident, report = incident_and_report
    database_path = tmp_path / "test.db"

    save_incident(incident, report, database_path)

    results = list_incidents(database_path=database_path)

    assert len(results) == 1
    assert results[0]["incident_id"] == incident.incident_id
    assert results[0]["environment"] == "staging"


def test_mismatched_ids_are_rejected(tmp_path, incident_and_report):
    incident, report = incident_and_report
    database_path = tmp_path / "test.db"

    mismatched_report = report.model_copy(
        update={"incident_id": str(uuid4())}
    )

    with pytest.raises(ValueError, match="Incident ID"):
        save_incident(incident, mismatched_report, database_path)


def test_saving_same_incident_updates_existing_record(
    tmp_path,
    incident_and_report,
):
    incident, report = incident_and_report
    database_path = tmp_path / "test.db"

    save_incident(incident, report, database_path)

    updated_report = report.model_copy(
        update={"summary": "Updated incident summary."}
    )

    save_incident(incident, updated_report, database_path)

    retrieved = get_incident_report(
        incident.incident_id,
        database_path,
    )
    results = list_incidents(database_path=database_path)

    assert retrieved is not None
    assert retrieved.summary == "Updated incident summary."
    assert len(results) == 1
