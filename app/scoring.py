from __future__ import annotations

import pandas as pd


def compute_agent_metrics(snapshots: pd.DataFrame, events: pd.DataFrame, alerts: pd.DataFrame) -> pd.DataFrame:
    if snapshots.empty:
        return pd.DataFrame()

    s = snapshots.copy()
    s["snapshot_timestamp"] = pd.to_datetime(s["snapshot_timestamp"])

    e = events.copy()
    if not e.empty:
        e["inferred_change_timestamp"] = pd.to_datetime(e["inferred_change_timestamp"])

    by_agent = s.groupby("agent_id", dropna=False).agg(
        agent_name=("agent_name", "last"),
        max_login=("login_time_seconds", "max"),
        max_ready=("ready_time_total_seconds", "max"),
        max_aux=("aux_time_total_seconds", "max"),
        snapshots_count=("snapshot_id", "count"),
        first_seen=("snapshot_timestamp", "min"),
        last_seen=("snapshot_timestamp", "max"),
    ).reset_index()

    if e.empty:
        by_agent["total_aux_entries"] = 0
        by_agent["short_aux_count"] = 0
        by_agent["avg_aux_duration_seconds"] = 0.0
        by_agent["median_aux_duration_seconds"] = 0.0
        by_agent["pct_short_aux"] = 0.0
        by_agent["transitions_per_hour"] = 0.0
    else:
        aux_entries = e[e["transition_type"] == "avail_to_aux"]
        short_aux = aux_entries[aux_entries["inferred_duration_seconds"] <= 60]

        agg_aux = aux_entries.groupby("agent_id").agg(
            total_aux_entries=("event_id", "count"),
            avg_aux_duration_seconds=("inferred_duration_seconds", "mean"),
            median_aux_duration_seconds=("inferred_duration_seconds", "median"),
        )
        agg_short = short_aux.groupby("agent_id").agg(short_aux_count=("event_id", "count"))
        trans = e.groupby("agent_id").agg(total_transitions=("event_id", "count"))

        by_agent = by_agent.merge(agg_aux, on="agent_id", how="left")
        by_agent = by_agent.merge(agg_short, on="agent_id", how="left")
        by_agent = by_agent.merge(trans, on="agent_id", how="left")

        by_agent[["total_aux_entries", "short_aux_count", "total_transitions"]] = (
            by_agent[["total_aux_entries", "short_aux_count", "total_transitions"]].fillna(0)
        )
        by_agent[["avg_aux_duration_seconds", "median_aux_duration_seconds"]] = (
            by_agent[["avg_aux_duration_seconds", "median_aux_duration_seconds"]].fillna(0.0)
        )
        by_agent["pct_short_aux"] = by_agent.apply(
            lambda r: (r["short_aux_count"] / r["total_aux_entries"]) if r["total_aux_entries"] else 0.0,
            axis=1,
        )
        hours = (by_agent["last_seen"] - by_agent["first_seen"]).dt.total_seconds().clip(lower=1) / 3600
        by_agent["transitions_per_hour"] = by_agent["total_transitions"] / hours

    by_agent["ready_vs_login_ratio"] = by_agent.apply(
        lambda r: (r["max_ready"] / r["max_login"]) if r["max_login"] else 0.0,
        axis=1,
    )
    by_agent["aux_vs_login_ratio"] = by_agent.apply(
        lambda r: (r["max_aux"] / r["max_login"]) if r["max_login"] else 0.0,
        axis=1,
    )

    if alerts.empty:
        by_agent["suspicion_score_final"] = 0.0
    else:
        score = alerts.groupby("agent_id").agg(suspicion_score_final=("suspicion_score", "sum")).reset_index()
        by_agent = by_agent.merge(score, on="agent_id", how="left")
        by_agent["suspicion_score_final"] = by_agent["suspicion_score_final"].fillna(0.0)

    return by_agent.sort_values("suspicion_score_final", ascending=False).reset_index(drop=True)
