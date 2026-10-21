
#!/usr/bin/env python

import argparse
import sys
import warnings
from datetime import datetime

from devops_ai.crew import DevopsAi
from devops_ai.history import show_incident_history
from devops_ai.report_viewer import show_incident_report

warnings.filterwarnings(
    "ignore",
    category=SyntaxWarning,
    module="pysbd",
)


def run():
    from devops_ai.services.investigations import run_ai_investigation

    description = input("Describe the incident: ").strip()

    if not description:
        return

    environment = (
        input(
            "Environment (development/staging/production/unknown): "
        )
        .strip()
        .lower()
        or "unknown"
    )

    print("\nPaste your logs below.")

    log_lines = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        if not line.strip():
            if log_lines:
                break
            continue

        log_lines.append(line)

    log_sample = "\n".join(log_lines).strip()

    if not log_sample:
        print("No logs were provided. Please run the investigation again.")
        return

    try:
        print("\nInvestigating incident. Please wait...\n")

        report = run_ai_investigation(
            description=description,
            log_sample=log_sample,
            environment=environment,
        )

        print("\n=== Investigation Results ===\n")
        print(report.model_dump_json(indent=2))
        print("\n=== Investigation Complete ===\n")

    except Exception as exc:
        print(f"\nInvestigation failed: {exc}")
        raise


def train():
    """Train the crew for a given number of iterations."""
    if len(sys.argv) < 3:
        raise ValueError(
            "Usage: devops_ai train <iterations> <filename>"
        )

    inputs = {
        "topic": "DevOps incident investigation",
        "current_year": str(datetime.now().year),
    }

    try:
        DevopsAi().crew().train(
            n_iterations=int(sys.argv[1]),
            filename=sys.argv[2],
            inputs=inputs,
        )
    except Exception as exc:
        raise RuntimeError(
            f"An error occurred while training the crew: {exc}"
        ) from exc


def replay():
    """Replay the crew execution from a specific task."""
    if len(sys.argv) < 2:
        raise ValueError("Usage: devops_ai replay <task_id>")

    try:
        DevopsAi().crew().replay(task_id=sys.argv[1])
    except Exception as exc:
        raise RuntimeError(
            f"An error occurred while replaying the crew: {exc}"
        ) from exc


def test():
    """Test the crew execution."""
    if len(sys.argv) < 3:
        raise ValueError(
            "Usage: devops_ai test <iterations> <eval_llm>"
        )

    inputs = {
        "topic": "DevOps incident investigation",
        "current_year": str(datetime.now().year),
    }

    try:
        DevopsAi().crew().test(
            n_iterations=int(sys.argv[1]),
            eval_llm=sys.argv[2],
            inputs=inputs,
        )
    except Exception as exc:
        raise RuntimeError(
            f"An error occurred while testing the crew: {exc}"
        ) from exc


def run_with_trigger():
    """Run the crew with a trigger payload."""
    import json

    if len(sys.argv) < 2:
        raise ValueError(
            "Usage: devops_ai run_with_trigger '<json_payload>'"
        )

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Invalid JSON payload provided as an argument."
        ) from exc

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "DevOps incident investigation",
        "current_year": str(datetime.now().year),
    }

    try:
        return DevopsAi().crew().kickoff(inputs=inputs)
    except Exception as exc:
        raise RuntimeError(
            f"An error occurred while running the crew with trigger: {exc}"
        ) from exc

def update_human_decision(
    decision: str,
    incident_id: str,
    reason: str | None = None,
) -> None:
    """Persist the user's approve/reject selection for an incident."""
    from devops_ai.storage.database import update_incident_human_approval

    if decision not in {"approve", "reject"}:
        raise ValueError("Decision must be 'approve' or 'reject'.")

    status = "approved" if decision == "approve" else "rejected"

    updated_report = update_incident_human_approval(
        incident_id=incident_id,
        status=status,
        reason=reason,
    )

    if updated_report is None:
        print(f"No incident found for ID: {incident_id}")
        return

    print(
        f"Incident {incident_id} marked as {status}. "
        "The decision was saved to the database."
    )

def main():
    """Handle DevOpsAI CLI commands."""
    parser = argparse.ArgumentParser(
        description="DevOpsAI incident investigation CLI"
    )

    subparsers = parser.add_subparsers(dest="command")

    # Display saved incident history.
    history_parser = subparsers.add_parser(
        "history",
        help="Display previously saved incidents",
    )
    history_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum incidents to display (1-100)",
    )

    # Display a complete saved report.
    report_parser = subparsers.add_parser(
        "report",
        help="Display a saved incident report by ID",
    )
    report_parser.add_argument(
        "incident_id",
        help="ID of the incident to retrieve",
    )

    # Human in the loop
    approve_parser = subparsers.add_parser(
        "approve",
        help="Approve the remediation for an incident report",
    )
    approve_parser.add_argument(
        "incident_id",
        help="Incident ID to approve",
    )
    approve_parser.add_argument(
        "--reason",
        default=None,
        help="Optional justification for the approval decision",
    )

    reject_parser = subparsers.add_parser(
        "reject",
        help="Reject the remediation for an incident report",
    )
    reject_parser.add_argument(
        "incident_id",
        help="Incident ID to reject",
    )
    reject_parser.add_argument(
        "--reason",
        default=None,
        help="Optional justification for the rejection decision",
    )

    args = parser.parse_args()

    if args.command == "history":
        if not 1 <= args.limit <= 100:
            parser.error("--limit must be between 1 and 100")

        show_incident_history(limit=args.limit)
        return

    if args.command == "report":
        show_incident_report(args.incident_id)
        return

    if args.command == "approve":
        update_human_decision("approve", args.incident_id, args.reason)
        return

    if args.command == "reject":
        update_human_decision("reject", args.incident_id, args.reason)
        return
    
    # Preserve the generated CrewAI scaffold commands.
    if args.command == "train":
        train()
        return
    
    elif args.command == "replay":
        replay()
        return
    
    elif args.command == "test":
        test()
        return
    
    elif args.command == "run_with_trigger":
        run_with_trigger()
        return
    
    else:
        run()


if __name__ == "__main__":
    main()
