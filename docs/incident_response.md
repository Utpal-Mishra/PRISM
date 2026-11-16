# PRISM Enterprise Incident Response

This runbook supports the Phase 5/6 incident controls implemented in the enterprise API.

## Severity

- **SEV1:** confirmed material confidentiality/integrity breach, widespread outage, or loss of authoritative enterprise data.
- **SEV2:** major tenant/workspace impact, repeated failed security control, or extended service degradation.
- **SEV3:** contained functional degradation with a workaround.
- **SEV4:** low-impact defect or operational anomaly.

## Immediate procedure

1. Open an `INC-*` record in PRISM with severity, category, owner and factual summary.
2. Preserve relevant logs, audit-chain records and infrastructure evidence; do not copy secrets into the incident record.
3. Contain the affected connector/provider/workspace/service where technically possible.
4. Determine whether personal data, regulated data or another notification obligation may be involved.
5. Update the incident to `contained` only when the active impact has stopped.
6. Document remediation, validation and residual risk.
7. Update the incident to `resolved` only after evidence confirms recovery.
8. Create follow-up Decision/Governance records for material corrective actions.

## Operational targets

The default configuration targets acknowledgement/ownership within 30 minutes and resolution within 24 hours for incidents that can reasonably meet that target. Organisation-specific incident SLAs override these defaults.

## Evidence handling

Incident records are governance metadata, not a dump location. Credentials, raw access tokens, full personal datasets and private keys must not be placed in incident payloads. Reference governed evidence/audit IDs instead.

## External obligations

Whether a regulator, customer, data subject, insurer or other party must be notified depends on the actual incident and the organisation's legal/compliance obligations. PRISM records `notification_required` but does not make the legal determination automatically.
