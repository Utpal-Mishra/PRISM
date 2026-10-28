# PRISM Enterprise hosting boundary

PRISM has two intentionally separate deployment surfaces.

## Public demonstration

The repository-root GitHub Pages application is the public/browser-local product demonstration. It uses synthetic data by default and must **not** be treated as the confidential enterprise runtime.

Do not use the public deployment for regulated, confidential or personal enterprise datasets.

## Enterprise runtime

The enterprise runtime is served from `enterprise.api:app` and is packaged by `Dockerfile.enterprise`.

Production requirements:

- approved private/cloud hosting rather than GitHub Pages;
- PostgreSQL using `PRISM_DATABASE_URL`;
- OIDC/OAuth identity using `PRISM_OIDC_ISSUER` and `PRISM_OIDC_AUDIENCE`;
- HTTPS terminated by an approved ingress/load balancer;
- secrets injected from an approved secrets manager rather than files or source control;
- encryption and audit keys with controlled rotation/versioning;
- database backups, restore testing and managed encryption at rest;
- migration execution as a controlled deployment step: `alembic upgrade head`;
- one or more `python -m enterprise.worker` worker processes;
- explicit connector/AI-provider egress allowlists;
- protected Prometheus scraping via `PRISM_METRICS_TOKEN`;
- managed database PITR/backups plus tested restore procedures.

The service refuses production configuration that lacks PostgreSQL, OIDC, a strong audit HMAC key or a valid AES-256 field-encryption key.

## Local enterprise development

Generate local keys:

```bash
python scripts/generate_enterprise_secrets.py
```

Set those values and a PostgreSQL password in your shell, then:

```bash
docker compose -f compose.enterprise.yml up -d postgres
docker compose -f compose.enterprise.yml run --rm api alembic upgrade head
docker compose -f compose.enterprise.yml up api
```

Development header authentication is permitted only when `PRISM_ALLOW_DEV_AUTH=true` and the environment is not production. Production configuration rejects that setting.

## P1 operations

The API and worker use the same container image. Durable work is stored in PostgreSQL, so workers can be horizontally replicated without a separate message broker for the current P1 workload.

Before production deployment, set the P1 environment controls documented in `.env.enterprise.example`, especially connector allowlists, metrics token, quotas and SLO targets.

Operational runbooks:
- [Enterprise operations](enterprise_operations.md)
- [Disaster recovery](disaster_recovery.md)

The repository provides an executable backup/restore drill. Production still requires the managed database provider's encrypted automated backups/PITR, monitoring and alerting.
