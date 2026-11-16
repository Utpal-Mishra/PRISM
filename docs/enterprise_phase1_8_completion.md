# PRISM Enterprise Phase 1–8 Completion

Date: 2026-11-16

This document maps the original Enterprise Phase 1–8 programme to the implementation now present in the PRISM repository.

A capability is marked **integrated** when its application/runtime contract, persistence, authorization and tests exist in source control. A capability is marked **activation required** when it depends on an organisation-specific identity provider, cloud account, external data platform, KMS/vault, monitoring stack or pilot organisation that cannot be provisioned generically from the repository.

## Phase 1 — Identity + tenants + backend

**Integrated**

- FastAPI enterprise runtime.
- OIDC/JWT validation with issuer/audience/time/sub checks.
- Authoritative enterprise users, tenants, workspaces and memberships.
- Viewer / Analyst / Manager / Admin server-side authorization.
- Public / Internal / Confidential / Restricted data-clearance hierarchy.
- PostgreSQL production requirement and Alembic migrations.
- PostgreSQL Row Level Security on tenant-scoped enterprise tables.
- AES-256-GCM field encryption.
- Versioned encryption keyring and audited workspace ciphertext re-encryption.
- Non-root enterprise container/runtime.

**Activation required**

- Organisation-selected OIDC/SSO provider.
- Managed PostgreSQL.
- HTTPS ingress/WAF/DNS.
- KMS/secret-manager delivery of current and historical key versions.

## Phase 2 — Evidence persistence migration

**Integrated**

The original browser-oriented business chain now has authoritative server-side persistence and version history for:

`Dataset Registry → Metric Registry → Evidence → Strategy → Decision → Outcome → Governance`

- `DS-*` dataset registry records.
- `MET-*` metric registry records.
- append-only `EVD-*` evidence.
- `STR-*` strategy records.
- `DEC-*` decisions, including `DC-* → DEC-*` promotion.
- `OUT-*` outcome records.
- `GOV-*` governance records.
- immutable `ArtifactVersion` history with content hashes and change notes.
- tenant/workspace authorization and classification checks.
- version-history API.

The public GitHub Pages edition remains browser-local by design. The enterprise API is the authoritative organisational persistence boundary.

## Phase 3 — Real connectors

**Integrated adapters**

- PostgreSQL read-only connector.
- HTTPS REST connector.
- Snowflake SQL API.
- Databricks SQL Statements API.
- Azure Blob-compatible HTTPS object reads.
- Google Cloud Storage-compatible HTTPS object reads.
- governed presigned-S3 HTTPS object reads.
- OAuth2 client-credentials token acquisition.
- encrypted/versioned connector credentials.
- host allowlists, HTTPS-only network boundary and redirect refusal.
- service-account/client-secret material stays in encrypted credential records.
- optional DPA gate for connectors acting as external processors.
- source/run provenance and connector evidence.

**Activation required**

Real credentials/endpoints for Snowflake, Databricks, Azure, GCP, S3 or other organisation systems.

## Phase 4 — Compute + scale

**Integrated**

- PostgreSQL durable job queue.
- separate worker runtime.
- leases, retries and retry exhaustion.
- `FOR UPDATE SKIP LOCKED` worker claims.
- workspace concurrent-job ceiling protected by PostgreSQL advisory lock.
- database-backed API/job/AI quotas.
- tenant-scoped bounded query cache with TTL.
- cache-aware materialisation provenance.
- SQL query pushdown for PostgreSQL/Snowflake/Databricks operations.
- streamed CSV cloud-object ingestion.
- byte-bounded JSON object ingestion.
- explicit governed `DATA-*` / immutable `SNAP-*` materialisation.
- configurable row/byte ceilings.

**Scale boundary**

PRISM's control-plane database is not presented as a replacement for a warehouse/lakehouse. Very large datasets should remain in approved external platforms with query pushdown or future warehouse/object-storage materialisation.

## Phase 5 — Security / governance / privacy

**Integrated**

- tamper-evident HMAC audit chain.
- append-only database audit protection.
- data classification and clearance.
- retention and deletion workflows.
- legal holds that block policy deletion.
- Processing Activity / ROPA records.
- DPIA records.
- DPA/counterparty records.
- residency policies.
- Restricted-data handling note.
- Restricted materialisation requires a linked active Processing Activity and approved DPIA.
- residency policies gate governed data-asset creation.
- external-processor connectors can require an active DPA.
- incident records and status lifecycle.
- AES key-version history and audited re-encryption.
- human approval for material Decision Cases.

**Activation required**

Organisation-specific legal determinations, DPO approval, actual DPA contracts, residency regions, KMS policies and incident contacts.

## Phase 6 — Reliability

**Integrated**

- Prometheus request, latency, job, connector, materialisation, Decision Case, AI-gateway and pilot metrics.
- structured request logs and correlation IDs.
- SLO targets.
- checksum-verified PostgreSQL logical backup/restore.
- automated PostgreSQL 17 restore drill.
- RPO/RTO targets.
- bounded staging load-smoke tool.
- recurring failure-drill workflow.
- worker lease-recovery drill.
- legal-hold/retention drill.
- cache-expiry drill.
- AI prompt-injection/redaction drill.
- Prometheus alert rules for 5xx rate, p95 latency, worker/connector/materialisation/Decision Case failure bursts.
- incident-response runbook.

**Activation required**

Production metrics scraping, alert routing, managed PITR/WAL, real staging load measurements and organisation-run recovery exercises.

## Phase 7 — Governed AI runtime

**Integrated**

- governed provider registry and encrypted credentials.
- provider egress allowlist and data-class policy.
- governed model registry.
- explicit intended use, risk classification, human-oversight statement and transparency notice.
- model enablement requires a passing evaluation.
- evaluation records with dataset version, metrics and thresholds.
- live `openai_compatible` provider gateway.
- daily AI call quota.
- prompt-size/output-size limits.
- prompt-injection detection across user question **and retrieved evidence context**.
- common secret/email redaction before provider transmission.
- evidence IDs are validated before transmission.
- model output must return valid supplied `EVD-*` citations.
- causal-status validation.
- prompt body is not stored in the AI audit; a SHA-256 prompt hash and operational metadata are stored instead.
- token usage, latency, redaction count, injection flag and output status are audited.
- Decision Case AI synthesis resets human review and cannot bypass Manager/Admin approval.

**Activation required**

An approved model/provider configuration, real provider credential, approved evaluation dataset/results and organisation-specific AI governance determination.

## Phase 8 — Enterprise pilot

**Integrated pilot-control framework**

- `PILOT-*` records.
- organisation label, owner, date window and user limit.
- bounded data-domain and classification scope.
- security-review and UAT gates.
- measurable success criteria.
- evidence-backed pilot measurements.
- `UAT-*` findings.
- high/critical UAT findings fail the UAT gate.
- readiness endpoint verifies security review, UAT, blocking findings and success-criterion measurements.
- pilot lifecycle metrics.

**Activation required**

A real controlled organisation, named authorised users, approved data domains, completed security review/UAT and measured pilot outcomes.

## Public application design update

The GitHub Pages application now uses a restrained enterprise palette:

| Token | Value |
| --- | --- |
| Canvas | `#0B1220` |
| Sidebar | `#0F172A` |
| Surface | `#111827` |
| Elevated surface | `#172033` |
| Border | `#263247` |
| Primary text | `#F8FAFC` |
| Muted text | `#94A3B8` |
| Primary accent | `#60A5FA` |
| Strong accent | `#3B82F6` |
| Action accent | `#2563EB` |
| Soft highlight | `#93C5FD` |
| Success | `#2DD4BF` |
| Warning | `#F59E0B` |
| Danger | `#F87171` |

The old green/lime-dominant visual identity is no longer the primary UI language.

## Remaining external release blockers

These are not missing application features:

1. activate the documented GitHub `main` protection/ruleset;
2. provision the chosen enterprise cloud/private runtime;
3. connect a real OIDC provider;
4. connect managed PostgreSQL/PITR;
5. inject keys/secrets from the approved secret/KMS platform;
6. activate organisation-specific connector/provider endpoints and allowlists;
7. connect Prometheus/log/alert infrastructure;
8. execute a real staging performance/recovery exercise;
9. nominate and execute the Phase 8 pilot with a real organisation.

Until those environment-specific actions are completed, the public GitHub Pages application remains a demonstration surface and the repository enterprise runtime remains deployment-ready rather than a live confidential customer service.
