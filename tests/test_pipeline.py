from pathlib import Path

from app.config import load_default_config
from app.event_reconstruction import reconstruct_events
from app.parsers import parse_snapshot_folder
from app.rules import run_rules
from app.scoring import compute_agent_metrics


def _write_csv(path: Path, rows: str) -> None:
    path.write_text(rows, encoding="utf-8")


def test_snapshot_pipeline(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()

    _write_csv(
        data / "snapshot_2026-03-26_14-00-00.csv",
        "Nombre,Employee Id,Current Status,Time in Status,Login Time,Ready Time,Auxiliares,Llamadas\n"
        "Agent A,1,Ready,00:10:00,02:00:00,01:30:00,00:20:00,5\n",
    )
    _write_csv(
        data / "snapshot_2026-03-26_14-01-00.csv",
        "Nombre,Employee Id,Current Status,Time in Status,Login Time,Ready Time,Auxiliares,Llamadas\n"
        "Agent A,1,Auxiliar,00:00:20,02:01:00,01:30:10,00:20:20,5\n",
    )
    _write_csv(
        data / "snapshot_2026-03-26_14-02-00.csv",
        "Nombre,Employee Id,Current Status,Time in Status,Login Time,Ready Time,Auxiliares,Llamadas\n"
        "Agent A,1,Ready,00:00:15,02:02:00,01:31:00,00:20:20,6\n",
    )

    cfg = load_default_config()
    snapshots = parse_snapshot_folder(data, cfg)
    events = reconstruct_events(snapshots, cfg)
    alerts = run_rules(events, snapshots, cfg)
    metrics = compute_agent_metrics(snapshots, events, alerts)

    assert len(snapshots) == 3
    assert (events["transition_type"] == "avail_to_aux").any()
    assert (alerts["alert_type"] == "short_aux").any()
    assert float(metrics.iloc[0]["suspicion_score_final"]) > 0
