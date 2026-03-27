from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def build_general_summary(agent_metrics: pd.DataFrame, events: pd.DataFrame, alerts: pd.DataFrame) -> dict:
    return {
        "agents_total": int(agent_metrics["agent_id"].nunique()) if not agent_metrics.empty else 0,
        "events_total": int(len(events)),
        "alerts_total": int(len(alerts)),
        "agents_with_alerts": int(alerts["agent_id"].nunique()) if not alerts.empty else 0,
        "top_suspicion_score": float(agent_metrics["suspicion_score_final"].max()) if not agent_metrics.empty else 0.0,
    }


def export_outputs(
    output_dir: Path,
    snapshots: pd.DataFrame,
    events: pd.DataFrame,
    alerts: pd.DataFrame,
    metrics: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshots.to_csv(output_dir / "snapshots_normalized.csv", index=False)
    events.to_csv(output_dir / "inferred_events.csv", index=False)
    alerts.to_csv(output_dir / "alerts.csv", index=False)
    metrics.to_csv(output_dir / "agent_metrics.csv", index=False)

    ranking = metrics.sort_values("suspicion_score_final", ascending=False)
    ranking.to_csv(output_dir / "ranking_global.csv", index=False)

    summary = build_general_summary(metrics, events, alerts)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    with pd.ExcelWriter(output_dir / "report.xlsx", engine="openpyxl") as writer:
        snapshots.to_excel(writer, sheet_name="snapshots", index=False)
        events.to_excel(writer, sheet_name="events", index=False)
        alerts.to_excel(writer, sheet_name="alerts", index=False)
        metrics.to_excel(writer, sheet_name="agent_metrics", index=False)
        ranking.to_excel(writer, sheet_name="ranking", index=False)
