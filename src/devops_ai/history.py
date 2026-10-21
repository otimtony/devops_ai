from devops_ai.storage.database import list_incidents, get_incident_report


def show_incident_history(limit: int = 20) -> None:
    """Display previously saved incident investigations with full report details."""
    incidents = list_incidents(limit=limit)

    if not incidents:
        print("\nNo saved incidents found.")
        return

    print(f"\nSaved incidents: {len(incidents)}")
    print("-" * 80)

    for incident in incidents:
        incident_id = incident["incident_id"]
        report = get_incident_report(incident_id)

        print(f"ID:          {incident_id}")
        print(f"Environment: {incident['environment']}")
        print(f"Created:     {incident['created_at']}")
        print(f"Description: {incident['description']}")

        if report is None:
            print("Report:      unable to load report payload")
        else:
            print(f"Severity:    {report.severity}")
            print(f"Summary:     {report.summary}")
            print(f"Confidence:  {report.confidence}")
            print(f"Human approval required: {report.requires_human_approval}")
            print("Likely causes:")
            for cause in report.likely_causes:
                print(f"  - {cause}")

            print("Recommended actions:")
            for action in report.recommended_actions:
                print(f"  - {action}")

        print("-" * 80)