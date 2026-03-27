from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class RuleThresholds:
    short_aux_max_seconds: int = 60
    quick_return_window_seconds: int = 120
    min_short_aux_per_hour: int = 3
    min_short_aux_per_day: int = 8
    short_aux_ratio_threshold: float = 0.35
    call_after_return_window_seconds: int = 90


@dataclass(slots=True)
class ScoreWeights:
    short_aux_event: float = 1.0
    quick_return_event: float = 1.2
    repetitive_hourly: float = 2.0
    repetitive_daily: float = 2.5
    high_short_ratio: float = 2.0
    call_after_return: float = 1.3
    same_aux_repeat_bonus: float = 0.8
    outlier_bonus: float = 1.5


@dataclass(slots=True)
class AppConfig:
    input_dir: Path = Path("data")
    output_dir: Path = Path("outputs")
    database_path: Path = Path("outputs/avail_detector.db")
    ingestion_mode: str = "snapshot"  # future: event_log
    csv_encoding: str = "utf-8"
    csv_delimiters: tuple[str, ...] = (",", ";", "\t", "|")
    timestamp_filename_patterns: tuple[str, ...] = (
        r"(?P<date>\d{8})[_-](?P<time>\d{6})",
        r"(?P<date>\d{4}-\d{2}-\d{2})[_-](?P<time>\d{2}-\d{2}-\d{2})",
    )
    # source column -> normalized canonical name
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "nombre": "agent_name",
            "employee id": "agent_id",
            "current status": "current_status",
            "time in status": "time_in_status",
            "login time": "login_time",
            "continuous login time": "continuous_login_time",
            "hold": "hold",
            "acw": "acw",
            "llamadas": "inbound_calls",
            "llamadas salientes": "outbound_calls",
            "coaching": "coaching",
            "tareas administrativas": "admin_task",
            "break": "break",
            "tmo": "tmo",
            "ready time": "ready_time_total",
            "auxiliares": "aux_time_total",
            "handle time": "handle_time",
            "transferencias": "transfers",
        }
    )
    available_statuses: set[str] = field(
        default_factory=lambda: {"ready", "waitfornextcall", "available"}
    )
    aux_statuses: set[str] = field(
        default_factory=lambda: {
            "auxiliar",
            "break",
            "coaching",
            "tareas administrativas",
            "notready",
            "notreadyfornextcall",
        }
    )
    thresholds: RuleThresholds = field(default_factory=RuleThresholds)
    weights: ScoreWeights = field(default_factory=ScoreWeights)


def load_default_config() -> AppConfig:
    cfg = AppConfig()
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    return cfg
