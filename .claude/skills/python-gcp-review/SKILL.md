---
name: python-gcp-review
description: Review Python code and GCP architecture for correctness, security, and best-practice adherence. Trigger when the user asks to review code, audit architecture, check something before committing or deploying, or asks "does this follow best practices" for Python services or GCP resources (Cloud Run, Firestore, GCS, Pub/Sub, IAM, Secret Manager, Vertex AI/Gemini, ADK agents). Not for generic review of non-Python/non-GCP code, and not for writing new ADK agent code (that's a separate concern).
---

Review Python code and its GCP architecture together — a change can be clean Python and still violate GCP best practice, or vice versa. Cover both in one pass.

## 1. Determine scope

- If the user names files, review those. Otherwise use `git diff` (staged + unstaged) or the current branch's diff against `main`.
- Read enough surrounding code to understand the call site, not just the changed lines.
- If [docs/usecase.md](docs/usecase.md) exists, read it — it's the architecture source of truth for this project (audio capture → Chirp 3 STT → multi-agent pipeline on Cloud Run → Firestore/GCS → SOAP note + FHIR output). Flag any code that silently diverges from the documented design (wrong region, wrong storage choice, skipped pipeline stage, etc.) as a finding, not just a style note.

## 2. Python checklist

- **Correctness**: off-by-one/edge cases, mutable default args, bare `except:`, swallowed exceptions, incorrect async/await usage, blocking calls inside async functions.
- **Typing & structure**: type hints on public functions, dataclasses/pydantic models over loose dicts for structured data (especially LLM/API payloads), no God-functions doing I/O + parsing + business logic in one block.
- **Error handling**: exceptions are specific and actionable, retries use backoff (not naive `while True`), failures are logged with enough context to debug in production, no silent `pass` on caught exceptions.
- **Security**: no hardcoded credentials/API keys, no `eval`/`exec` on external input, no string-formatted SQL, input validation at system boundaries (API handlers, file uploads), dependencies pinned in `requirements.txt`/`pyproject.toml`.
- **Testing**: new logic has a corresponding test; tests exercise real behavior, not over-mocked internals.
- **Style**: PEP 8, meaningful names, no dead code or commented-out blocks left behind.

## 3. GCP checklist

- **IAM**: service accounts scoped to least privilege (no `roles/owner` or `roles/editor` on service accounts), no broad `allUsers`/`allAuthenticatedUsers` bindings unless the endpoint is intentionally public.
- **Secrets**: pulled from Secret Manager (or env vars injected at deploy time), never committed to the repo or hardcoded in source.
- **Cloud Run services**: stateless (no reliance on local disk/memory surviving across requests), sensible `--concurrency`/`--timeout`/`--min-instances`/`--max-instances`, a real health/readiness path, container runs as non-root, image built via multi-stage Dockerfile to keep it slim.
- **Storage**: GCS buckets have a lifecycle policy for staged data (e.g., raw audio) rather than growing unbounded; Firestore data model matches access patterns (avoid hot-document contention, avoid unindexed queries at scale).
- **Messaging**: Pub/Sub consumers are idempotent (at-least-once delivery), dead-letter topics configured for poison messages.
- **Client calls**: GCP SDK calls (Speech-to-Text, Firestore, GCS, Vertex AI/Gemini) use retry/backoff and handle quota/rate-limit errors explicitly rather than letting them bubble up as generic exceptions.
- **Logging & observability**: structured logging (so Cloud Logging can parse it), no PII/PHI in log lines, trace/request IDs threaded through the agent pipeline for debugging multi-agent flows.
- **Region/data residency**: resources default to an appropriate region for this project's data (Indian clinical data — flag if a resource is provisioned outside an India region without justification).
- **Cost**: no obviously unbounded loops calling paid APIs (Gemini, Speech-to-Text) without caps, batching, or caching where reuse is possible.

## 4. Domain-specific (clinical data)

This project processes patient health information (transcripts, SOAP notes, FHIR bundles). Flag as high-severity:
- PHI logged in plaintext (console logs, error messages, trace spans).
- PHI stored without encryption-at-rest guarantees (default GCS/Firestore encryption is fine; flag only if something bypasses it, e.g., writing to local disk and forgetting to clean up).
- Any code path that would send PHI to a third-party API/service not covered by the project's intended GCP-native pipeline.

If the code defines or calls ADK agents and you need deeper API-correctness guidance (tool definitions, callbacks, state management), that's covered by the separate ADK code-pattern skill — mention it if the user needs that level of detail, but still review the surrounding Python/GCP concerns yourself.

## 5. Output

Report findings grouped by severity (Critical / High / Medium / Low), each with:
- `file:line`
- One-sentence description of the defect
- Why it matters (concrete failure scenario, not "best practice says so")
- A specific fix, not just "consider improving"

Skip nitpicks that don't change behavior unless the user asked for a style pass. If nothing meaningful is wrong, say so plainly instead of inventing findings.
