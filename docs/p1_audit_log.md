# PRISM P1 Enterprise Scale & Reliability Audit Log

Date: 2026-10-28  
Scope: private project implementation record for P1 application-side enterprise scale and reliability controls.

## Decision Log

- **DEC-P1-001 — PostgreSQL-backed durable queue.** Use the existing enterprise PostgreSQL control plane for P1 jobs rather than adding Redis/Celery in this stage. Method: minimise operational dependencies while preserving leases, retries and multi-worker claiming. Revisit when queue volume or scheduling complexity justifies a dedicated broker.
- **DEC-P1-002 — Operational queue/counters are not tenant-RLS business tables.** Workers must claim jobs across tenants and quota counters must aggregate atomically. Payloads are restricted to IDs/bounded operation parameters; credentials/raw datasets stay in tenant-scoped encrypted/governed stores.
- **DEC-P1-003 — Raw connector rows are not persisted by default.** P1 connector execution emits run metadata, schema summary and a content hash as evidence. This reduces uncontrolled data replication and keeps storage expansion a deliberate later decision.
- **DEC-P1-004 — Connector and AI-provider egress requires deployment allowlists.** Application-supplied endpoints alone are insufficient for enterprise network trust.
- **DEC-P1-005 — Deletion uses two-person-role workflow semantics.** Manager requests; Admin approves/queues. This is application role separation even when a small deployment may map both roles to the same human.
- **DEC-P1-006 — AI providers remain disabled by default.** P1 adds governed provider registration/credentials/policy only; live AI-team calls belong to a later evidence-grounded orchestration stage.

## System Log

- **SYS-P1-001** Added `enterprise.worker` and a worker service in `compose.enterprise.yml`.
- **SYS-P1-002** Added Prometheus metrics for API requests/latency, jobs and connector outcomes.
- **SYS-P1-003** Added shared request correlation IDs across observability/security middleware.
- **SYS-P1-004** Added P1 environment controls for jobs, quotas, connector egress, metrics/SLOs, retention and AI-provider egress.
- **SYS-P1-005** Enterprise runtime version advanced to `0.2.0-p1`.

## Architecture Log

- **ARC-P1-001** Durable job lifecycle: queued → running/leased → retrying or succeeded/failed.
- **ARC-P1-002** PostgreSQL worker claims use `FOR UPDATE SKIP LOCKED` to support concurrent workers.
- **ARC-P1-003** Business/configuration records remain tenant/workspace scoped; operational queue and usage buckets are control-plane records.
- **ARC-P1-004** Connector execution boundary is server-only; the public browser app receives no enterprise connector credentials.
- **ARC-P1-005** API and worker share one container image but run separate processes.

## Automation Log

- **AUT-P1-001** Added automated PostgreSQL 17 disaster-recovery restore drill.
- **AUT-P1-002** Added durable background execution for connector runs, retention purges and approved deletions.
- **AUT-P1-003** Added recurring Browser E2E workflow including npm audit and accessibility checks.
- **AUT-P1-004** Added bounded staging load-smoke utility; production/staging execution remains an explicitly authorised operations action.

## Data & Integration Log

- **DAT-P1-001** Added governed `rest_https` connector: HTTPS GET, no redirects, explicit host allowlist, bounded JSON rows.
- **DAT-P1-002** Added governed `postgresql` connector: allowlisted host, encrypted credential, read-only transaction default, bounded row fetch.
- **DAT-P1-003** Connector runs produce `EVD-CONN-*` evidence containing row count, SHA-256 content hash, schema summary and method metadata.
- **DAT-P1-004** Added AI-provider configuration/credential store with egress/data-policy validation before enablement.

## Security Log

- **SEC-P1-001** Connector credentials encrypted/versioned; previous version revoked on rotation.
- **SEC-P1-002** Connector configuration rejects secret-like plaintext keys.
- **SEC-P1-003** AI-provider credentials use encrypted enterprise secret storage; prior provider credential is replaced on rotation.
- **SEC-P1-004** Metrics endpoint supports token authentication; production configuration requires a strong metrics token.
- **SEC-P1-005** Workspace quotas use database-backed atomic counters.
- **SEC-P1-006** Browser acceptance gate exposed and remediated accessible-name, scroll-region keyboard and closed-drawer focus defects.

## Product / Feature Log

- **PRO-P1-001** Enterprise connector administration and queued execution API.
- **PRO-P1-002** Job status API.
- **PRO-P1-003** Retention policy API and queued execution.
- **PRO-P1-004** Manager deletion request + Admin approval/execution API.
- **PRO-P1-005** AI-provider registration, credential rotation, enable/disable administration.
- **PRO-P1-006** Public app version label aligned to v1.8.0; enterprise service version aligned to P1.

## Risk & Assumption Log

- **RSK-P1-001 — Production infrastructure not provisioned.** Impact: repository controls do not prove production availability/RPO/RTO. Mitigation: explicit environment activation list, DR runbook, staging load tool. Status: open/environment.
- **RSK-P1-002 — PostgreSQL queue is appropriate only for current P1 scale.** Evidence: queue design is intentionally minimal. Mitigation: monitor backlog/claim latency; evaluate dedicated broker at higher scale. Status: accepted for P1.
- **RSK-P1-003 — Host allowlists do not replace network egress controls.** Mitigation: production ingress/network architecture must also restrict egress/DNS as appropriate. Status: open/environment.
- **RSK-P1-004 — Raw connector rows are not persisted.** Impact: downstream enterprise analytics requires a later governed data materialisation path or immediate processing pipeline. Mitigation: P1 records trace/evidence only; expand deliberately later. Status: known product boundary.
- **RSK-P1-005 — Retention jobs require an external recurring scheduler/cadence for automatic policy enforcement.** Mitigation: queueable policies are implemented; production scheduler remains environment activation. Status: open/environment.
- **RSK-P1-006 — GitHub main branch protection is still an administrator setting.** Mitigation: issue #37 and `docs/repository_controls.md`. Status: open/release blocker for enterprise production.

## Experiment / Validation Log

- **EXP-P1-001** P1 migration initially failed because Alembic revision name exceeded its version column; shortened to `0002_scale_reliability`. Result: PostgreSQL migration/DR workflow passed.
- **EXP-P1-002** Security scan flagged credential-like test literals; fixtures were changed rather than weakening secret detection.
- **EXP-P1-003** Browser E2E/axe found serious accessibility defects in the existing public shell; accessible naming, scroll focus and mobile drawer focus isolation were corrected.
- **EXP-P1-004** Connector retry regression added to verify retrying vs terminal failed run state.
- **EXP-P1-005** Dependency/security gates continue to use CodeQL, pip-audit, Bandit, detect-secrets and SBOM controls from P0.

## External Evidence / Operational Evidence Log

- **EXT-P1-001** PostgreSQL 17 automated migration/bootstrap/backup/restore drill succeeded after migration-ID repair.
- **EXT-P1-002** P1 security runs have demonstrated clean CodeQL, dependency audit and Bandit stages; final merge requires all branch-head gates together.
- **EXT-P1-003** Browser gate uses Chromium with axe and npm audit; final merge requires a green branch-head browser run.

## Recommendation Log

- **REC-P1-001** Do not introduce a dedicated broker until measured queue pressure requires it.
- **REC-P1-002** Use managed PostgreSQL PITR as the primary recovery mechanism and logical dumps as a portable secondary layer.
- **REC-P1-003** Keep future AI-team calls behind the P1 provider-governance boundary; never place provider API keys in GitHub Pages.
- **REC-P1-004** Before production, execute the load smoke against a real staging environment and capture achieved p95/availability rather than treating target values as measured facts.

## Expansion Log

- **EXPAN-P1-001** Future connector types can extend the server adapter model without changing the credential/tenant/job boundary.
- **EXPAN-P1-002** Higher-volume execution can move from PostgreSQL queue to a managed broker while retaining the P1 job state contract.
- **EXPAN-P1-003** AI Teams can build on the provider registry, Evidence Graph and durable job runtime after P1 production activation.
