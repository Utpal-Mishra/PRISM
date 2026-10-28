from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, or_, select
from sqlalchemy.orm import Session

from enterprise.config import EnterpriseSettings
from enterprise.control_plane import (
    route_teams,
    run_control_plane,
    select_evidence,
    team_registry,
)
from enterprise.db import Base
from enterprise.materialization import MaterializationError, create_snapshot
from enterprise.models import EvidenceRecord
from enterprise.p2_models import (
    AITeamRun,
    DataAsset,
    DataSnapshot,
    DecisionCase,
    EvidenceEdge,
)
from enterprise.retention import purge_expired_records


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _asset(db: Session, classification: str = "internal") -> DataAsset:
    asset = DataAsset(
        id="DATA-TEST",
        tenant_id="tenant-p2",
        workspace_id="workspace-p2",
        created_by="user-p2",
        name="Governed test asset",
        description="P2 test fixture",
        owner="Data Owner",
        classification=classification,
        source_connector_id="connector-p2",
        status="active",
    )
    db.add(asset)
    db.flush()
    return asset


def _case(
    db: Session,
    *,
    question: str,
    max_classification: str = "internal",
    requested_evidence_ids: list[str] | None = None,
) -> DecisionCase:
    case = DecisionCase(
        id=f"DC-TEST-{len(db.query(DecisionCase).all()) + 1}",
        tenant_id="tenant-p2",
        workspace_id="workspace-p2",
        created_by="user-p2",
        business_question=question,
        owner="Decision Owner",
        materiality="material",
        max_classification=max_classification,
        status="queued",
        approval_state="not_reviewed",
        requested_evidence_ids=requested_evidence_ids or [],
        evidence_ids=[],
    )
    db.add(case)
    db.flush()
    return case


def _evidence(
    db: Session,
    evidence_id: str,
    evidence_class: str,
    classification: str,
    finding: str,
) -> EvidenceRecord:
    record = EvidenceRecord(
        id=evidence_id,
        tenant_id="tenant-p2",
        workspace_id="workspace-p2",
        created_by="user-p2",
        evidence_class=evidence_class,
        classification=classification,
        payload={
            "finding": finding,
            "method": "test_method",
            "causal_status": "causal-not-established",
        },
    )
    db.add(record)
    db.flush()
    return record


def test_team_registry_contains_five_core_teams() -> None:
    teams = {item["team"] for item in team_registry()}
    assert teams == {
        "data",
        "analytics",
        "data_science",
        "strategy",
        "governance",
    }


def test_router_can_assemble_all_five_core_teams() -> None:
    teams = route_teams(
        "Given the data quality and KPI performance, forecast the result "
        "and recommend what strategy we should decide."
    )
    assert teams == [
        "data",
        "analytics",
        "data_science",
        "strategy",
        "governance",
    ]


def test_materialized_snapshots_are_bounded_versioned_and_traceable() -> None:
    db = _session()
    asset = _asset(db)
    settings = EnterpriseSettings(
        materialized_dataset_max_rows=1,
        materialized_dataset_max_bytes=100_000,
    )

    first, first_evidence = create_snapshot(
        db,
        asset=asset,
        rows=[{"when": datetime(2026, 10, 28, tzinfo=UTC), "value": 10}],
        connector_run_id="run-1",
        created_by="user-p2",
        connector_type="postgresql",
        settings=settings,
    )
    second, second_evidence = create_snapshot(
        db,
        asset=asset,
        rows=[{"when": datetime(2026, 10, 29, tzinfo=UTC), "value": 11}],
        connector_run_id="run-2",
        created_by="user-p2",
        connector_type="postgresql",
        settings=settings,
    )
    db.flush()

    assert first.version == 1
    assert second.version == 2
    assert first.immutable is True
    assert first.rows[0]["when"].startswith("2026-10-28")
    assert asset.latest_snapshot_id == second.id
    assert first_evidence.evidence_class == "materialized_dataset_snapshot"
    assert second_evidence.payload["raw_rows_in_evidence"] is False
    assert db.query(EvidenceEdge).count() == 5

    with pytest.raises(MaterializationError):
        create_snapshot(
            db,
            asset=asset,
            rows=[{"value": 1}, {"value": 2}],
            connector_run_id="run-3",
            created_by="user-p2",
            connector_type="postgresql",
            settings=settings,
        )


def test_snapshot_retention_repairs_latest_pointer() -> None:
    db = _session()
    asset = _asset(db)
    settings = EnterpriseSettings(
        materialized_dataset_max_rows=10,
        materialized_dataset_max_bytes=100_000,
    )
    old, _ = create_snapshot(
        db,
        asset=asset,
        rows=[{"value": 1}],
        connector_run_id="run-old",
        created_by="user-p2",
        connector_type="rest_https",
        settings=settings,
    )
    latest, _ = create_snapshot(
        db,
        asset=asset,
        rows=[{"value": 2}],
        connector_run_id="run-new",
        created_by="user-p2",
        connector_type="rest_https",
        settings=settings,
    )
    now = datetime.now(UTC)
    old.created_at = now - timedelta(days=400)
    latest.created_at = now - timedelta(days=10)
    db.commit()

    deleted = purge_expired_records(
        db,
        tenant_id="tenant-p2",
        workspace_id="workspace-p2",
        record_type="data_snapshot",
        retention_days=365,
        now=now,
    )
    db.commit()

    assert deleted == 1
    assert db.get(DataSnapshot, old.id) is None
    assert db.get(DataSnapshot, latest.id) is not None
    assert db.get(DataAsset, asset.id).latest_snapshot_id == latest.id


def test_control_plane_filters_clearance_and_requires_human_review() -> None:
    db = _session()
    _evidence(
        db,
        "EVD-INTERNAL",
        "forecast_result",
        "internal",
        "Forecast evidence for margin planning.",
    )
    _evidence(
        db,
        "EVD-RESTRICTED",
        "forecast_result",
        "restricted",
        "Restricted forecast evidence must not be exposed.",
    )
    case = _case(
        db,
        question="Should we use the forecast to decide the margin strategy?",
        max_classification="internal",
    )

    synthesis = run_control_plane(db, case)
    db.flush()

    assert case.status == "completed"
    assert case.approval_state == "pending_human_review"
    assert "EVD-INTERNAL" in case.evidence_ids
    assert "EVD-RESTRICTED" not in case.evidence_ids
    assert synthesis["method"] == "deterministic_control_plane_v1"
    assert synthesis["causal_status"] == "causal-not-established"
    assert synthesis["human_review_required"] is True
    assert set(case.participating_teams) == {
        "analytics",
        "data_science",
        "strategy",
        "governance",
    }

    governance = db.scalar(
        select(AITeamRun).where(
            AITeamRun.decision_case_id == case.id,
            AITeamRun.team == "governance",
        )
    )
    assert governance is not None
    assert governance.finding["review_ready"] is True

    team_runs = db.scalars(
        select(AITeamRun).where(
            AITeamRun.decision_case_id == case.id,
            AITeamRun.team != "governance",
        )
    ).all()
    assert team_runs
    assert all(run.evidence_ids for run in team_runs)


def test_control_plane_refuses_when_no_evidence_exists() -> None:
    db = _session()
    case = _case(
        db,
        question="Should we launch this product based on the available evidence?",
    )
    synthesis = run_control_plane(db, case)
    db.flush()

    assert case.status == "insufficient_evidence"
    assert case.approval_state == "not_reviewable"
    assert case.participating_teams == ["governance"]
    assert synthesis["status"] == "insufficient_evidence"
    assert synthesis["evidence_ids"] == []


def test_decision_case_rerun_replaces_team_lineage_and_discovers_new_evidence() -> None:
    db = _session()
    _evidence(
        db,
        "EVD-ONE",
        "forecast_result",
        "internal",
        "Forecast evidence for revenue planning.",
    )
    case = _case(
        db,
        question="Should we forecast revenue and choose a strategy?",
    )
    run_control_plane(db, case)
    db.flush()

    old_run_ids = db.scalars(
        select(AITeamRun.id).where(AITeamRun.decision_case_id == case.id)
    ).all()
    assert old_run_ids

    _evidence(
        db,
        "EVD-TWO",
        "forecast_result",
        "internal",
        "New forecast evidence for revenue strategy.",
    )
    run_control_plane(db, case)
    db.flush()

    assert "EVD-TWO" in case.evidence_ids
    new_run_ids = db.scalars(
        select(AITeamRun.id).where(AITeamRun.decision_case_id == case.id)
    ).all()
    assert new_run_ids
    assert not set(old_run_ids).intersection(new_run_ids)

    stale_edges = db.scalars(
        select(EvidenceEdge).where(
            or_(
                EvidenceEdge.source_id.in_(old_run_ids),
                EvidenceEdge.target_id.in_(old_run_ids),
            )
        )
    ).all()
    assert stale_edges == []


def test_explicit_evidence_pins_remain_bounded_on_rerun() -> None:
    db = _session()
    _evidence(
        db,
        "EVD-PINNED",
        "forecast_result",
        "internal",
        "Pinned forecast evidence.",
    )
    _evidence(
        db,
        "EVD-UNPINNED",
        "forecast_result",
        "internal",
        "Other forecast evidence.",
    )
    case = _case(
        db,
        question="Should we use this forecast for a strategy decision?",
        requested_evidence_ids=["EVD-PINNED"],
    )

    selected = select_evidence(db, case)
    assert [item.id for item in selected] == ["EVD-PINNED"]

    run_control_plane(db, case)
    db.flush()
    assert case.requested_evidence_ids == ["EVD-PINNED"]
    assert case.evidence_ids == ["EVD-PINNED"]
