
#!/usr/bin/env python
import sys
import warnings
from datetime import datetime

from devops_ai.crew import DevopsAi

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """Collect incident details and run the AI investigation."""
    from devops_ai.services.investigations import run_ai_investigation

    print("\n=== DevOpsAI Incident Investigation ===\n")

    # Collect the incident description.
    description = input("Describe the incident: ").strip()

    if not description:
        print("Please provide an incident description.")
        return

    # Collect the environment.
    environment = (
        input(
            "Environment (development/staging/production/unknown): "
        )
        .strip()
        .lower()
        or "unknown"
    )

    # Collect multiple lines of logs.
    print("\nPaste your logs below.")
    print("Press Enter on an empty line when finished:\n")

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

        result = run_ai_investigation(
            description=description,
            log_sample=log_sample,
            environment=environment,
        )

        print("\n=== Investigation Results ===\n")
        print(result)
        print("\n=== Investigation Complete ===\n")

    except Exception as exc:
        print(f"\nInvestigation failed: {exc}")
        raise


def train():
    """Train the crew for a given number of iterations."""
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
        raise Exception(
            f"An error occurred while training the crew: {exc}"
        ) from exc


def replay():
    """Replay the crew execution from a specific task."""
    try:
        DevopsAi().crew().replay(task_id=sys.argv[1])
    except Exception as exc:
        raise Exception(
            f"An error occurred while replaying the crew: {exc}"
        ) from exc


def test():
    """Test the crew execution."""
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
        raise Exception(
            f"An error occurred while testing the crew: {exc}"
        ) from exc


def run_with_trigger():
    """Run the crew with a trigger payload."""
    import json

    if len(sys.argv) < 2:
        raise ValueError(
            "No trigger payload provided. "
            "Please provide a JSON payload as an argument."
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
        raise Exception(
            f"An error occurred while running the crew with trigger: {exc}"
        ) from exc
