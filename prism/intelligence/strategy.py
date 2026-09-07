from dataclasses import dataclass

import pandas as pd

from prism.intelligence.forecasting import ForecastResult
from prism.intelligence.prediction import PredictionResult
from prism.intelligence.profile import DatasetProfile


@dataclass(frozen=True)
class StrategySignal:
    priority: str
    theme: str
    evidence: str
    recommendation: str
    decision_impact: str


def build_strategy_signals(
    profile: DatasetProfile,
    relationships: pd.DataFrame,
    anomalies: pd.DataFrame,
    forecast: ForecastResult | None = None,
    prediction: PredictionResult | None = None,
    segment: pd.DataFrame | None = None,
) -> list[StrategySignal]:
    signals: list[StrategySignal] = []

    if profile.quality_score < 90:
        signals.append(
            StrategySignal(
                priority="High",
                theme="Data foundation",
                evidence=(
                    f"Data quality score is {profile.quality_score:.1f}% with "
                    f"{profile.missing_pct:.1f}% missing cells."
                ),
                recommendation=(
                    "Prioritise ownership, validation rules, missing-value controls and "
                    "source-system reconciliation before automating high-impact decisions."
                ),
                decision_impact=(
                    "Improves trust, repeatability and auditability of downstream reporting."
                ),
            )
        )

    if profile.duplicate_pct >= 2:
        signals.append(
            StrategySignal(
                priority="High",
                theme="Process control",
                evidence=f"{profile.duplicate_pct:.1f}% of rows are duplicates.",
                recommendation=(
                    "Define a business key and deduplication policy, then add duplicate checks "
                    "at ingestion."
                ),
                decision_impact=(
                    "Reduces KPI inflation and prevents duplicated operational actions."
                ),
            )
        )

    if forecast is not None:
        change = forecast.projected_change_pct
        if change <= -5:
            signals.append(
                StrategySignal(
                    priority="High",
                    theme="Performance protection",
                    evidence=(
                        f"Forecast indicates a {abs(change):.1f}% decline versus the recent "
                        "baseline."
                    ),
                    recommendation=(
                        "Build a recovery plan around the strongest controllable drivers, "
                        "segment the decline, and set trigger thresholds for intervention."
                    ),
                    decision_impact="Supports earlier corrective action and downside planning.",
                )
            )
        elif change >= 5:
            signals.append(
                StrategySignal(
                    priority="Medium",
                    theme="Growth readiness",
                    evidence=f"Forecast indicates {change:.1f}% growth versus the recent baseline.",
                    recommendation=(
                        "Validate capacity, inventory, service levels and budget against the "
                        "projected growth so operational constraints do not become the limiting factor."
                    ),
                    decision_impact="Aligns resources and operating plans with expected demand.",
                )
            )

    if prediction is not None and not prediction.feature_importance.empty:
        top = prediction.feature_importance.iloc[0]
        if float(top["importance"]) > 0:
            signals.append(
                StrategySignal(
                    priority="Medium",
                    theme="Driver focus",
                    evidence=(
                        f"'{top['feature']}' is the strongest model driver for "
                        f"'{prediction.target}' in the current predictive run."
                    ),
                    recommendation=(
                        "Test whether this driver is controllable, validate it with domain owners, "
                        "and design an experiment or scenario around it before treating it as causal."
                    ),
                    decision_impact=(
                        "Focuses analysis effort on variables most associated with the target."
                    ),
                )
            )

    if not relationships.empty:
        strongest = relationships.iloc[0]
        if abs(float(strongest["correlation"])) >= 0.7:
            signals.append(
                StrategySignal(
                    priority="Medium",
                    theme="Relationship validation",
                    evidence=(
                        f"Strong {str(strongest['direction']).lower()} association between "
                        f"'{strongest['variable_a']}' and '{strongest['variable_b']}' "
                        f"(r={float(strongest['correlation']):.2f})."
                    ),
                    recommendation=(
                        "Investigate the relationship by segment and time period and check for "
                        "common drivers before using it in policy, investment or operating decisions."
                    ),
                    decision_impact=(
                        "Surfaces potentially valuable relationships without overstating causality."
                    ),
                )
            )

    if segment is not None and not segment.empty and "share_pct" in segment:
        top_share = segment["share_pct"].dropna()
        if not top_share.empty and float(top_share.iloc[0]) >= 50:
            top_name = str(segment.iloc[0, 0])
            signals.append(
                StrategySignal(
                    priority="Medium",
                    theme="Concentration risk",
                    evidence=(
                        f"Top segment '{top_name}' contributes "
                        f"{float(top_share.iloc[0]):.1f}%."
                    ),
                    recommendation=(
                        "Stress-test dependency on the dominant segment and identify diversification "
                        "or retention actions appropriate to the business context."
                    ),
                    decision_impact=(
                        "Makes concentration exposure explicit for planning and risk management."
                    ),
                )
            )

    if not anomalies.empty and float(anomalies.iloc[0]["outlier_pct"]) >= 5:
        row = anomalies.iloc[0]
        signals.append(
            StrategySignal(
                priority="Medium",
                theme="Exception management",
                evidence=(
                    f"'{row['column']}' has {float(row['outlier_pct']):.1f}% potential outliers."
                ),
                recommendation=(
                    "Separate genuine business exceptions from data errors and create threshold-based "
                    "monitoring for recurring abnormal behaviour."
                ),
                decision_impact=(
                    "Improves control of operational exceptions and data-quality incidents."
                ),
            )
        )

    if not profile.date_columns:
        signals.append(
            StrategySignal(
                priority="Low",
                theme="Measurement design",
                evidence="No reliable date/time field was detected.",
                recommendation=(
                    "Add a governed temporal dimension so performance can be trended, forecast and "
                    "compared before/after interventions."
                ),
                decision_impact=(
                    "Unlocks forecasting, change detection and longitudinal strategy tracking."
                ),
            )
        )

    if not signals:
        signals.append(
            StrategySignal(
                priority="Low",
                theme="Next best analysis",
                evidence=(
                    "No material automated risk signal was detected in the current configuration."
                ),
                recommendation=(
                    "Define a decision target, select the KPI or outcome to optimise, and use PRISM's "
                    "prediction and segmentation views to test the strongest available drivers."
                ),
                decision_impact=(
                    "Moves the workflow from descriptive reporting toward decision-oriented analysis."
                ),
            )
        )
    return signals
