
from devops_ai.storage.database import get_incident_report

#******************** display incident report **********************
def show_incident_report(incident_id: str) -> None:
    report = get_incident_report(incident_id)

    if report is None:
        print(f"\nNo report found for incident ID: {incident_id}")
        return

    print("\n***************** Saved Incident Report *****************")
    print(f"Incident ID: {report.incident_id}")
    print(f"Severity: {report.severity.upper()}")
    print(f"Confidence: {report.confidence:.0%}")
    print(f"Human approval required: {report.requires_human_approval}")
    print(f"Human approval status: {report.human_approval_status}")
    if report.human_approval_reason:
        print(f"Human approval reason: {report.human_approval_reason}")

    print("\n******************* Summary ********************")
    print(report.summary)

    print("\n******************* Likely Causes *******************")
    if report.likely_causes:
        for index, cause in enumerate(report.likely_causes, start=1):
            print(f"{index}. {cause}")
    else:
        print("No likely causes recorded.")

    print("\n******************** Evidence *********************")
    if report.evidence:
        for index, item in enumerate(report.evidence, start=1):
            print(f"{index}. Observation: {item.observation}")
            print(f"   Source: {item.source}")
            print(f"   Type: {item.evidence_type}")
    else:
        print("No evidence recorded.")

    print("\n ******************* Recommended Actions *******************")
    if report.recommended_actions:
        for index, action in enumerate(
            report.recommended_actions,
            start=1,
        ):
            print(f"{index}. {action}")
    else:
        print("No recommended actions recorded.")
