from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class SnapshotRecord(BaseModel):
    snapshot_id: str
    snapshot_timestamp: datetime
    agent_id: str
    agent_name: str | None = None
    current_status: str
    time_in_status_seconds: int = 0
    login_time_seconds: int = 0
    continuous_login_time_seconds: int = 0
    hold_seconds: int = 0
    acw_seconds: int = 0
    inbound_calls: int = 0
    outbound_calls: int = 0
    coaching_seconds: int = 0
    admin_task_seconds: int = 0
    break_seconds: int = 0
    tmo_seconds: int = 0
    ready_time_total_seconds: int = 0
    aux_time_total_seconds: int = 0
    handle_time_seconds: int = 0
    transfers: int = 0
    raw_payload: str = "{}"


class InferredEvent(BaseModel):
    event_id: str
    agent_id: str
    previous_snapshot_timestamp: datetime
    current_snapshot_timestamp: datetime
    previous_status: str
    current_status: str
    inferred_change_timestamp: datetime
    inferred_duration_seconds: int = 0
    transition_type: str
    aux_category: str | None = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_payload: str = "{}"


class AlertRecord(BaseModel):
    alert_id: str
    agent_id: str
    alert_timestamp: datetime
    alert_type: str
    severity: str
    suspicion_score: float
    rule_triggered: str
    evidence_payload: str = "{}"
    notes: str | None = None
