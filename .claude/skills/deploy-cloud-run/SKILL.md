---
name: deploy-cloud-run
description: Deploy one of this project's ADK agent services (doctor-service or patient-service) to Google Cloud Run, given the local agent service and the target Cloud Run service name. Trigger when the user says "deploy <service> to cloud run", "deploy the doctor/patient service", or asks to ship one of the services/ projects to Cloud Run. Not for Agent Runtime or GKE deployment, and not for building/reviewing agent code.
---

Deploys one of the two scaffolded agent projects under `services/` (`doctor-service`, `patient-service`) to Cloud Run via `agents-cli deploy`. This wraps `agents-cli` — see `/google-agents-cli-deploy` for the full mechanics if something here doesn't cover the situation.

## 1. Parse the request

You need two things from the user's message (ask if either is missing or ambiguous):
- **Agent service**: which local project to deploy — `services/doctor-service` or `services/patient-service`.
- **Cloud Run service name**: the name the service should have on Cloud Run (passed as `--service-name`). This does not have to match the local directory name.

Also confirm, if not already known from `.env` or prior conversation:
- **GCP project ID** and **region** to deploy into.

Do not guess these — deploying to the wrong project/region is expensive to undo. Ask.

## 2. Check current deployment config

From the agent service directory (`services/<agent-service>/`), run:

```bash
agents-cli info
```

If it shows no deployment target configured (these projects were scaffolded with `--deployment-target none`), you must add Cloud Run support first:

```bash
agents-cli scaffold enhance . --deployment-target cloud_run
```

This generates the Terraform/IAM scaffolding and Cloud Run-specific config. Tell the user this happened — it's a real change to the project, not a no-op.

## 3. Confirm before deploying

**Never run `agents-cli deploy` without explicit human approval** — it builds and pushes a container and creates/updates a live Cloud Run service. Before running it, summarize exactly what will happen:

- Which local project (`services/doctor-service` or `services/patient-service`)
- Target Cloud Run service name
- GCP project + region
- Whether this is a new service or an update to an existing one (`agents-cli deploy --list` or `gcloud run services describe <name> --region <region>` can confirm)

Wait for the user to say go before proceeding.

## 4. Deploy

From inside `services/<agent-service>/`:

```bash
agents-cli deploy \
  --service-name <cloud-run-service-name> \
  --project <gcp-project-id> \
  --region <region> \
  --no-confirm-project
```

Notes:
- Add `--secrets ENV=SECRET_ID` for any API keys/credentials instead of putting them in `--update-env-vars`.
- Add `--service-account <sa-email>` if the project's Terraform-created `app_sa` should be used — `agents-cli deploy` does not pick it up automatically.
- Default sizing is `--cpu 1 --memory 4Gi --concurrency 8 --min-instances 1 --max-instances 10`; only override these if the user asks or load-testing shows a need (see `/google-agents-cli-deploy` "Sizing a deployment").
- If the deploy hangs past a couple minutes, that's normal — Cloud Run builds can take a few minutes. Don't cancel and retry reflexively.

## 5. Verify

After a successful deploy, the command prints the service URL. Sanity-check it:

```bash
agents-cli run --url <service-url> --mode adk "hello"
```

Cloud Run services deploy with `--no-allow-unauthenticated` by default — if the smoke test gets a 403, that's expected; use an identity token:

```bash
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" <service-url>/...
```

Report the final service URL and whether the smoke test passed.

## Troubleshooting

Common failures and fixes are in `/google-agents-cli-deploy`'s troubleshooting table (403s, secret access, cold starts, Cloud Run 503s). Check there before improvising a fix.
