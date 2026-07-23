# Production-readiness foundation

## Capabilities in v0.2.0

- Optional access-code authentication controlled through deployment secrets.
- Demo mode with a deterministic product-order dataset.
- Central version management and runtime settings.
- Structured logging and privacy-conscious audit events.
- Optional Sentry integration through `SENTRY_DSN`.
- Dependabot, pre-commit checks, pull-request standards, and generated release notes.

## Authentication boundary

The access-code gate is suitable for demonstrations and restricted prototypes. It is not a replacement for enterprise identity. A commercial multi-user release should use an external identity provider with OAuth/OIDC, user roles, session expiry, and server-side authorisation.

## Audit boundary

The current audit file is stored at `logs/audit.jsonl`. Streamlit Community Cloud storage is ephemeral, so events are not guaranteed to persist across restarts. A later release should write audit events to PostgreSQL or a managed logging service.

## Error reporting

Set `SENTRY_DSN` in deployment secrets to enable Sentry. Exception configuration must be reviewed before processing confidential data.
