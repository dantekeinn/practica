from __future__ import annotations

import json
from datetime import timedelta

import pandas as pd

from app.config import AppConfig


def classify_transition(prev_status: str, curr_status: str, cfg: AppConfig) -> tuple[str, str | None]:
    if prev_status == curr_status:
        return "no_change", None

    prev_avail = prev_status in cfg.available_statuses
    curr_avail = curr_status in cfg.available_statuses
    prev_aux = prev_status in cfg.aux_statuses
    curr_aux = curr_status in cfg.aux_statuses

    if prev_avail and curr_aux:
        return "avail_to_aux", curr_status
    if prev_aux and curr_avail:
        return "aux_to_avail", prev_status
    if prev_aux and curr_aux:
        return "aux_to_aux", curr_status
    if prev_avail and curr_avail:
        return "avail_to_avail", None
    return "other", None


def _confidence_from_gap(gap_seconds: float) -> float:
    if gap_seconds <= 60:
        return 0.95
    if gap_seconds <= 180:
        return 0.8
    if gap_seconds <= 600:
        return 0.6
    return 0.35


def reconstruct_events(snapshots: pd.DataFrame, cfg: AppConfig) -> pd.DataFrame:
    ordered = snapshots.sort_values(["agent_id", "snapshot_timestamp"]).reset_index(drop=True).copy()
    ordered["snapshot_timestamp"] = pd.to_datetime(ordered["snapshot_timestamp"])

    rows: list[dict] = []
    for _, agent_df in ordered.groupby("agent_id", sort=False):
        prev = None
        for _, curr in agent_df.iterrows():
            if prev is None:
                prev = curr
                continue

            prev_ts = prev["snapshot_timestamp"]
            curr_ts = curr["snapshot_timestamp"]
            gap_seconds = max(0, (curr_ts - prev_ts).total_seconds())
            prev_status = str(prev["current_status"])
            curr_status = str(curr["current_status"])
            transition_type, aux_category = classify_transition(prev_status, curr_status, cfg)

            if transition_type == "no_change":
                prev = curr
                continue

            tis = int(curr.get("time_in_status_seconds", 0) or 0)
            inferred_back_seconds = min(tis, int(gap_seconds))
            inferred_change_ts = curr_ts - timedelta(seconds=inferred_back_seconds)
            inferred_duration_seconds = int((curr_ts - inferred_change_ts).total_seconds())
            ambiguity = gap_seconds > 300

            evidence = {
                "gap_seconds": gap_seconds,
                "time_in_status_seconds": tis,
                "ambiguity": ambiguity,
                "previous_snapshot_id": prev.get("snapshot_id"),
                "current_snapshot_id": curr.get("snapshot_id"),
            }

            rows.append(
                {
                    "event_id": f"{curr['agent_id']}_{curr_ts.strftime('%Y%m%d%H%M%S')}_{transition_type}",
                    "agent_id": curr["agent_id"],
                    "previous_snapshot_timestamp": prev_ts,
                    "current_snapshot_timestamp": curr_ts,
                    "previous_status": prev_status,
                    "current_status": curr_status,
                    "inferred_change_timestamp": inferred_change_ts,
                    "inferred_duration_seconds": inferred_duration_seconds,
                    "transition_type": transition_type,
                    "aux_category": aux_category,
                    "confidence_score": _confidence_from_gap(gap_seconds),
                    "evidence_payload": json.dumps(evidence),
                }
            )
            prev = curr

    return pd.DataFrame(rows)
