from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id TEXT PRIMARY KEY,
            snapshot_timestamp TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            agent_name TEXT,
            current_status TEXT NOT NULL,
            time_in_status_seconds INTEGER,
            login_time_seconds INTEGER,
            continuous_login_time_seconds INTEGER,
            hold_seconds INTEGER,
            acw_seconds INTEGER,
            inbound_calls INTEGER,
            outbound_calls INTEGER,
            coaching_seconds INTEGER,
            admin_task_seconds INTEGER,
            break_seconds INTEGER,
            tmo_seconds INTEGER,
            ready_time_total_seconds INTEGER,
            aux_time_total_seconds INTEGER,
            handle_time_seconds INTEGER,
            transfers INTEGER,
            raw_payload TEXT
        );

        CREATE TABLE IF NOT EXISTS inferred_events (
            event_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            previous_snapshot_timestamp TEXT NOT NULL,
            current_snapshot_timestamp TEXT NOT NULL,
            previous_status TEXT NOT NULL,
            current_status TEXT NOT NULL,
            inferred_change_timestamp TEXT NOT NULL,
            inferred_duration_seconds INTEGER,
            transition_type TEXT,
            aux_category TEXT,
            confidence_score REAL,
            evidence_payload TEXT
        );

        CREATE TABLE IF NOT EXISTS alerts (
            alert_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            alert_timestamp TEXT NOT NULL,
            alert_type TEXT,
            severity TEXT,
            suspicion_score REAL,
            rule_triggered TEXT,
            evidence_payload TEXT,
            notes TEXT
        );
        """
    )
    conn.commit()


def write_dataframe(conn: sqlite3.Connection, df: pd.DataFrame, table: str, if_exists: str = "append") -> None:
    df.to_sql(table, conn, index=False, if_exists=if_exists)


def read_table(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    return pd.read_sql_query(f"SELECT * FROM {table}", conn)
