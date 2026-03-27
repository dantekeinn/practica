from __future__ import annotations

import re
from typing import Any

import pandas as pd


def clean_column_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def normalize_columns(df: pd.DataFrame, column_mapping: dict[str, str]) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    for col in df.columns:
        cleaned = clean_column_name(str(col))
        rename_map[col] = column_mapping.get(cleaned, cleaned.replace(" ", "_"))
    return df.rename(columns=rename_map)


def parse_duration_to_seconds(value: Any) -> int:
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return 0
    parts = text.split(":")
    if len(parts) == 3:
        try:
            h, m, s = (int(float(x)) for x in parts)
            return h * 3600 + m * 60 + s
        except ValueError:
            return 0
    if text.isdigit():
        return int(text)
    return 0


def normalize_status(raw_status: Any) -> str:
    if raw_status is None or pd.isna(raw_status):
        return "unknown"
    return re.sub(r"\s+", "", str(raw_status).strip().lower())
