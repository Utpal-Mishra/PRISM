# PRISM Enterprise disaster recovery

## Recovery objectives

Initial P1/P2 targets:

- **Availability SLO:** 99.9% for the authenticated enterprise API.
- **Latency SLO:** p95 API latency below 750 ms for non-analytical control-plane requests.
- **Production RPO target:** 15 minutes or better.
- **Production RTO target:** 4 hours or better.

The logical backup scripts in this repository are a portable secondary recovery mechanism. A production managed PostgreSQL service must additionally enable encrypted automated backups and point-in-time recovery / WAL retention sufficient to meet the RPO target.

## Backup layers

1. Managed database continuous/PITR backup — primary recovery path.
2. Scheduled encrypted logical backup — independent portable recovery artifact.
3. Schema migrations in source control — reconstruction of database structure.
4. Security/audit key material — backed up separately in the approved secret/KMS system. Keys are not placed in database dumps or source control.

## Portable logical backup

The scripts use standard PostgreSQL environment variables so the database password does not appear in process arguments.

Required:
- `PGHOST`
- `PGPORT` when non-default
- `PGDATABASE`
- `PGUSER`
- `PGPASSWORD` supplied by the runtime secret manager when required

Create a backup:

```bash
BACKUP_PATH=/secure/prism/prism.dump scripts/backup_postgres.sh
```

The script creates a custom-format PostgreSQL dump plus a SHA-256 manifest.

Restore into a clean recovery database:

```bash
BACKUP_PATH=/secure/prism/prism.dump scripts/restore_postgres.sh
```

The checksum is verified before `pg_restore` runs.

## Restore drill

`.github/workflows/dr-test.yml` performs an automated recovery drill against PostgreSQL 17:

1. migrate a clean PRISM database;
2. create a deterministic bootstrap tenant/workspace;
3. take a logical backup;
4. restore it into a second clean database;
5. verify restored P0/P1/P2 tables, bootstrap data and the P2 immutable-snapshot trigger.

A passing drill proves the repository's logical backup path is executable. It does not replace a production-region disaster-recovery exercise.

### P2 recovery scope

The automated restore drill now verifies the presence of `data_assets`, `data_snapshots`, `evidence_edges`, `decision_cases` and `ai_team_runs`, plus the PostgreSQL trigger that rejects snapshot updates. Materialised rows are therefore covered by the same logical-backup recovery path as the rest of the enterprise database.

For production-scale materialisation, recovery testing must additionally verify real snapshot volumes and the achieved RTO/RPO under representative storage size.

## Production controls still required

- store backup artifacts in encrypted, access-controlled object storage;
- use immutable/versioned retention for backup objects where supported;
- replicate backups to an approved recovery region/account when the risk model requires it;
- alert on failed scheduled backups and missed PITR windows;
- run a documented production restore exercise at least quarterly;
- record actual RPO/RTO achieved during each exercise;
- rotate and separately recover encryption/audit keys through the secret-management process.
