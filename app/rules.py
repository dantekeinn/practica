from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from app.config import AppConfig


def _severity(score: float) -> str:
    if score >= 8:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def run_rules(events: pd.DataFrame, snapshots: pd.DataFrame, cfg: AppConfig) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=[
            "alert_id", "agent_id", "alert_timestamp", "alert_type", "severity",
            "suspicion_score", "rule_triggered", "evidence_payload", "notes"
        ])

    e = events.copy()
    e["current_snapshot_timestamp"] = pd.to_datetime(e["current_snapshot_timestamp"])
    e["inferred_change_timestamp"] = pd.to_datetime(e["inferred_change_timestamp"])
    e["is_short_aux"] = (
        (e["transition_type"] == "avail_to_aux")
        & (e["inferred_duration_seconds"] <= cfg.thresholds.short_aux_max_seconds)
    )

    alerts: list[dict] = []

    # Regla 1: auxiliar corto
    for _, row in e[e["is_short_aux"]].iterrows():
        score = cfg.weights.short_aux_event * row["confidence_score"]
        alerts.append({
            "alert_id": f"r1_{row['event_id']}",
            "agent_id": row["agent_id"],
            "alert_timestamp": row["current_snapshot_timestamp"],
            "alert_type": "short_aux",
            "severity": _severity(score),
            "suspicion_score": score,
            "rule_triggered": "rule_1_short_aux",
            "evidence_payload": json.dumps({"event_id": row["event_id"]}),
            "notes": "Entrada a auxiliar con duración inferida corta",
        })

    # Regla 2: retorno rápido a disponibilidad
    for _, aux_row in e[e["is_short_aux"]].iterrows():
        candidates = e[
            (e["agent_id"] == aux_row["agent_id"]) &
            (e["transition_type"] == "aux_to_avail") &
            (e["inferred_change_timestamp"] >= aux_row["inferred_change_timestamp"]) &
            (e["inferred_change_timestamp"] <= aux_row["inferred_change_timestamp"] + pd.Timedelta(seconds=cfg.thresholds.quick_return_window_seconds))
        ]
        if not candidates.empty:
            score = cfg.weights.quick_return_event * aux_row["confidence_score"]
            alerts.append({
                "alert_id": f"r2_{aux_row['event_id']}",
                "agent_id": aux_row["agent_id"],
                "alert_timestamp": candidates.iloc[0]["current_snapshot_timestamp"],
                "alert_type": "quick_return_to_avail",
                "severity": _severity(score),
                "suspicion_score": score,
                "rule_triggered": "rule_2_quick_return",
                "evidence_payload": json.dumps({
                    "source_short_aux_event": aux_row["event_id"],
                    "return_event": candidates.iloc[0]["event_id"],
                }),
                "notes": "Retorno rápido a estado disponible luego de auxiliar corto",
            })

    # Regla 3: patrón repetitivo
    short_aux = e[e["is_short_aux"]].copy()
    if not short_aux.empty:
        short_aux["hour_bucket"] = short_aux["inferred_change_timestamp"].dt.floor("h")
        hourly = short_aux.groupby(["agent_id", "hour_bucket"]).size().reset_index(name="count")
        for _, h in hourly[hourly["count"] >= cfg.thresholds.min_short_aux_per_hour].iterrows():
            score = cfg.weights.repetitive_hourly
            alerts.append({
                "alert_id": f"r3h_{h['agent_id']}_{h['hour_bucket']}",
                "agent_id": h["agent_id"],
                "alert_timestamp": h["hour_bucket"],
                "alert_type": "repetitive_short_aux_hourly",
                "severity": _severity(score),
                "suspicion_score": score,
                "rule_triggered": "rule_3_repetition_hour",
                "evidence_payload": json.dumps(h.to_dict(), default=str),
                "notes": "Exceso de auxiliares cortos por hora",
            })

        short_aux["date_bucket"] = short_aux["inferred_change_timestamp"].dt.date
        daily = short_aux.groupby(["agent_id", "date_bucket"]).size().reset_index(name="count")
        for _, d in daily[daily["count"] >= cfg.thresholds.min_short_aux_per_day].iterrows():
            score = cfg.weights.repetitive_daily
            alerts.append({
                "alert_id": f"r3d_{d['agent_id']}_{d['date_bucket']}",
                "agent_id": d["agent_id"],
                "alert_timestamp": datetime.combine(d["date_bucket"], datetime.min.time()),
                "alert_type": "repetitive_short_aux_daily",
                "severity": _severity(score),
                "suspicion_score": score,
                "rule_triggered": "rule_3_repetition_day",
                "evidence_payload": json.dumps(d.to_dict(), default=str),
                "notes": "Exceso de auxiliares cortos por día",
            })

    # Regla 4: refuerzos
    snap = snapshots.copy()
    snap["snapshot_timestamp"] = pd.to_datetime(snap["snapshot_timestamp"])
    snap = snap.sort_values(["agent_id", "snapshot_timestamp"])

    for agent_id, grp in e.groupby("agent_id"):
        aux_total = (grp["transition_type"] == "avail_to_aux").sum()
        short_total = grp["is_short_aux"].sum()
        if aux_total > 0 and (short_total / aux_total) >= cfg.thresholds.short_aux_ratio_threshold:
            score = cfg.weights.high_short_ratio
            alerts.append({
                "alert_id": f"r4ratio_{agent_id}",
                "agent_id": agent_id,
                "alert_timestamp": grp["current_snapshot_timestamp"].max(),
                "alert_type": "high_short_aux_ratio",
                "severity": _severity(score),
                "suspicion_score": score,
                "rule_triggered": "rule_4_high_short_aux_ratio",
                "evidence_payload": json.dumps({"short": int(short_total), "total_aux": int(aux_total)}),
                "notes": "Alto porcentaje de auxiliares cortos",
            })

    return pd.DataFrame(alerts).drop_duplicates(subset=["alert_id"]) if alerts else pd.DataFrame()
