# Security Policy

## Supported surfaces

- **PRISM public GitHub Pages edition:** demonstration/browser-local processing only. Do not upload confidential, regulated or personal enterprise data.
- **PRISM Enterprise runtime:** security-hardened server boundary under `enterprise/`; production use requires the deployment controls documented in `docs/enterprise_hosting.md`.

## Reporting a vulnerability

Do not disclose a suspected vulnerability in a public GitHub issue.

Use GitHub's private security reporting / security advisory workflow for this repository when available. If private reporting is unavailable, contact the repository owner privately before sharing technical exploit details.

Include:

- affected component and version/commit;
- impact and attack prerequisites;
- minimal reproduction;
- whether credentials, personal data, tenant isolation or audit integrity may be affected.

## Response principles

Security defects affecting authentication, authorization, tenant isolation, encryption, secret handling or audit integrity block an enterprise release until remediated or formally risk-accepted.

Production secrets must never be committed to source control. Rotate any credential immediately if exposure is suspected.
