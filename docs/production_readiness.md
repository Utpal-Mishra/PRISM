# PRISM Production Readiness

PRISM is deliberately split into a **public demonstration surface** and an **enterprise runtime**. The public GitHub Pages application remains browser-local and suitable for synthetic/non-confidential demonstrations. Confidential organisational data belongs only in the authenticated enterprise runtime after the deployment controls below are activated.

## Enterprise P0 foundation — implemented in repository

### Identity and access
- OIDC/OAuth Bearer-token verification with issuer, audience, expiry, issued-at and subject validation.
- OIDC discovery/JWKS endpoints are restricted to HTTPS.
- Development-header authentication is disabled by configuration in production.
- Authoritative users and workspace memberships are stored server-side; tenant access is not trusted from arbitrary token claims.
- Central Viewer / Analyst / Manager / Admin role hierarchy.
- Public / Internal / Confidential / Restricted data-clearance hierarchy.
- API endpoints enforce role and classification clearance server-side.

### Tenant isolation and persistence
- PostgreSQL is required in production.
- Tenant and workspace identifiers are carried by governed enterprise records.
- PostgreSQL transaction-local tenant/workspace context is set only after membership verification.
- Row Level Security is enabled and forced on tenant-scoped evidence, strategy, decision, outcome, encrypted-secret and audit tables.
- Alembic migration foundation manages the enterprise schema.

### Audit, encryption and secrets
- Enterprise audit events are persisted server-side.
- Audit events form an HMAC-SHA256 hash chain and can be verified for tampering.
- PostgreSQL rejects UPDATE or DELETE mutations to the audit table.
- Sensitive connector/secret material has an AES-256-GCM field-encryption helper with key versioning.
- Production encryption and audit keys must be injected from deployment secrets; no key is committed to source.
- Enterprise security middleware adds trusted-host enforcement and restrictive response headers.

### Production hosting boundary
- `Dockerfile.enterprise` packages the authenticated FastAPI runtime as a non-root container.
- `compose.enterprise.yml` provides a local PostgreSQL-backed enterprise development path.
- Production configuration fails closed if PostgreSQL, OIDC, audit integrity key or AES-256 key requirements are missing.
- GitHub Pages remains a public demo and is explicitly labelled as unsuitable for confidential, regulated or personal enterprise data.

### Upload and export security
- Browser-demo uploads are bounded by file size, row count, column count and cell length.
- XLS/XLSX sheet dimensions are checked before full JSON expansion.
- CSV parsing enforces bounded row/column/cell limits.
- CSV exports neutralise formula-leading string values before spreadsheet consumption.
- The public page now carries an explicit Content Security Policy and enterprise-data warning.

### Security SDLC
- `CODEOWNERS` and `SECURITY.md` are present.
- CI/release Actions are pinned to immutable commit SHAs.
- CodeQL scans Python and JavaScript/TypeScript.
- `pip-audit` gates Python dependency vulnerabilities.
- Bandit gates Python security findings.
- `detect-secrets` checks committed material.
- CycloneDX SBOM generation is part of the security workflow.
- Enterprise regression tests cover fail-closed production config, role/clearance hierarchy, authoritative workspace membership, encryption round-trip and audit tamper detection.

## Enterprise P1 scale & reliability — implemented in repository

### Governed data integrations
- Added server-side HTTPS REST and PostgreSQL read-only connector adapters.
- Added explicit connector egress allowlists, bounded extraction and redirect refusal.
- Added encrypted/versioned connector credentials with rotation and revocation.
- Added plaintext-secret rejection for connector configuration.
- Connector runs persist metadata/evidence by default rather than raw extracted rows.

### Durable execution and quotas
- Added PostgreSQL-backed durable jobs with leases, retry budgets and `SKIP LOCKED` worker claims.
- Added a separate worker process in the enterprise deployment topology.
- Added database-backed workspace API-write and daily-job quotas with HTTP 429 / Retry-After behaviour.
- Added connector-run retry/terminal state reconciliation.

### Observability and service objectives
- Added Prometheus request, latency, job and connector-run metrics.
- Added structured request logs using shared correlation IDs.
- Added authenticated metrics access and explicit initial availability/latency objectives.
- Added a bounded staging load-smoke utility.

### Recovery and lifecycle
- Added checksum-verified PostgreSQL logical backup and restore scripts.
- Added an automated PostgreSQL 17 migration/bootstrap/backup/restore verification workflow.
- Added workspace retention policies and queued retention execution.
- Added Manager-requested / Admin-approved deletion workflows with audited completion.

### Governed AI-provider boundary
- Added disabled-by-default enterprise AI-provider configurations.
- Added encrypted provider credentials and rotation.
- Added provider-host allowlisting and recorded purpose/data-class/retention-policy requirements before enablement.
- Live AI-team/provider invocation remains a later governed feature rather than an unbounded P1 network call.

### Browser acceptance
- Added Chromium desktop/mobile Playwright acceptance tests.
- Added axe-based serious/critical accessibility gating.
- Added bounded browser-load smoke assertions and npm dependency auditing.
- Remediated public-shell keyboard/focus accessibility issues surfaced by the new tests.

See [enterprise_operations.md](enterprise_operations.md) for the operational model and [disaster_recovery.md](disaster_recovery.md) for recovery controls.

## P0 platform activation still required before enterprise data

The repository cannot activate GitHub branch rules through application source code. Before an enterprise release, activate the `main` ruleset documented in [repository_controls.md](repository_controls.md), including required CI/Security status checks and force-push/deletion restrictions.

A production deployment must also supply:
- approved OIDC provider configuration;
- managed PostgreSQL;
- approved HTTPS ingress;
- audit/encryption secrets from a managed secret store;
- production DNS/trusted-host/origin values;
- controlled Alembic migration execution.

These are environment activations, not missing application features.

## Remaining production activation and later programme

P1 now implements the application-side scale/reliability foundation. A real production environment must still activate managed PITR/backups, metrics/log shipping and alerts, ingress/network limits, organisation-specific connector/provider allowlists, recurring retention scheduling, staged load measurement and the documented GitHub ruleset. Later product stages can build governed AI-team orchestration on top of the P0/P1 control plane.

## Legacy Streamlit boundary

The `app/` and `prism/` packages are retained analytical/reference code. They are not the current GitHub Pages runtime and are not the new PRISM Enterprise API boundary. The retained dependency set is nevertheless scanned and kept compatible with current security fixes so it does not become an unmanaged repository risk.
