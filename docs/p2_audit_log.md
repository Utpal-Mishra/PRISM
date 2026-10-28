# PRISM P2 Governed Data & AI Control Plane Audit Log

Date: 2026-10-28  
Scope: private project implementation record for the P2 governed data materialisation and AI Control Plane foundation.

## Decision Log

- **DEC-P2-001 — Explicit materialisation only.** Connector reads remain ephemeral unless an authorised user creates a `DATA-*` asset and queues a materialisation. Rationale: avoid silently copying enterprise source data.
- **DEC-P2-002 — Bounded PostgreSQL snapshots for P2.** P2 uses small governed `SNAP-*` JSON snapshots (default 1,000 rows / 10 MiB) rather than claiming warehouse-scale storage. Expansion to warehouse/object storage is deferred until measured need.
- **DEC-P2-003 — Immutable snapshot versions.** Snapshot UPDATE is rejected by PostgreSQL; new source state creates a new version. Retention/deletion may remove snapshots according to policy.
- **DEC-P2-004 — Deterministic Control Plane before live LLM orchestration.** P2 proves evidence routing, team boundaries, Decision Cases and human review without external model calls.
- **DEC-P2-005 — Dynamic team routing.** Users ask a business question; PRISM selects relevant core teams rather than forcing manual agent selection.
- **DEC-P2-006 — Decision Case is not a business decision.** `DC-*` is an evidence-grounded investigation package. Only reviewed cases can be promoted into a separate `DEC-*` human decision.
- **DEC-P2-007 — Clearance-bound evidence.** A case may only consume evidence within the creator's data-clearance ceiling.
- **DEC-P2-008 — Relevance required unless evidence is explicitly pinned.** Unpinned cases with zero lexical evidence relevance refuse rather than falling back to arbitrary workspace evidence.
- **DEC-P2-009 — Restricted data requires handling basis.** Restricted data assets require a recorded handling/lawful-basis note before persistence.

## System Log

- **SYS-P2-001** Enterprise service version advanced to `0.3.0-p2`.
- **SYS-P2-002** Added `enterprise/p2_models.py`, `materialization.py`, `control_plane.py` and `p2_api.py`.
- **SYS-P2-003** Added durable job types `dataset_materialize` and `decision_case_analyze`.
- **SYS-P2-004** Added materialisation and Decision Case Prometheus counters.
- **SYS-P2-005** Added P2 configuration limits for materialised rows/bytes and Decision Case evidence count.

## Architecture Log

- **ARC-P2-001** Governed data chain: Connector → DATA-* → SNAP-* → EVD-DATA-*.
- **ARC-P2-002** Evidence Graph chain: Source → Data → EVD-* → AITeamRun → DC-* → DEC-*.
- **ARC-P2-003** First five teams: Data, Analytics, Data Science, Strategy, Governance.
- **ARC-P2-004** Control Plane execution is worker-based, tenant-context scoped and persisted through Decision Cases/team runs.
- **ARC-P2-005** Team output carries cited evidence IDs, deterministic method, limitations and causal guardrails.
- **ARC-P2-006** Materialisation version assignment is serialized with a DataAsset row lock.
- **ARC-P2-007** Decision Case worker execution, rerun, review and promotion are serialized to prevent duplicate/conflicting state transitions.

## Automation Log

- **AUT-P2-001** Materialisation requests queue durable worker jobs with P1 leases/retries.
- **AUT-P2-002** Decision Case analysis queues durable Control Plane jobs.
- **AUT-P2-003** Decision Case reruns replace obsolete team runs and their Evidence Graph edges.
- **AUT-P2-004** Snapshot retention automatically recalculates `latest_snapshot_id`.
- **AUT-P2-005** DR workflow verifies P2 tables and immutable-snapshot trigger after restore.

## Data & Integration Log

- **DAT-P2-001** Added explicit `DATA-*` assets tied to active governed P1 connectors.
- **DAT-P2-002** Added versioned `SNAP-*` rows with classification, schema, size, hash and provenance.
- **DAT-P2-003** Normalises non-JSON-native connector values before materialised JSON storage.
- **DAT-P2-004** `EVD-DATA-*` stores metadata/hash/schema only; raw rows are excluded from evidence.
- **DAT-P2-005** Raw rows are excluded from job results and audit details.
- **DAT-P2-006** Added P2 retention type `data_snapshot`.
- **DAT-P2-007** Added deletion targets for `data_asset` and `decision_case`.

## Product / Feature Log

- **PRO-P2-001** Data Asset create/list APIs.
- **PRO-P2-002** Queue materialisation API plus snapshot metadata/row access.
- **PRO-P2-003** Shared Evidence Graph inspection API.
- **PRO-P2-004** AI team registry API.
- **PRO-P2-005** Decision Case create/list/detail/rerun APIs.
- **PRO-P2-006** Manager/Admin Decision Case review API.
- **PRO-P2-007** Reviewed Decision Case → `DEC-*` promotion API.
- **PRO-P2-008** Explicit insufficient-evidence state and non-reviewable refusal.

## Governance & Security Log

- **SEC-P2-001** All P2 business tables use PostgreSQL RLS under tenant/workspace context.
- **SEC-P2-002** DataSnapshot UPDATE is rejected at the database layer.
- **SEC-P2-003** Snapshot row access is filtered by membership data clearance.
- **SEC-P2-004** Evidence Graph edges carry classification and are filtered before API return.
- **SEC-P2-005** Restricted assets require handling/lawful-basis metadata; audit records only whether it was recorded, not the note content.
- **SEC-P2-006** Decision Cases cannot consume evidence above creator clearance.
- **SEC-P2-007** Human review is required before promotion into a business Decision Record where strategy/materiality requires it.
- **SEC-P2-008** P2 does not expose provider credentials or invoke an external AI service.

## Experiment / Validation Log

- **VAL-P2-001** Initial P2 migration/API schema successfully passed PostgreSQL DR before snapshot immutability was added.
- **VAL-P2-002** First immutability trigger migration failed because a dollar-quote delimiter was malformed; replaced with migration-safe escaped PL/pgSQL body.
- **VAL-P2-003** P2 regression suite validates five-team registry/routing, snapshot bounds/versioning, evidence lineage, classification filtering, insufficient-evidence refusal, rerun replacement and evidence pinning.
- **VAL-P2-004** Added explicit regression that unrelated workspace evidence cannot ground an unpinned Decision Case.
- **VAL-P2-005** DR gate extended to verify P2 tables and immutable trigger after backup/restore.
- **VAL-P2-006** CI contract now asserts P2 modules, migration, refusal/human-review language and durable job types.

## External / Operational Evidence Log

- **EXT-P2-001** PostgreSQL 17 DR workflow passed after the migration-safe trigger repair and P2 table checks.
- **EXT-P2-002** CI and Security gates have passed on intermediate P2 states; final merge requires green gates on the final branch head.
- **EXT-P2-003** Public GitHub Pages UI is intentionally unchanged by P2; browser-local privacy boundary remains intact.

## Risk & Assumption Log

- **RSK-P2-001 — PostgreSQL JSON snapshots are not warehouse scale.** Impact: large datasets/cadences can create storage pressure. Mitigation: strict row/byte limits, retention, future warehouse/object-store materialisation. Status: accepted P2 boundary.
- **RSK-P2-002 — Lexical evidence routing is not semantic reasoning.** Impact: relevant evidence can be missed. Mitigation: explicit evidence pinning and refusal over unsupported fallback; later governed provider/embedding layer. Status: accepted P2 boundary.
- **RSK-P2-003 — External AI providers remain disconnected.** Impact: team synthesis is structured/deterministic rather than generative. Mitigation: intentional until evidence/governance orchestration is validated. Status: planned expansion.
- **RSK-P2-004 — Materialised Restricted data relies on PostgreSQL/storage encryption plus RLS, not per-cell application encryption.** Mitigation: production encrypted storage/KMS, classification controls, strict bounds; consider field/tokenisation/warehouse controls for higher-risk deployments. Status: environment/policy.
- **RSK-P2-005 — Concurrent version/review races.** Mitigation: row locking on snapshot creation, asset deletion, Decision Case worker/rerun/review/promotion. Status: mitigated.
- **RSK-P2-006 — Retention can remove raw snapshot rows while evidence metadata remains.** Intentional: preserve trace/audit metadata without retaining aged raw data. Status: accepted design.
- **RSK-P2-007 — `main` repository protection remains an external GitHub admin setting.** Mitigation: existing repository-controls issue/documentation. Status: open production blocker.

## Recommendation Log

- **REC-P2-001** Prove P2 with real staging workloads before enabling live model-provider orchestration.
- **REC-P2-002** Add a warehouse/object-store materialisation adapter before raising P2 snapshot bounds substantially.
- **REC-P2-003** Keep Decision Cases separate from Decisions; do not allow AI team output to execute operational actions directly.
- **REC-P2-004** For model-enabled P3, require provider responses to cite valid `EVD-*` IDs and pass Governance validation before synthesis is reviewable.
- **REC-P2-005** Introduce semantic retrieval/embedding only as a governed evidence-retrieval improvement, never as a substitute for source/evidence traceability.

## Expansion Log

- **EXP-P2-001** Later core-team specialists can be added under the same team-run/Decision Case contract.
- **EXP-P2-002** Later specialist teams: Database, Finance, Business, Operations, Product, Development and Marketing.
- **EXP-P2-003** P1 AI provider registry is the controlled path for future live model calls.
- **EXP-P2-004** Data materialisation can move to Snowflake/Databricks/BigQuery/Redshift/Fabric/S3/Blob while keeping `DATA-*`, `SNAP-*` metadata and Evidence Graph semantics.
- **EXP-P2-005** Outcome records can later link back to `DC-*` to complete Decision Case → Decision → Outcome → Learning.
