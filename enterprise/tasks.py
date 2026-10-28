from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from enterprise.audit import append_audit_event
from enterprise.auth import Principal
from enterprise.connectors import ConnectorError, execute_connector, fetch_connector_rows
from enterprise.control_plane import run_control_plane
from enterprise.materialization import MaterializationError, create_snapshot
from enterprise.models import (
    Connector,
    ConnectorCredential,
    ConnectorRun,
    DecisionRecord,
    DeletionRequest,
    EvidenceRecord,
    JobRecord,
    OutcomeRecord,
    RetentionPolicy,
    StrategyRecord,
)
from enterprise.observability import (
    CONNECTOR_RUNS,
    DECISION_CASES,
    MATERIALIZATIONS,
)
from enterprise.p2_models import (
    AITeamRun,
    DataAsset,
    DataSnapshot,
    DecisionCase,
    EvidenceEdge,
)
from enterprise.retention import purge_expired_records
from enterprise.tenancy import WorkspaceAccess


class TaskError(RuntimeError):
    pass


def _system_access(job: JobRecord) -> WorkspaceAccess:
    principal = Principal(
        subject="system:prism-worker",
        email=None,
        display_name="PRISM Worker",
        claims={"system": True},
    )
    return WorkspaceAccess(
        tenant_id=job.tenant_id,
        workspace_id=job.workspace_id,
        user_id=job.created_by,
        principal=principal,
        role="admin",
        data_clearance="restricted",
    )


def run_connector_job(db: Session, job: JobRecord) -> dict:
    connector_id = str(job.payload.get("connector_id", ""))
    run_id = str(job.payload.get("run_id", ""))
    operation = job.payload.get("operation")
    if not connector_id or not run_id or not isinstance(operation, dict):
        raise TaskError("Connector job payload is incomplete.")

    connector = db.scalar(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == job.tenant_id,
            Connector.workspace_id == job.workspace_id,
            Connector.status == "active",
        )
    )
    run = db.scalar(
        select(ConnectorRun).where(
            ConnectorRun.id == run_id,
            ConnectorRun.tenant_id == job.tenant_id,
            ConnectorRun.workspace_id == job.workspace_id,
        )
    )
    if connector is None or run is None:
        raise TaskError("Connector or connector run was not found.")

    try:
        result = execute_connector(db, connector, operation)
    except ConnectorError:
        CONNECTOR_RUNS.labels(
            connector_type=connector.connector_type,
            status="failed",
        ).inc()
        raise

    run.status = "succeeded"
    run.row_count = int(result["row_count"])
    run.content_hash = str(result["content_hash"])
    run.schema_summary = dict(result["schema_summary"])
    run.completed_at = datetime.now(UTC)

    evidence_id = f"EVD-CONN-{uuid.uuid4().hex.upper()}"
    db.add(
        EvidenceRecord(
            id=evidence_id,
            tenant_id=job.tenant_id,
            workspace_id=job.workspace_id,
            created_by=job.created_by,
            evidence_class="connector_run_metadata",
            classification="internal",
            payload={
                "connector_id": connector.id,
                "connector_type": connector.connector_type,
                "run_id": run.id,
                "row_count": run.row_count,
                "content_hash": run.content_hash,
                "schema_summary": run.schema_summary,
                "method": "bounded_read_only_connector_extract",
                "raw_rows_persisted": False,
            },
        )
    )
    append_audit_event(
        db,
        _system_access(job),
        event_type="connector_run_completed",
        object_type="connector_run",
        object_id=run.id,
        detail={
            "connector_id": connector.id,
            "row_count": run.row_count,
            "evidence_id": evidence_id,
        },
    )
    CONNECTOR_RUNS.labels(
        connector_type=connector.connector_type,
        status="succeeded",
    ).inc()
    return {
        "run_id": run.id,
        "evidence_id": evidence_id,
        "row_count": run.row_count,
        "content_hash": run.content_hash,
    }


def run_dataset_materialization_job(db: Session, job: JobRecord) -> dict:
    asset_id = str(job.payload.get("asset_id", ""))
    connector_id = str(job.payload.get("connector_id", ""))
    run_id = str(job.payload.get("run_id", ""))
    operation = job.payload.get("operation")
    if not asset_id or not connector_id or not run_id or not isinstance(operation, dict):
        raise TaskError("Dataset materialisation job payload is incomplete.")

    asset = db.scalar(
        select(DataAsset).where(
            DataAsset.id == asset_id,
            DataAsset.tenant_id == job.tenant_id,
            DataAsset.workspace_id == job.workspace_id,
            DataAsset.status == "active",
        )
    )
    connector = db.scalar(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == job.tenant_id,
            Connector.workspace_id == job.workspace_id,
            Connector.status == "active",
        )
    )
    run = db.scalar(
        select(ConnectorRun).where(
            ConnectorRun.id == run_id,
            ConnectorRun.tenant_id == job.tenant_id,
            ConnectorRun.workspace_id == job.workspace_id,
        )
    )
    if asset is None or connector is None or run is None:
        raise TaskError("Data asset, connector or connector run was not found.")
    if asset.source_connector_id != connector.id:
        raise TaskError("Data asset source connector does not match the queued connector.")

    try:
        rows = fetch_connector_rows(db, connector, operation)
        snapshot, evidence = create_snapshot(
            db,
            asset=asset,
            rows=rows,
            connector_run_id=run.id,
            created_by=job.created_by,
            connector_type=connector.connector_type,
        )
    except (ConnectorError, MaterializationError):
        CONNECTOR_RUNS.labels(
            connector_type=connector.connector_type,
            status="failed",
        ).inc()
        raise

    run.status = "succeeded"
    run.row_count = snapshot.row_count
    run.content_hash = snapshot.content_hash
    run.schema_summary = snapshot.schema_summary
    run.completed_at = datetime.now(UTC)
    append_audit_event(
        db,
        _system_access(job),
        event_type="data_materialization_completed",
        object_type="data_snapshot",
        object_id=snapshot.id,
        detail={
            "data_asset_id": asset.id,
            "snapshot_version": snapshot.version,
            "row_count": snapshot.row_count,
            "size_bytes": snapshot.size_bytes,
            "evidence_id": evidence.id,
            "connector_run_id": run.id,
        },
    )
    CONNECTOR_RUNS.labels(
        connector_type=connector.connector_type,
        status="succeeded",
    ).inc()
    MATERIALIZATIONS.labels(status="succeeded").inc()
    return {
        "data_asset_id": asset.id,
        "snapshot_id": snapshot.id,
        "snapshot_version": snapshot.version,
        "evidence_id": evidence.id,
        "row_count": snapshot.row_count,
        "content_hash": snapshot.content_hash,
    }


def run_decision_case_job(db: Session, job: JobRecord) -> dict:
    case_id = str(job.payload.get("decision_case_id", ""))
    if not case_id:
        raise TaskError("Decision Case job payload is incomplete.")

    case = db.scalar(
        select(DecisionCase)
        .where(
            DecisionCase.id == case_id,
            DecisionCase.tenant_id == job.tenant_id,
            DecisionCase.workspace_id == job.workspace_id,
        )
        .with_for_update()
    )
    if case is None:
        raise TaskError("Decision Case was not found.")

    case.status = "running"
    synthesis = run_control_plane(db, case)
    append_audit_event(
        db,
        _system_access(job),
        event_type="decision_case_analysis_completed",
        object_type="decision_case",
        object_id=case.id,
        detail={
            "status": case.status,
            "approval_state": case.approval_state,
            "participating_teams": case.participating_teams,
            "evidence_count": len(case.evidence_ids),
            "method": synthesis.get("method"),
        },
    )
    DECISION_CASES.labels(status=case.status).inc()
    return {
        "decision_case_id": case.id,
        "status": case.status,
        "approval_state": case.approval_state,
        "participating_teams": case.participating_teams,
        "evidence_count": len(case.evidence_ids),
    }


def run_retention_job(db: Session, job: JobRecord) -> dict:
    policy_id = str(job.payload.get("policy_id", ""))
    policy = db.scalar(
        select(RetentionPolicy).where(
            RetentionPolicy.id == policy_id,
            RetentionPolicy.tenant_id == job.tenant_id,
            RetentionPolicy.workspace_id == job.workspace_id,
            RetentionPolicy.enabled.is_(True),
        )
    )
    if policy is None:
        raise TaskError("Active retention policy was not found.")

    deleted = purge_expired_records(
        db,
        tenant_id=job.tenant_id,
        workspace_id=job.workspace_id,
        record_type=policy.record_type,
        retention_days=policy.retention_days,
    )
    append_audit_event(
        db,
        _system_access(job),
        event_type="retention_purge_completed",
        object_type="retention_policy",
        object_id=policy.id,
        detail={
            "record_type": policy.record_type,
            "retention_days": policy.retention_days,
            "deleted_records": deleted,
        },
    )
    return {"policy_id": policy.id, "deleted_records": deleted}


def _delete_connector(db: Session, job: JobRecord, connector_id: str) -> dict:
    connector = db.scalar(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == job.tenant_id,
            Connector.workspace_id == job.workspace_id,
        )
    )
    if connector is None:
        return {"connector_deleted": False}

    db.execute(
        delete(ConnectorCredential).where(
            ConnectorCredential.tenant_id == job.tenant_id,
            ConnectorCredential.workspace_id == job.workspace_id,
            ConnectorCredential.connector_id == connector_id,
        )
    )
    db.execute(
        delete(ConnectorRun).where(
            ConnectorRun.tenant_id == job.tenant_id,
            ConnectorRun.workspace_id == job.workspace_id,
            ConnectorRun.connector_id == connector_id,
        )
    )
    db.delete(connector)
    return {"connector_deleted": True}


def _delete_data_asset(db: Session, job: JobRecord, asset_id: str) -> dict:
    asset = db.scalar(
        select(DataAsset)
        .where(
            DataAsset.id == asset_id,
            DataAsset.tenant_id == job.tenant_id,
            DataAsset.workspace_id == job.workspace_id,
        )
        .with_for_update()
    )
    if asset is None:
        return {"data_asset_deleted": False}

    snapshots = db.scalars(
        select(DataSnapshot).where(
            DataSnapshot.tenant_id == job.tenant_id,
            DataSnapshot.workspace_id == job.workspace_id,
            DataSnapshot.asset_id == asset_id,
        )
    ).all()
    snapshot_ids = [item.id for item in snapshots]

    evidence = db.scalars(
        select(EvidenceRecord).where(
            EvidenceRecord.tenant_id == job.tenant_id,
            EvidenceRecord.workspace_id == job.workspace_id,
            EvidenceRecord.evidence_class == "materialized_dataset_snapshot",
        )
    ).all()
    evidence_ids = [
        item.id
        for item in evidence
        if item.payload.get("data_asset_id") == asset_id
    ]

    related_ids = [asset_id, *snapshot_ids, *evidence_ids]
    if related_ids:
        db.execute(
            delete(EvidenceEdge).where(
                EvidenceEdge.tenant_id == job.tenant_id,
                EvidenceEdge.workspace_id == job.workspace_id,
                or_(
                    EvidenceEdge.source_id.in_(related_ids),
                    EvidenceEdge.target_id.in_(related_ids),
                ),
            )
        )
    if evidence_ids:
        db.execute(
            delete(EvidenceRecord).where(
                EvidenceRecord.tenant_id == job.tenant_id,
                EvidenceRecord.workspace_id == job.workspace_id,
                EvidenceRecord.id.in_(evidence_ids),
            )
        )
    db.execute(
        delete(DataSnapshot).where(
            DataSnapshot.tenant_id == job.tenant_id,
            DataSnapshot.workspace_id == job.workspace_id,
            DataSnapshot.asset_id == asset_id,
        )
    )
    db.delete(asset)
    return {
        "data_asset_deleted": True,
        "snapshots_deleted": len(snapshot_ids),
        "evidence_deleted": len(evidence_ids),
    }


def _delete_decision_case(db: Session, job: JobRecord, case_id: str) -> dict:
    case = db.scalar(
        select(DecisionCase).where(
            DecisionCase.id == case_id,
            DecisionCase.tenant_id == job.tenant_id,
            DecisionCase.workspace_id == job.workspace_id,
        )
    )
    if case is None:
        return {"decision_case_deleted": False}

    runs = db.scalars(
        select(AITeamRun).where(
            AITeamRun.tenant_id == job.tenant_id,
            AITeamRun.workspace_id == job.workspace_id,
            AITeamRun.decision_case_id == case_id,
        )
    ).all()
    related_ids = [case_id, *[run.id for run in runs]]
    db.execute(
        delete(EvidenceEdge).where(
            EvidenceEdge.tenant_id == job.tenant_id,
            EvidenceEdge.workspace_id == job.workspace_id,
            or_(
                EvidenceEdge.source_id.in_(related_ids),
                EvidenceEdge.target_id.in_(related_ids),
            ),
        )
    )
    db.execute(
        delete(AITeamRun).where(
            AITeamRun.tenant_id == job.tenant_id,
            AITeamRun.workspace_id == job.workspace_id,
            AITeamRun.decision_case_id == case_id,
        )
    )
    db.delete(case)
    return {
        "decision_case_deleted": True,
        "team_runs_deleted": len(runs),
    }


def run_deletion_job(db: Session, job: JobRecord) -> dict:
    request_id = str(job.payload.get("deletion_request_id", ""))
    request = db.scalar(
        select(DeletionRequest).where(
            DeletionRequest.id == request_id,
            DeletionRequest.tenant_id == job.tenant_id,
            DeletionRequest.workspace_id == job.workspace_id,
        )
    )
    if request is None or request.status != "approved":
        raise TaskError("Deletion request is missing or is not approved.")

    result: dict[str, int | bool] = {}
    if request.request_type == "evidence":
        deleted = db.execute(
            delete(EvidenceRecord).where(
                EvidenceRecord.tenant_id == job.tenant_id,
                EvidenceRecord.workspace_id == job.workspace_id,
                EvidenceRecord.id == request.target_id,
            )
        )
        result["evidence_deleted"] = int(deleted.rowcount or 0)
    elif request.request_type == "connector" and request.target_id:
        result.update(_delete_connector(db, job, request.target_id))
    elif request.request_type == "data_asset" and request.target_id:
        result.update(_delete_data_asset(db, job, request.target_id))
    elif request.request_type == "decision_case" and request.target_id:
        result.update(_delete_decision_case(db, job, request.target_id))
    elif request.request_type == "workspace_analytical_records":
        for name, model in [
            ("ai_team_runs", AITeamRun),
            ("decision_cases", DecisionCase),
            ("evidence_edges", EvidenceEdge),
            ("data_snapshots", DataSnapshot),
            ("data_assets", DataAsset),
            ("evidence", EvidenceRecord),
            ("strategy", StrategyRecord),
            ("decision", DecisionRecord),
            ("outcome", OutcomeRecord),
            ("connector_runs", ConnectorRun),
        ]:
            deleted = db.execute(
                delete(model).where(
                    model.tenant_id == job.tenant_id,
                    model.workspace_id == job.workspace_id,
                )
            )
            result[name] = int(deleted.rowcount or 0)
    else:
        raise TaskError("Unsupported deletion request type.")

    request.status = "completed"
    request.completed_at = datetime.now(UTC)
    request.result = result
    append_audit_event(
        db,
        _system_access(job),
        event_type="deletion_request_completed",
        object_type="deletion_request",
        object_id=request.id,
        detail={
            "request_type": request.request_type,
            "target_id": request.target_id,
            "result": result,
        },
    )
    return {"deletion_request_id": request.id, **result}


def dispatch_job(db: Session, job: JobRecord) -> dict:
    if job.job_type == "connector_run":
        return run_connector_job(db, job)
    if job.job_type == "dataset_materialize":
        return run_dataset_materialization_job(db, job)
    if job.job_type == "decision_case_analyze":
        return run_decision_case_job(db, job)
    if job.job_type == "retention_purge":
        return run_retention_job(db, job)
    if job.job_type == "deletion_execute":
        return run_deletion_job(db, job)
    raise TaskError("Unsupported job type.")


def record_task_failure(
    db: Session,
    job: JobRecord,
    error_code: str,
) -> None:
    if job.job_type in {"connector_run", "dataset_materialize"}:
        run_id = str(job.payload.get("run_id", ""))
        if run_id:
            run = db.scalar(
                select(ConnectorRun).where(
                    ConnectorRun.id == run_id,
                    ConnectorRun.tenant_id == job.tenant_id,
                    ConnectorRun.workspace_id == job.workspace_id,
                )
            )
            if run is not None:
                run.error_code = error_code[:80]
                if job.status == "failed":
                    run.status = "failed"
                    run.completed_at = datetime.now(UTC)
                else:
                    run.status = "retrying"
                    run.completed_at = None
        if job.job_type == "dataset_materialize":
            status_label = "failed" if job.status == "failed" else "retrying"
            MATERIALIZATIONS.labels(status=status_label).inc()
        return

    if job.job_type == "decision_case_analyze":
        case_id = str(job.payload.get("decision_case_id", ""))
        if not case_id:
            return
        case = db.scalar(
            select(DecisionCase).where(
                DecisionCase.id == case_id,
                DecisionCase.tenant_id == job.tenant_id,
                DecisionCase.workspace_id == job.workspace_id,
            )
        )
        if case is None:
            return
        if job.status == "failed":
            case.status = "failed"
            case.approval_state = "not_reviewable"
            DECISION_CASES.labels(status="failed").inc()
        else:
            case.status = "retrying"
            DECISION_CASES.labels(status="retrying").inc()
