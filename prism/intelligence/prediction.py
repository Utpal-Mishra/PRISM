from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


@dataclass(frozen=True)
class PredictionResult:
    task: str
    target: str
    primary_metric: str
    primary_score: float
    secondary_metric: str
    secondary_score: float
    baseline_metric: str
    baseline_score: float
    feature_importance: pd.DataFrame
    training_rows: int
    test_rows: int
    warnings: tuple[str, ...]


def _is_classification_target(series: pd.Series) -> bool:
    unique = int(series.nunique(dropna=True))
    if pd.api.types.is_bool_dtype(series) or not pd.api.types.is_numeric_dtype(series):
        return 2 <= unique <= 30
    return 2 <= unique <= 10


def _usable_features(df: pd.DataFrame, target: str, requested: list[str] | None) -> list[str]:
    candidates = requested or [column for column in df.columns if column != target]
    usable: list[str] = []
    for column in candidates:
        if column == target or column not in df:
            continue
        series = df[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            continue
        unique = int(series.nunique(dropna=True))
        non_null = max(int(series.notna().sum()), 1)
        unique_ratio = unique / non_null
        name = str(column).lower()
        if unique <= 1:
            continue
        if unique_ratio >= 0.98 and ("id" in name or "key" in name or "code" in name):
            continue
        if not pd.api.types.is_numeric_dtype(series) and unique > 60:
            continue
        usable.append(column)
    return usable[:30]


def train_predictive_model(
    df: pd.DataFrame,
    target: str,
    features: list[str] | None = None,
    random_state: int = 42,
) -> PredictionResult:
    if target not in df:
        raise ValueError(f"Target column '{target}' was not found.")

    working = df.copy()
    working = working.dropna(subset=[target])
    if len(working) < 40:
        raise ValueError("At least 40 rows with a target value are required for prediction.")

    selected = _usable_features(working, target, features)
    if not selected:
        raise ValueError("No usable predictor columns were found for this target.")

    x = working[selected].copy()
    y = working[target].copy()
    classification = _is_classification_target(y)

    if classification:
        if y.nunique() < 2:
            raise ValueError("The selected target needs at least two classes.")
        task = "Classification"
    else:
        y = pd.to_numeric(y, errors="coerce")
        valid = y.notna()
        x = x.loc[valid]
        y = y.loc[valid]
        if len(y) < 40:
            raise ValueError("The target does not contain enough numeric values for regression.")
        task = "Regression"

    numeric_features = [
        column for column in selected if pd.api.types.is_numeric_dtype(x[column])
    ]
    categorical_features = [column for column in selected if column not in numeric_features]

    numeric_pipeline = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", max_categories=30)),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
    )

    warnings: list[str] = []
    stratify = y if classification and y.value_counts().min() >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=random_state,
        stratify=stratify,
    )

    if classification:
        estimator = RandomForestClassifier(
            n_estimators=180,
            max_depth=12,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1,
            class_weight="balanced_subsample",
        )
        scoring = "accuracy"
    else:
        estimator = RandomForestRegressor(
            n_estimators=180,
            max_depth=12,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1,
        )
        scoring = "r2"

    model = Pipeline([("preprocessor", preprocessor), ("model", estimator)])
    model.fit(x_train, y_train)
    predicted = model.predict(x_test)

    if classification:
        primary_metric = "Accuracy"
        primary_score = float(accuracy_score(y_test, predicted))
        secondary_metric = "Weighted F1"
        secondary_score = float(f1_score(y_test, predicted, average="weighted"))
        majority_share = float(y_train.value_counts(normalize=True).iloc[0])
        baseline_metric = "Majority-class accuracy"
        baseline_score = majority_share
        if primary_score <= majority_share:
            warnings.append("Model accuracy does not outperform the majority-class baseline.")
    else:
        primary_metric = "R²"
        primary_score = float(r2_score(y_test, predicted))
        secondary_metric = "MAE"
        secondary_score = float(mean_absolute_error(y_test, predicted))
        baseline_prediction = np.repeat(float(y_train.median()), len(y_test))
        baseline_metric = "Median baseline MAE"
        baseline_score = float(mean_absolute_error(y_test, baseline_prediction))
        if primary_score < 0:
            warnings.append("Model fit is weak; treat driver rankings as exploratory only.")

    sample_size = min(len(x_test), 1000)
    sampled_x = x_test.iloc[:sample_size]
    sampled_y = y_test.iloc[:sample_size]
    importance = permutation_importance(
        model,
        sampled_x,
        sampled_y,
        n_repeats=3,
        random_state=random_state,
        scoring=scoring,
        n_jobs=-1,
    )
    feature_importance = pd.DataFrame(
        {
            "feature": selected,
            "importance": importance.importances_mean,
        }
    ).sort_values("importance", ascending=False)
    feature_importance["importance"] = feature_importance["importance"].round(4)

    return PredictionResult(
        task=task,
        target=target,
        primary_metric=primary_metric,
        primary_score=round(primary_score, 4),
        secondary_metric=secondary_metric,
        secondary_score=round(secondary_score, 4),
        baseline_metric=baseline_metric,
        baseline_score=round(baseline_score, 4),
        feature_importance=feature_importance.reset_index(drop=True),
        training_rows=len(x_train),
        test_rows=len(x_test),
        warnings=tuple(warnings),
    )
