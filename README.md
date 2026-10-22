# DevOpsAI

A multi-agent incident investigation assistant built with [crewAI](https://crewai.com).

Describe a production incident and paste some logs. Five AI agents investigate it one after another and produce a structured incident report with severity, likely causes, evidence, recommended actions and a confidence score. Every report is saved to a local SQLite database.

The assistant only recommends actions. It never makes changes itself, and every report requires human approval.

## How it works

```
input ─► guardrails (validate + redact secrets) ─► 5-agent crew ─► IncidentReport ─► SQLite
```

| Agent | What it does |
|---|---|
| Incident Triage | Assesses impact, scope and severity, and lists missing information |
| Log Analysis | Finds errors, timestamps and patterns in the supplied logs |
| Technical Research | Combines general LLM knowledge with recent human-approved reports from SQLite |
| Root Cause | Ranks root-cause hypotheses using the evidence for and against each one |
| Remediation & Risk | Produces the final validated report with recommended actions |

Before anything is sent to the model, the guardrails reject empty or oversized input and redact common secret patterns (AWS keys, `password=...`, `api_key=...`).

The Technical Research agent compares its general knowledge with up to three recent human-approved reports from SQLite. It receives report summaries and incident IDs, not historical raw logs, and must treat past incidents as examples rather than proof of the current cause. It does not search the live web.

## Project structure

```
src/devops_ai/
├── main.py                  # Interactive CLI
├── app.py                   # Gradio web UI
├── crew.py                  # Agents, tasks and crew setup
├── config/agents.yaml       # Agent roles and goals
├── config/tasks.yaml        # Task prompts
├── config.py                # Settings loaded from .env
├── guardrails.py            # Input validation and secret redaction
├── schemas.py               # IncidentInput / IncidentReport models
├── services/investigations.py  # Investigation workflow
└── storage/database.py      # SQLite incident history
tests/                       # pytest tests (no API key needed)
```

## Setup

You need Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/).

```bash
pip install uv
uv sync
```

If `uv` isn't on your PATH after installing it with pip, run it as `python -m uv` instead, for example `python -m uv sync`.

Create your `.env` file from the example and add your OpenAI API key:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | – | OpenAI API key used by the agents |
| `APP_NAME` | No | `DevOpsAI` | Application name |
| `ENVIRONMENT` | No | `development` | Application environment |
| `MAX_INCIDENT_DESCRIPTION_CHARS` | No | `5000` | Maximum length of the incident description |
| `MAX_LOG_SAMPLE_CHARS` | No | `20000` | Maximum length of the log sample |
| `DATABASE_PATH` | No | `data/devops_ai.db` | Location of the SQLite database |

## Usage

**Web UI (Gradio):**

```bash
uv run ui
```

Then open http://127.0.0.1:7860.

**Command line:**

```bash
uv run devops_ai
```

You'll be asked for an incident description, the environment, and the logs (finish with an empty line).

An investigation takes a minute or two because the agents run one after another. The final report is also written to `incident_report.md`.

## Tests

```bash
uv run pytest tests
```

The tests cover the guardrails, the preliminary report and the storage layer. They don't call the OpenAI API.
