# Detector de posible "renovación de avail" (snapshot-first)

Base inicial funcional en Python para analizar snapshots CSV de contact center, reconstruir transiciones inferidas y generar alertas de sospecha estadística (sin afirmar causalidad).

## Arquitectura propuesta

La solución está separada por capas:

1. **Ingesta/Parsing (`app/parsers.py`)**
   - Lee todos los CSV de una carpeta.
   - Prueba delimitadores `,`, `;`, `\t`, `|`.
   - Extrae `snapshot_timestamp` desde el nombre del archivo con patrones configurables.

2. **Normalización (`app/normalizers.py`)**
   - Normaliza nombres de columnas.
   - Convierte duraciones `HH:MM:SS` a segundos.
   - Estandariza estados para matching robusto.

3. **Persistencia (`app/storage.py`)**
   - SQLite local.
   - Tablas: `snapshots`, `inferred_events`, `alerts`.

4. **Reconstrucción de eventos (`app/event_reconstruction.py`)**
   - Compara snapshots consecutivos por agente.
   - Infere timestamp de cambio usando `time_in_status_seconds` del snapshot actual.
   - Marca menor confianza cuando la brecha entre snapshots es grande.

5. **Reglas (`app/rules.py`)**
   - Regla 1: auxiliar corto.
   - Regla 2: retorno rápido a disponibilidad.
   - Regla 3: repetición por hora/día.
   - Regla 4: alto ratio de auxiliares cortos.

6. **Scoring/Métricas (`app/scoring.py`)**
   - Métricas por agente y score final acumulado.

7. **Reportes (`app/reports.py`)**
   - Exporta CSV + Excel + JSON resumen.

8. **CLI (`app/cli.py`)**
   - Orquesta todo el pipeline de punta a punta.

## Diseño dual (snapshot vs event-log)

La config incluye `ingestion_mode`:
- `snapshot` (implementado): reconstrucción inferida desde fotos periódicas.
- `event_log` (preparado para evolución): estructura y tablas compatibles para incorporar una fuente de eventos nativos después.

## Estructura de carpetas

```text
project/
├── app/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── event_reconstruction.py
│   ├── models.py
│   ├── normalizers.py
│   ├── parsers.py
│   ├── reports.py
│   ├── rules.py
│   ├── scoring.py
│   └── storage.py
├── data/
│   └── examples/
├── outputs/
├── tests/
│   └── test_pipeline.py
├── requirements.txt
└── README.md
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso rápido

```bash
python -m app.cli run --input-dir data/examples --output-dir outputs --db-path outputs/avail_detector.db
```

Salidas esperadas en `outputs/`:
- `snapshots_normalized.csv`
- `inferred_events.csv`
- `alerts.csv`
- `agent_metrics.csv`
- `ranking_global.csv`
- `summary.json`
- `report.xlsx`

## Configuración

Todos los supuestos principales están centralizados en `app/config.py`:

- Mapping de columnas reales -> nombres normalizados.
- Estados disponibles y auxiliares.
- Patrones regex de timestamp en nombre de archivo.
- Umbrales de reglas:
  - `short_aux_max_seconds`
  - `quick_return_window_seconds`
  - repetición por hora/día
  - ratio de auxiliar corto
- Pesos para scoring.

## Ejemplo de input

Archivos como:
- `CalculadorStartekTRF_20260326_140500.csv`
- `snapshot_2026-03-26_14-05-00.csv`

Con columnas tipo:
- `Nombre`, `Employee Id`, `Current Status`, `Time in Status`, `Login Time`, `Ready Time`, `Auxiliares`, etc.

## Ejemplo de output (conceptual)

`alerts.csv`:

| alert_id | agent_id | alert_type | suspicion_score | rule_triggered |
|---|---|---|---:|---|
| r1_... | 45678 | short_aux | 0.95 | rule_1_short_aux |
| r2_... | 45678 | quick_return_to_avail | 1.14 | rule_2_quick_return |

`agent_metrics.csv`:

| agent_id | total_aux_entries | short_aux_count | pct_short_aux | suspicion_score_final |
|---|---:|---:|---:|---:|
| 45678 | 4 | 3 | 0.75 | 6.09 |

## Limitaciones metodológicas (importantes)

1. **Un snapshot aislado no prueba manipulación**.
2. **Brechas largas entre snapshots degradan precisión temporal**.
3. **Eventos muy cortos pueden no observarse** si la frecuencia de captura es baja.
4. El output representa:
   - dato observado,
   - inferencia probable,
   - sospecha estadística,
   y **no una conclusión disciplinaria automática**.

## Tests

```bash
pytest -q
```

Incluye un test de pipeline extremo a extremo con 3 snapshots sintéticos.
