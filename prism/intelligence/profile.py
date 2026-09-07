from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DatasetProfile:
    rows: int
    columns: int
    missing_cells: int
    missing_pct: float
    duplicate_rows: int
    duplicate_pct: float
    numeric_columns: list[str]
    categorical_columns: list[str]
    date_columns: list[str]
    boolean_columns: list[str]
    id_like_columns: list[str]
    constant_columns: list[str]
    quality_score: float


def _looks_like_date_name(column: str) -> bool:
    name = column.lower().strip()
    tokens = ("date", "time", "timestamp", "month", "year", "week", "day")
    return any(token in name for token in tokens)


def _infer_date_columns(df: pd.DataFrame) -> list[str]:
    date_columns: list[str] = []
    for column in df.columns:
        series = df[column]
        if pd.api.types.is_datetime64_any_dtype(series):
            date_columns.append(column)
            continue
        if not _looks_like_date_name(str(column)):
            continue
        if pd.api.types.is_numeric_dtype(series):
            continue
        sample = series.dropna().astype(str).head(200)
        if sample.empty:
            continue
        parsed = pd.to_datetime(sample, errors="coerce")
        if float(parsed.notna().mean()) >= 0.8:
            date_columns.append(column)
    return date_columns


def profile_dataset(df: pd.DataFrame) -> DatasetProfile:
    if df is None or df.empty:
        raise ValueError("The dataset is empty.")

    rows, columns = df.shape
    total_cells = max(rows * columns, 1)
    missing_cells = int(df.isna().sum().sum())
    missing_pct = 100.0 * missing_cells / total_cells
    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = 100.0 * duplicate_rows / max(rows, 1)

    date_columns = _infer_date_columns(df)
    boolean_columns = [
        column for column in df.columns if pd.api.types.is_bool_dtype(df[column])
    ]
    numeric_columns = [
        column
        for column in df.select_dtypes(include="number").columns.tolist()
        if column not in date_columns
    ]
    categorical_columns = [
        column
        for column in df.columns
        if column not in numeric_columns + date_columns + boolean_columns
    ]

    id_like_columns: list[str] = []
    constant_columns: list[str] = []
    for column in df.columns:
        unique = int(df[column].nunique(dropna=True))
        if unique <= 1:
            constant_columns.append(column)
        unique_ratio = unique / max(int(df[column].notna().sum()), 1)
        name = str(column).lower()
        if unique_ratio >= 0.95 and ("id" in name or "key" in name or "code" in name):
            id_like_columns.append(column)

    constant_pct = 100.0 * len(constant_columns) / max(columns, 1)
    quality_score = 100.0 - (0.65 * missing_pct) - (0.25 * duplicate_pct)
    quality_score -= 0.10 * constant_pct
    quality_score = round(max(0.0, min(100.0, quality_score)), 1)

    return DatasetProfile(
        rows=rows,
        columns=columns,
        missing_cells=missing_cells,
        missing_pct=round(missing_pct, 2),
        duplicate_rows=duplicate_rows,
        duplicate_pct=round(duplicate_pct, 2),
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        date_columns=date_columns,
        boolean_columns=boolean_columns,
        id_like_columns=id_like_columns,
        constant_columns=constant_columns,
        quality_score=quality_score,
    )


def column_inventory(df: pd.DataFrame, profile: DatasetProfile) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for column in df.columns:
        if column in profile.date_columns:
            role = "Date/time"
        elif column in profile.numeric_columns:
            role = "Numeric"
        elif column in profile.boolean_columns:
            role = "Boolean"
        else:
            role = "Category/text"
        if column in profile.id_like_columns:
            role = "Identifier"
        if column in profile.constant_columns:
            role = "Constant"

        rows.append(
            {
                "column": column,
                "role": role,
                "dtype": str(df[column].dtype),
                "missing": int(df[column].isna().sum()),
                "missing_pct": round(100.0 * df[column].isna().mean(), 2),
                "unique": int(df[column].nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)
