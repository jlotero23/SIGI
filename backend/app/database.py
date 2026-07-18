"""Persistencia SQLite para ejecuciones, pronósticos y recomendaciones."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from .config import DB_PATH, DATA_DIR


def init_db() -> None:
    """Crea las tablas si no existen."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                details_json TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER,
                producto TEXT NOT NULL,
                fecha TEXT NOT NULL,
                demanda_real REAL,
                demanda_pronosticada REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (execution_id) REFERENCES executions(id)
            );

            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER,
                producto TEXT NOT NULL,
                categoria TEXT,
                demanda_pronosticada REAL,
                cantidad_sugerida INTEGER NOT NULL,
                punto_reorden REAL,
                stock_seguridad REAL,
                prioridad TEXT,
                fecha_sugerida TEXT,
                justificacion TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (execution_id) REFERENCES executions(id)
            );

            CREATE TABLE IF NOT EXISTS agent_status (
                agent TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_run TEXT,
                message TEXT
            );
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO agent_status (agent, status, last_run, message) VALUES (?, ?, ?, ?)",
            ("agent1_forecast", "idle", None, "Esperando ejecución"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO agent_status (agent, status, last_run, message) VALUES (?, ?, ?, ?)",
            ("agent2_replenishment", "idle", None, "Esperando pronósticos"),
        )


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def log_execution(agent: str, status: str, message: str = "", details: dict | None = None) -> int:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO executions (agent, status, message, details_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agent, status, message, json.dumps(details or {}, ensure_ascii=False), now),
        )
        return int(cur.lastrowid)


def update_agent_status(agent: str, status: str, message: str) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO agent_status (agent, status, last_run, message)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(agent) DO UPDATE SET status=excluded.status, last_run=excluded.last_run, message=excluded.message
            """,
            (agent, status, now, message),
        )


def get_agent_statuses() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM agent_status").fetchall()
    return [dict(r) for r in rows]


def save_forecasts(execution_id: int, records: list[dict]) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        for r in records:
            conn.execute(
                """
                INSERT INTO forecasts (execution_id, producto, fecha, demanda_real, demanda_pronosticada, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    r["producto"],
                    r["fecha"],
                    r.get("demanda_real"),
                    r["demanda_pronosticada"],
                    now,
                ),
            )


def save_recommendations(execution_id: int, records: list[dict]) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        for r in records:
            conn.execute(
                """
                INSERT INTO recommendations (
                    execution_id, producto, categoria, demanda_pronosticada,
                    cantidad_sugerida, punto_reorden, stock_seguridad, prioridad,
                    fecha_sugerida, justificacion, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    r["producto"],
                    r.get("categoria"),
                    r.get("demanda_pronosticada"),
                    r["cantidad_sugerida"],
                    r.get("punto_reorden"),
                    r.get("stock_seguridad"),
                    r.get("prioridad"),
                    r.get("fecha_sugerida"),
                    r.get("justificacion"),
                    now,
                ),
            )


def get_latest_forecasts(limit: int = 500) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT f.* FROM forecasts f
            INNER JOIN (
                SELECT MAX(execution_id) AS max_id FROM forecasts
            ) latest ON f.execution_id = latest.max_id
            ORDER BY f.fecha, f.producto
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_latest_recommendations() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.* FROM recommendations r
            INNER JOIN (
                SELECT MAX(execution_id) AS max_id FROM recommendations
            ) latest ON r.execution_id = latest.max_id
            ORDER BY
                CASE r.prioridad WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END,
                r.cantidad_sugerida DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_execution_history(limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM executions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    result = []
    for r in rows:
        item = dict(r)
        if item.get("details_json"):
            item["details"] = json.loads(item["details_json"])
        result.append(item)
    return result
