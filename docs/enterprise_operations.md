# PRISM Enterprise Operations — Phase 1–8

The original Phase 1–8 programme is implemented as one governed enterprise runtime: identity/tenancy, authoritative persistence, connectors, workers/cache, privacy/governance, reliability, model-gateway controls and controlled-pilot records. Organisation-specific cloud/vendor activation remains outside source control.

## Runtime topology

```text
Approved client
    ↓
HTTPS ingress / WAF / gateway
    ↓
PRISM Enterprise API
    ├── OIDC / tenant membership / RBAC
    ├── workspace quotas
    ├── connector administration
    ├── governed DATA-* assets and SNAP-* materialisation
    ├── DC-* Decision Cases and Evidence Graph inspection
    ├── retention / deletion administration
    └── governed AI-provider administration
            ↓
       PostgreSQL
            ↑
PRISM Worker(s)
    ├── connector_run
    ├── dataset_materialize
    ├── decision_case_analyze
    ├── retention_purge
    └── deletion_execute
```

The API and workers use the same application image. Workers run `python -m enterprise.worker`.

## Connector execution

The governed connector catalogue includes:

- `rest_https` — HTTPS GET, redirect refusal, explicit host allowlist and bounded JSON rows;
- `postgresql` — allowlisted host with session forced to `default_transaction_read_only=on`;
- `snowflake_sql_api` — SQL pushdown through Snowflake's HTTPS API;
- `databricks_sql` — SQL Statements API with bounded inline results;
- `azure_blob_https` and `gcs_https` — streamed/bounded object reads;
- `s3_presigned_https` — encrypted presigned URL with approved host validation.

REST/cloud adapters can use encrypted bearer credentials or OAuth2 client-credentials with an independently HTTPS/allowlisted token endpoint.

Connector credentials are submitted separately from connector configuration, encrypted with AES-256-GCM, versioned and rotated. Previous connector credentials are revoked when a new version becomes active. Connector configuration rejects credential-like fields to prevent accidental plaintext secret persistence.

A connector run does not persist extracted raw rows by default. It records bounded operational evidence instead: row count, SHA-256 content hash, sampled schema summary, method and run identifiers. This preserves traceability without turning the control plane into an uncontrolled data lake.

Production deployments must set `PRISM_CONNECTOR_ALLOWED_HOSTS` to the exact hosts or approved wildcard subdomains that PRISM may contact.

## P2 governed materialisation

A connector read remains ephemeral unless an authorised user explicitly queues materialisation into a governed `DATA-*` asset.

Each materialisation creates an immutable `SNAP-*` version containing:
- data classification and accountable asset owner;
- bounded rows and encoded byte size;
- SHA-256 content hash;
- sampled schema summary;
- source connector/run provenance;
- immutable version number.

Configured defaults are 1,000 rows and 10 MiB per materialised snapshot. These are application bounds, not warehouse-scale capacity claims.

Raw materialised rows are stored only in the tenant-scoped snapshot record. They are not copied into the durable job result, audit detail or `EVD-DATA-*` evidence payload. PostgreSQL rejects snapshot UPDATE operations; approved retention/deletion may remove snapshots.

P2 Evidence Graph relationships include:

`connector → data_asset → data_snapshot → evidence → ai_team_run → decision_case → decision`

Snapshot retention recalculates `latest_snapshot_id` so a data asset never points to an expired snapshot.

## P2 AI Control Plane

A Decision Case starts from a business question rather than manual agent selection. The deterministic P2 Control Plane routes the case across the relevant subset of:

- Data Team;
- Analytics Team;
- Data Science Team;
- Strategy Team;
- Governance Team.

Evidence selection is limited to the creator's authorised classification. Explicitly pinned evidence remains pinned across reruns; otherwise reruns can discover newly created evidence.

Each team run stores evidence IDs, deterministic method, limitations and a claim boundary. Team output may organise and interpret cited PRISM evidence but must not invent independent facts. If no traceable evidence is available, the case ends as `insufficient_evidence` and is not reviewable.

The Governance Team verifies that specialist team runs retain evidence links. Material or strategy-oriented cases become `pending_human_review`; a Manager/Admin must approve the case before it can be promoted into the existing `DEC-*` human Decision Register.

P2 does not call an external AI provider and does not execute operational business actions. The P1 provider registry remains the future controlled egress boundary.

## Durable jobs and workers

`job_records` is the durable operational queue. PostgreSQL workers claim work using `FOR UPDATE SKIP LOCKED`, establish a lease, increment attempts and retry failed work with bounded exponential backoff.

The job table is deliberately a control-plane table rather than a tenant RLS business table because workers must claim jobs across tenants. Its payload contains operation identifiers and bounded parameters only; credentials remain in encrypted tenant-scoped stores.

Connector-run state mirrors the durable job state:

- `queued` → awaiting worker claim;
- `running` → leased;
- `retrying` → retryable attempt failed;
- `succeeded` → metadata/evidence persisted;
- `failed` → retry budget exhausted.

## Workspace quotas

P1 uses database-backed usage buckets rather than process-local counters so limits remain coherent across multiple API replicas.

Default controls:

- API writes: 120 per workspace per minute.
- Durable jobs: 1,000 per workspace per day.

A rejected request returns HTTP 429 plus a `Retry-After` value. Production ingress should add coarse network-level abuse protection in addition to these authenticated workspace controls.

## Observability and SLOs

The enterprise API exposes Prometheus metrics at `/metrics`. In production this endpoint is protected by `X-PRISM-Metrics-Token`.

Current metrics include:

- HTTP request totals by route/status;
- HTTP latency histograms;
- terminal job outcomes;
- connector-run outcomes;
- governed materialisation outcomes;
- Decision Case outcomes.

Structured application logs include a request correlation ID, method, route, status and duration without request bodies or connector credentials.

Initial P1 objectives:

- availability: 99.9%;
- control-plane API p95 latency: <750 ms;
- database recovery-point objective: <=15 minutes in production;
- recovery-time objective: <=4 hours.

The repository does not claim those objectives are achieved in production until a real staging/production environment is measured.

## Phase 5 privacy/compliance controls

The enterprise API now persists Processing Activity/ROPA records, DPIAs, DPAs, residency policies, incidents and legal holds. Restricted data assets require a processing activity and approved DPIA before materialisation. Active residency policies gate data-asset regions/classifications. Connectors explicitly marked as external processors require an active DPA record. Active legal holds override retention deletion.

Encryption key rotation uses a versioned AES keyring. Historical key versions remain available during controlled re-encryption, and the Admin rotation endpoint rewrites connector/provider ciphertext to the configured current key version with an audit event.

## Backup and disaster recovery

See [disaster_recovery.md](disaster_recovery.md).

The repository provides a checksum-verified PostgreSQL logical backup/restore path and an automated PostgreSQL 17 restore drill. Production must additionally use managed encrypted automated backups and point-in-time recovery/WAL retention sufficient for the RPO.

## Retention and deletion

Admin users can create workspace retention policies for governed analytical record classes and queue retention purges through the durable worker.

Deletion is intentionally two-stage:

1. Manager creates a reasoned deletion request.
2. Admin approves the request, which queues execution.

Supported targets include individual evidence, connectors (including credentials/run metadata), P2 data assets, P2 Decision Cases, and workspace analytical records. Completion is written to the tamper-evident audit chain. Audit history itself is not silently removed by analytical-record deletion.

## AI-provider governance

Provider configurations remain disabled by default. Provider enablement requires:

- provider host in `PRISM_AI_PROVIDER_ALLOWED_HOSTS`;
- encrypted provider credential;
- explicit approved purpose;
- allowed data classifications;
- recorded acknowledgement of provider retention/training terms.

No provider API key is exposed to the public browser application.

The model-enabled gateway is now implemented. A registered model still cannot be enabled without a passing evaluation and an enabled approved provider. Runtime requests enforce data-class ceilings, input/output bounds, injection/redaction checks, valid supplied `EVD-*` citations, causal-status validation, AI-call auditing and human review for Decision Case synthesis.

## Phase 8 controlled pilot

The pilot framework stores bounded organisation/user/data-domain scope, security-review/UAT gates, success criteria, evidence-backed measurements and UAT findings. Readiness refuses completion if security/UAT is not passed, blocking findings remain, or required success measurements are missing. A real organisation/pilot is never inferred from the presence of these controls.

## Browser and staging acceptance

The public GitHub Pages surface has a Playwright/Chromium gate for desktop and mobile navigation, serious/critical axe accessibility findings and bounded initial-load smoke thresholds.

A bounded staging load utility is available:

```bash
python scripts/load_smoke.py \
  --url https://staging.example.com/health/live \
  --requests 500 \
  --concurrency 25 \
  --min-availability 0.999 \
  --max-p95-ms 750
```

Do not run load tests against third-party systems or production infrastructure without explicit operational approval.

## Production activations outside source control

P1 code does not provision a cloud account or organisation-specific services. Before confidential enterprise traffic, operations still must configure:

- approved private/cloud runtime and HTTPS ingress;
- managed PostgreSQL with PITR/backups and encrypted storage;
- approved OIDC provider;
- secret/KMS injection for audit, encryption and metrics keys;
- exact connector and AI-provider egress allowlists;
- Prometheus/metrics scraping and alert rules;
- central log collection with retention/access policy;
- ingress/network-level rate limiting;
- scheduled backup retention and quarterly recovery exercises;
- an approved scheduler or operations cadence for recurring retention jobs;
- the GitHub `main` ruleset documented in `repository_controls.md`;
- a measured staging load test before production scale claims.

These are environment activations, not hidden application capabilities.
