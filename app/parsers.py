from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.config import AppConfig
from app.normalizers import normalize_columns, normalize_status, parse_duration_to_seconds


def extract_snapshot_timestamp(file_path: Path, config: AppConfig) -> datetime:
    name = file_path.stem
    for pattern in config.timestamp_filename_patterns:
        match = re.search(pattern, name)
        if not match:
            continue
        raw_date = match.group("date")
        raw_time = match.group("time").replace("-", "")
        if "-" in raw_date:
            return datetime.strptime(f"{raw_date}{raw_time}", "%Y-%m-%d%H%M%S")
        return datetime.strptime(f"{raw_date}{raw_time}", "%Y%m%d%H%M%S")
    raise ValueError(f"No se pudo extraer timestamp desde nombre de archivo: {file_path.name}")


def _read_csv_with_best_delimiter(file_path: Path, config: AppConfig) -> pd.DataFrame:
    last_error: Exception | None = None
    for delimiter in config.csv_delimiters:
        try:
            df = pd.read_csv(file_path, sep=delimiter, encoding=config.csv_encoding)
            if df.shape[1] > 1:
                return df
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise ValueError(f"No se pudo parsear {file_path}")


def parse_snapshot_file(file_path: Path, config: AppConfig) -> pd.DataFrame:
    snapshot_ts = extract_snapshot_timestamp(file_path, config)
    raw_df = _read_csv_with_best_delimiter(file_path, config)
    df = normalize_columns(raw_df, config.column_mapping)

    for required in ("agent_id", "current_status"):
        if required not in df.columns:
            raise ValueError(f"Falta columna requerida '{required}' en {file_path.name}")

    df["snapshot_timestamp"] = snapshot_ts
    df["source_file"] = file_path.name

    duration_cols = {
        "time_in_status": "time_in_status_seconds",
        "login_time": "login_time_seconds",
        "continuous_login_time": "continuous_login_time_seconds",
        "hold": "hold_seconds",
        "acw": "acw_seconds",
        "coaching": "coaching_seconds",
        "admin_task": "admin_task_seconds",
        "break": "break_seconds",
        "tmo": "tmo_seconds",
        "ready_time_total": "ready_time_total_seconds",
        "aux_time_total": "aux_time_total_seconds",
        "handle_time": "handle_time_seconds",
    }

    for source_col, target_col in duration_cols.items():
        if source_col in df.columns:
            df[target_col] = df[source_col].apply(parse_duration_to_seconds)
        else:
            df[target_col] = 0

    numeric_cols = {
        "inbound_calls": 0,
        "outbound_calls": 0,
        "transfers": 0,
    }
    for col, default in numeric_cols.items():
        if col not in df.columns:
            df[col] = default
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default).astype(int)

    if "agent_name" not in df.columns:
        df["agent_name"] = None

    df["current_status"] = df["current_status"].apply(normalize_status)
    df["agent_id"] = df["agent_id"].astype(str).str.strip()
    df["snapshot_id"] = df.apply(
        lambda x: f"{x['agent_id']}_{x['snapshot_timestamp'].strftime('%Y%m%d%H%M%S')}", axis=1
    )

    payload_cols = [c for c in raw_df.columns]
    df["raw_payload"] = raw_df[payload_cols].fillna("").to_dict(orient="records")
    df["raw_payload"] = df["raw_payload"].apply(json.dumps)

    keep_cols = [
        "snapshot_id",
        "snapshot_timestamp",
        "agent_id",
        "agent_name",
        "current_status",
        "time_in_status_seconds",
        "login_time_seconds",
        "continuous_login_time_seconds",
        "hold_seconds",
        "acw_seconds",
        "inbound_calls",
        "outbound_calls",
        "coaching_seconds",
        "admin_task_seconds",
        "break_seconds",
        "tmo_seconds",
        "ready_time_total_seconds",
        "aux_time_total_seconds",
        "handle_time_seconds",
        "transfers",
        "raw_payload",
    ]

    return df[keep_cols]


def parse_snapshot_folder(folder: Path, config: AppConfig) -> pd.DataFrame:
    all_files = sorted(folder.glob("*.csv"))
    if not all_files:
        raise FileNotFoundError(f"No hay CSV en {folder}")
    parts = [parse_snapshot_file(path, config) for path in all_files]
    combined = pd.concat(parts, ignore_index=True)
    combined = combined.sort_values(["agent_id", "snapshot_timestamp"]).reset_index(drop=True)
    return combined
