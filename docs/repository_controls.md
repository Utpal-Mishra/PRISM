# PRISM repository security controls

These repository controls are required before PRISM Enterprise is approved for confidential production data.

## Implemented in source control

- `CODEOWNERS` assigns ownership for the repository, enterprise runtime, workflows and documentation.
- CI and release workflows pin third-party GitHub Actions to full immutable commit SHAs.
- Security workflow runs CodeQL for Python and JavaScript/TypeScript.
- Supply-chain workflow runs `pip-audit`, Bandit and committed-secret detection.
- A CycloneDX SBOM is generated as a workflow artifact.
- `SECURITY.md` defines the private vulnerability-reporting boundary.
- Enterprise secrets, local databases, private keys and generated SBOM files are excluded from Git.

## Required GitHub repository setting — release blocker

The following control must be activated in **Settings → Rules → Rulesets** (or equivalent branch-protection controls) for the `main` branch. It is a platform configuration and is not represented by an application code commit.

Recommended ruleset name: **PRISM Enterprise Main Protection**

Target:
- branch: `main`
- enforcement: Active

Required rules:
- require a pull request before merging;
- require at least one approving review for multi-maintainer operation;
- require Code Owner review when another maintainer is available;
- dismiss stale approvals when new commits are pushed;
- require all review conversations to be resolved;
- require successful **CI / quality**;
- require successful **Security / CodeQL (python)**;
- require successful **Security / CodeQL (javascript-typescript)**;
- require successful **Security / Supply chain and Python security**;
- block force pushes;
- block branch deletion;
- restrict bypass to explicitly authorised repository administrators;
- require signed commits where the organisation's signing workflow supports it.

For a single-maintainer personal repository, review-count/Code Owner approval can temporarily be zero because self-approval is not a meaningful control. The required CI and Security checks, force-push/delete restrictions and bypass controls should still be enforced before enterprise deployment. When a second maintainer is added, increase required approvals to at least one and enable Code Owner approval.

## Additional GitHub security settings

Before enterprise release, enable where available:
- private vulnerability reporting;
- Dependabot alerts/security updates;
- secret scanning and push protection;
- default workflow token permission = read-only, granting write permission only per job when required;
- Actions policy that permits only approved actions and reusable workflows.

## Release rule

A commit may be used for the public GitHub Pages demo without these enterprise controls, but **PRISM Enterprise must not process confidential, regulated or personal organisational data until this repository rule is active and the required production infrastructure is configured**.
