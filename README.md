# CCCL Hackathon — AI Clinical Scribe

An AI-assisted clinical documentation system for Indian OPD consultations: ambient transcription → structured SOAP notes + entity extraction → a patient-facing chat over their own records.

See [docs/usecase.md](docs/usecase.md) for the original architecture writeup (STT config, Indian drug-brand mapping, FHIR output format) and this session's memory for the current two-service design — summarized below.

## Architecture

Two independent ADK agent services, no shared auth (out of scope for the hackathon):

- **`services/doctor-service`** — doctor uploads a transcript → an orchestrator fans out in parallel to (a) generate a SOAP note and (b) extract structured entities → both are written to the patient's record in Firestore.
- **`services/patient-service`** — patient enters a patient ID → the service fetches that patient's records from Firestore into context → patient chats over those records (simple context-stuffed chat, not vector-search RAG).

A single frontend UI is expected to have two tabs (Doctor / Patient), each talking to its respective service.

> **Current status:** both services are freshly scaffolded ADK projects (`agents-cli scaffold create`) with placeholder agent logic — not yet the doctor/patient pipeline described above. Deployment target is `none` (prototype); Cloud Run isn't wired in yet.

## Repository layout

```
CCCL_Hackathon/
├── services/
│   ├── doctor-service/     # ADK agent project — doctor-facing pipeline
│   └── patient-service/    # ADK agent project — patient-facing chat
├── aci-bench-corpus/        # Ambient clinical intelligence benchmark dataset (reference/eval data)
├── docs/usecase.md          # Original architecture writeup
├── analysis_results.md      # Prior analysis notes
└── .claude/skills/          # Project-specific Claude Code skills (see below)
```

## Prerequisites

Install these once per machine:

1. **Python 3.12** (this repo's root `.venv` was created with 3.12.4; each service manages its own env via `uv`).
2. **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — Python package/dependency manager used by both services.
3. **agents-cli** (Google Agents CLI) — wraps ADK scaffolding, local runs, eval, and deployment:
   ```bash
   uv tool install google-agents-cli
   uvx google-agents-cli setup   # installs the agents-cli Claude Code skills
   ```
4. **[Google Cloud SDK](https://cloud.google.com/sdk/docs/install)** (`gcloud`) — for auth and (later) Cloud Run deployment.
5. Access to the shared GCP project (ask whoever owns it to add you), then authenticate:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project <the-gcp-project-id>
   ```

## Getting the code running

```bash
git clone <repo-url>
cd CCCL_Hackathon
```

Each service is a self-contained ADK project — set them up independently.

### doctor-service

```bash
cd services/doctor-service
cp .env.example .env          # then fill in GOOGLE_CLOUD_PROJECT
agents-cli install            # installs deps via uv
agents-cli playground         # local web UI for interactive testing, auto-reloads on save
```

### patient-service

```bash
cd services/patient-service
cp .env.example .env          # then fill in GOOGLE_CLOUD_PROJECT
agents-cli install
agents-cli playground
```

`agents-cli playground` runs each service independently on its own local port — run both in separate terminals if you want to work on them side by side.

### Quick one-off test without the playground UI

```bash
agents-cli run "your test prompt"
```

## Project-specific Claude Code skills

This repo ships two skills under `.claude/skills/` (auto-discovered by Claude Code when working in this directory):

- **`python-gcp-review`** — reviews Python code and GCP architecture choices against best practices (IAM, secrets, Cloud Run config, Firestore/Pub-Sub patterns, PHI-handling) and checks the code against the intended architecture.
- **`deploy-cloud-run`** — deploys `doctor-service` or `patient-service` to Cloud Run; asks for the target service name, GCP project, and region rather than assuming them.

There's also a broader `google-agents-cli-*` skill suite installed globally (scaffold, ADK code patterns, eval, deploy, observability, publish) — `agents-cli info` inside a service directory will tell you what's configured.

## Data

`aci-bench-corpus/` contains the ACI-BENCH ambient clinical intelligence dataset (transcripts + reference notes) — useful for grounding prompt design and, later, for eval datasets (`agents-cli eval`). See `aci-bench-corpus/README.txt` for its own provenance/license notes.

## Common gotchas

- If `agents-cli` isn't found after `uv tool install`, make sure `~/.local/bin` (or the uv tools bin dir) is on your `PATH`.
- `.env` files are git-ignored on purpose — never commit real project IDs/secrets; use `.env.example` as the template.
- Model 404s are almost always a `GOOGLE_CLOUD_LOCATION` problem (try `global`), not a wrong model name.
- Both services currently have `--deployment-target none` — deploying requires `agents-cli scaffold enhance . --deployment-target cloud_run` first (the `deploy-cloud-run` skill handles this for you).
