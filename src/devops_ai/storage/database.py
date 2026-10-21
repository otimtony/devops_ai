import sqlite3
from pathlib import Path

from devops_ai.config import settings
from devops_ai.schemas import IncidentInput, IncidentReport

from typing import Literal

from devops_ai.config import settings
from devops_ai.schemas import IncidentInput, IncidentReport


def update_incident_human_approval(
    incident_id: str,
    status: Literal["approved", "rejected"],
    reason: str | None = None,
    database_path: Path | None = None,
) -> IncidentReport | None:
    """Persist a human approval decision for a saved incident report."""
    if status not in {"approved", "rejected"}:
        raise ValueError("Status must be 'approved' or 'rejected'.")

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT report_json
            FROM incidents
            WHERE incident_id = ?
            """,
            (incident_id,),
        ).fetchone()

    if row is None:
        return None

    report = IncidentReport.model_validate_json(row["report_json"])
    report.human_approval_status = status
    report.human_approval_reason = (
        reason.strip() if reason and reason.strip() else None
    )
    report.requires_human_approval = False

    with get_connection(database_path) as connection:
        connection.execute(
            """
            UPDATE incidents
            SET report_json = ?
            WHERE incident_id = ?
            """,
            (report.model_dump_json(), incident_id),
        )
        connection.commit()

    return report

def get_connection(database_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection to the DevOpsAI SQLite database."""
    path = database_path or settings.database_path
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path: Path | None = None) -> None:
    """Create the incident history table if it does not exist."""
    with get_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                environment TEXT NOT NULL,
                created_at TEXT NOT NULL,
                report_json TEXT NOT NULL
            )
            """
        )


def save_incident(
    incident: IncidentInput,
    report: IncidentReport,
    database_path: Path | None = None,
) -> None:
    """Persist an incident/report and keep the report ID as the canonical key."""
    canonical_incident_id = report.incident_id or incident.incident_id

    if not canonical_incident_id:
        raise ValueError("Incident ID is required before saving.")

    # Keep the report ID as the source of truth, but don't fail the write.
    if (
        incident.incident_id
        and report.incident_id
        and incident.incident_id != report.incident_id
    ):
        print(
            "Warning: incident ID mismatch detected. "
            f"Using report incident_id '{canonical_incident_id}' as canonical."
        )

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO incidents (
                incident_id,
                description,
                environment,
                created_at,
                report_json
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(incident_id)
            DO UPDATE SET
                description = excluded.description,
                environment = excluded.environment,
                created_at = excluded.created_at,
                report_json = excluded.report_json
            """,
            (
                canonical_incident_id,
                incident.description,
                incident.environment,
                incident.created_at.isoformat(),
                report.model_dump_json(),
            ),
        )
        connection.commit()


def get_incident_report(
    incident_id: str,
    database_path: Path | None = None,
) -> IncidentReport | None:
    initialize_database(database_path)

    with get_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT report_json
            FROM incidents
            WHERE incident_id = ?
            """,
            (incident_id,),
        ).fetchone()

    if row is None:
        return None

    return IncidentReport.model_validate_json(row["report_json"])


def list_incidents(
    limit: int = 20,
    database_path: Path | None = None,
) -> list[dict]:
    """Return recent incident summaries, newest first."""
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100.")

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT incident_id, description, environment, created_at
            FROM incidents
            ORDER BY created_at DESC, incident_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]