import gradio as gr

from devops_ai.guardrails import GuardrailError
from devops_ai.schemas import IncidentReport
from devops_ai.services.investigations import run_ai_investigation


def format_report(report: IncidentReport) -> str:
    """Turn the structured report into readable markdown."""
    lines = [
        f"## Incident `{report.incident_id}`",
        f"**Severity:** {report.severity}  ",
        f"**Confidence:** {report.confidence:.0%}  ",
        f"**Requires human approval:** {'Yes' if report.requires_human_approval else 'No'}",
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


LOADING_MESSAGE = (
    '<span class="spin">⚙️</span> **Investigating...** '
    "The agents are analysing the incident, this can take a minute or two."
)

CSS = """
.spin { display: inline-block; animation: spin 1.5s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
"""


def investigate(description: str, environment: str, log_sample: str):
    """Show a loading message, run the investigation, then show the report."""
    # Show the loading message and disable the button while the crew runs.
    yield LOADING_MESSAGE, gr.update(value="⚙️ Investigating...", interactive=False)

    try:
        report = run_ai_investigation(
            description=description,
            log_sample=log_sample,
            environment=environment,
        )
        result = format_report(report)
    except GuardrailError as exc:
        result = f"**Input error:** {exc}"
    except Exception as exc:
        result = f"**Investigation failed:** {exc}"

    yield result, gr.update(value="Investigate", interactive=True)


with gr.Blocks(title="DevOpsAI") as demo:
    gr.Markdown("# DevOpsAI Incident Investigation")

    description = gr.Textbox(label="Incident description", lines=3)
    environment = gr.Dropdown(
        label="Environment",
        choices=["development", "staging", "production", "unknown"],
        value="unknown",
    )
    log_sample = gr.Textbox(label="Logs", lines=10)
    button = gr.Button("Investigate", variant="primary")

    output = gr.Markdown()

    button.click(
        investigate,
        inputs=[description, environment, log_sample],
        outputs=[output, button],
    )


def main():
    demo.launch(css=CSS)


if __name__ == "__main__":
    main()
