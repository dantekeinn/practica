from __future__ import annotations

from pathlib import Path

import typer

from app.config import load_default_config
from app.event_reconstruction import reconstruct_events
from app.parsers import parse_snapshot_folder
from app.reports import export_outputs
from app.rules import run_rules
from app.scoring import compute_agent_metrics
from app.storage import get_connection, init_db, write_dataframe

cli = typer.Typer(help="Detector de posible renovación de avail desde snapshots CSV")


@cli.command()
def run(
    input_dir: Path = typer.Option(Path("data"), exists=True, file_okay=False, help="Carpeta con CSV"),
    output_dir: Path = typer.Option(Path("outputs"), file_okay=False, help="Carpeta de salida"),
    db_path: Path = typer.Option(Path("outputs/avail_detector.db"), help="Ruta SQLite"),
) -> None:
    cfg = load_default_config()
    cfg.input_dir = input_dir
    cfg.output_dir = output_dir
    cfg.database_path = db_path

    typer.echo(f"[1/6] Parseando snapshots desde {input_dir}...")
    snapshots = parse_snapshot_folder(input_dir, cfg)

    typer.echo("[2/6] Inicializando base SQLite...")
    conn = get_connection(cfg.database_path)
    init_db(conn)
    write_dataframe(conn, snapshots, "snapshots", if_exists="replace")

    typer.echo("[3/6] Reconstruyendo eventos inferidos...")
    events = reconstruct_events(snapshots, cfg)
    if not events.empty:
        write_dataframe(conn, events, "inferred_events", if_exists="replace")

    typer.echo("[4/6] Ejecutando reglas de detección...")
    alerts = run_rules(events, snapshots, cfg)
    if not alerts.empty:
        write_dataframe(conn, alerts, "alerts", if_exists="replace")

    typer.echo("[5/6] Calculando métricas y scoring final...")
    metrics = compute_agent_metrics(snapshots, events, alerts)

    typer.echo(f"[6/6] Exportando reportes en {output_dir}...")
    export_outputs(output_dir, snapshots, events, alerts, metrics)

    conn.close()
    typer.echo("Proceso completado.")


if __name__ == "__main__":
    cli()
