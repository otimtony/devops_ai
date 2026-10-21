import html
import queue
import tempfile
import threading
from pathlib import Path

import gradio as gr
from crewai.tasks.task_output import TaskOutput

from devops_ai.guardrails import GuardrailError
from devops_ai.schemas import IncidentReport
from devops_ai.services.investigations import run_ai_investigation
from devops_ai.storage.database import (
    get_incident_input,
    get_incident_report,
    list_incidents,
    update_incident_human_approval,
)


def format_report(report: IncidentReport) -> str:
    """Turn the structured report into readable markdown."""
    lines = [
        f"## Incident `{report.incident_id}`",
        f"**Severity:** {report.severity}  ",
        f"**Confidence:** {report.confidence:.0%}  ",
        f"**Approval status:** {report.human_approval_status}",
        *([f"**Approval reason:** {report.human_approval_reason}"] if report.human_approval_reason else []),
        "",
        "### Summary",
        report.summary,
        "",
        "### Likely causes",
        *[f"- {cause}" for cause in report.likely_causes],
        "",
        "### Evidence",
        *[
            f"- **[{item.evidence_type}]** {item.observation} _(source: {item.source})_"
            for item in report.evidence
        ],
        "",
        "### Recommended actions",
        *[f"{i}. {action}" for i, action in enumerate(report.recommended_actions, 1)],
    ]
    return "\n".join(lines)


# Crew tasks run sequentially in this order (see crew.py).
STEPS = [
    "Incident triage",
    "Log analysis",
    "Technical research",
    "Root cause analysis",
    "Remediation & risk assessment",
]


def progress_markdown(completed: list[TaskOutput]) -> str:
    """Render the crew's progress, showing each finished step's output."""
    lines = [
        "### Investigating...",
        "The agents are analysing the incident, this can take a minute or two.",
        "",
    ]
    for i, step in enumerate(STEPS):
        if i < len(completed):
            output = completed[i]
            snippet = output.raw if len(output.raw) <= 600 else output.raw[:600] + "..."
            lines += [
                f"<details><summary>✅ <b>{step}</b> — {html.escape(str(output.agent))}</summary>",
                f"<pre style='white-space: pre-wrap'>{html.escape(snippet)}</pre></details>",
                "",
            ]
        elif i == len(completed):
            lines += [f'<span class="spin">⚙️</span> **{step}** — working...', ""]
        else:
            lines += [f"⏳ {step}", ""]
    return "\n".join(lines)

CSS = """
#header h1 { margin-bottom: 0; }
#header p { margin-top: 4px; opacity: 0.7; }
#report-actions { justify-content: flex-end; gap: 8px; margin-bottom: -8px; }
#approval { padding: 12px 16px; border-radius: 8px; border: 1px solid var(--color-accent); }
#report { padding: 16px 20px; border-radius: 8px; border: 1px solid var(--border-color-primary); }
.spin { display: inline-block; animation: spin 1.5s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
"""


def history_choices() -> list[tuple[str, str]]:
    """Build sidebar entries for approved incidents, newest first."""
    choices = []
    for incident in list_incidents(limit=50, approved_only=True):
        description = incident["description"]
        if len(description) > 40:
            description = description[:40] + "..."
        created = incident["created_at"][:16].replace("T", " ")
        label = f"{created} · {incident['environment']} — {description}"
        choices.append((label, incident["incident_id"]))
    return choices


SHARE_JS = """
(text) => {
    if (navigator.share) {
        navigator.share({ title: "Incident report", text });
    } else {
        navigator.clipboard.writeText(text);
        alert("Report copied to clipboard.");
    }
}
"""


def report_file(report: IncidentReport, markdown: str) -> str:
    """Write the rendered report to a markdown file for downloading."""
    path = Path(tempfile.gettempdir()) / f"incident_{report.incident_id}.md"
    path.write_text(markdown, encoding="utf-8")
    return str(path)


def read_log_file(path: str | None) -> str:
    """Load an uploaded log file into the logs textbox."""
    if not path:
        return gr.update()
    return Path(path).read_text(encoding="utf-8", errors="replace")


def show_saved_report(incident_id: str):
    """Load an approved report from history and fill the form with its inputs."""
    report = get_incident_report(incident_id)
    if report is None:
        return (
            f"**No report found for incident** `{incident_id}`",
            gr.update(visible=False),
            gr.update(),
            gr.update(visible=False),
            gr.update(),
            gr.update(),
            gr.update(),
        )
    incident = get_incident_input(incident_id)
    result = format_report(report)
    return (
        result,
        gr.update(visible=True),
        report_file(report, result),
        gr.update(visible=False),
        incident["description"],
        incident["environment"],
        incident["log_sample"],
    )


def investigate(description: str, environment: str, log_sample: str):
    """Show a loading message, run the investigation, then ask for approval."""
    # Show the loading message and disable the button while the crew runs.
    yield (
        progress_markdown([]),
        gr.update(value="⚙️ Investigating...", interactive=False),
        gr.update(visible=False),
        gr.update(visible=False),
        None,
    )
    approval = gr.update(visible=False)
    incident_id = None

    # Run the crew in a background thread so each finished task can be streamed.
    task_outputs: queue.Queue[TaskOutput | None] = queue.Queue()
    outcome = {}

    def run_crew():
        try:
            outcome["report"] = run_ai_investigation(
                description=description,
                log_sample=log_sample,
                environment=environment,
                on_task_complete=task_outputs.put,
            )
        except Exception as exc:
            outcome["error"] = exc
        finally:
            task_outputs.put(None)

    threading.Thread(target=run_crew, daemon=True).start()

    completed = []
    while (output := task_outputs.get()) is not None:
        # A rate-limit retry restarts the crew, so start the progress list over.
        if len(completed) == len(STEPS):
            completed = []
        completed.append(output)
        yield progress_markdown(completed), gr.update(), gr.update(), gr.update(), gr.update()

    try:
        if "error" in outcome:
            raise outcome["error"]
        report = outcome["report"]
        result = format_report(report)
        # Human in the loop: the report stays private until it is approved.
        approval = gr.update(visible=True)
        incident_id = report.incident_id
    except GuardrailError as exc:
        result = f"**Input error:** {exc}"
    except Exception as exc:
        result = f"**Investigation failed:** {exc}"

    yield (
        result,
        gr.update(value="Investigate", interactive=True),
        approval,
        gr.update(visible=False),
        incident_id,
    )


def record_decision(incident_id: str | None, reason: str, status: str):
    """Persist the human approval decision and unlock the report if approved."""
    report = update_incident_human_approval(incident_id, status, reason) if incident_id else None
    if report is None:
        return (
            "**Could not record decision:** incident not found.",
            gr.update(visible=False),
            gr.update(),
            gr.update(visible=False),
            gr.update(),
            "",
        )

    result = format_report(report)
    approved = status == "approved"
    return (
        result,
        gr.update(visible=approved),
        report_file(report, result) if approved else gr.update(),
        gr.update(visible=False),
        gr.update(choices=history_choices(), value=incident_id if approved else None),
        "",
    )


with gr.Blocks(title="DevOpsAI") as demo:
    current_incident = gr.State(None)

    with gr.Sidebar(open=True):
        gr.Markdown("### Incident history")
        refresh_button = gr.Button("↻ Refresh", size="sm")
        history = gr.Radio(choices=history_choices(), label="Saved reports", show_label=False)

    gr.Markdown(
        "# DevOpsAI Incident Investigation\n"
        "Describe an incident and paste relevant logs to get an AI-assisted root-cause report.",
        elem_id="header",
    )

    with gr.Row():
        with gr.Column(scale=3):
            description = gr.Textbox(label="Incident description", lines=3)
        with gr.Column(scale=1):
            environment = gr.Dropdown(
                label="Environment",
                choices=["development", "staging", "production", "unknown"],
                value="unknown",
            )
    log_sample = gr.Textbox(label="Logs", lines=10, max_lines=20)
    log_upload = gr.UploadButton(
        "📄 Upload log file", file_types=[".txt", ".log"], size="sm"
    )
    button = gr.Button("Investigate", variant="primary")

    with gr.Column(elem_id="approval", visible=False) as approval_panel:
        gr.Markdown("**Human review required.** Approve this report to save it to history and enable download and sharing.")
        approval_reason = gr.Textbox(label="Reason (optional)", lines=1)
        with gr.Row():
            approve_button = gr.Button("✅ Approve", variant="primary")
            reject_button = gr.Button("❌ Reject", variant="stop")

    with gr.Row(elem_id="report-actions", visible=False) as report_actions:
        download_button = gr.DownloadButton("⬇ Download", size="sm", scale=0)
        share_button = gr.Button("🔗 Share", size="sm", scale=0)
    output = gr.Markdown(elem_id="report")

    decision_outputs = [
        output,
        report_actions,
        download_button,
        approval_panel,
        history,
        approval_reason,
    ]

    log_upload.upload(read_log_file, inputs=log_upload, outputs=log_sample)
    button.click(
        investigate,
        inputs=[description, environment, log_sample],
        outputs=[output, button, approval_panel, report_actions, current_incident],
    )
    approve_button.click(
        lambda incident_id, reason: record_decision(incident_id, reason, "approved"),
        inputs=[current_incident, approval_reason],
        outputs=decision_outputs,
    )
    reject_button.click(
        lambda incident_id, reason: record_decision(incident_id, reason, "rejected"),
        inputs=[current_incident, approval_reason],
        outputs=decision_outputs,
    )
    history.input(
        show_saved_report,
        inputs=history,
        outputs=[
            output,
            report_actions,
            download_button,
            approval_panel,
            description,
            environment,
            log_sample,
        ],
    )
    share_button.click(None, inputs=output, js=SHARE_JS)
    refresh_history = lambda: gr.update(choices=history_choices())
    refresh_button.click(refresh_history, outputs=history)
    # Reload history on every page load; choices set at build time go stale.
    demo.load(refresh_history, outputs=history)


def main():
    demo.launch(css=CSS, theme=gr.themes.Soft(primary_hue="indigo"))


if __name__ == "__main__":
    main()
