import sqlite3
import os
from contextlib import contextmanager
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lotofacil.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS resultados (
                concurso INTEGER PRIMARY KEY,
                data TEXT NOT NULL,
                dezenas TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS palpites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_criacao TEXT NOT NULL DEFAULT (datetime('now')),
                concurso_alvo INTEGER NOT NULL,
                concurso_data TEXT,
                dezenas TEXT NOT NULL
            );
        """)
        _migrate_palpites(conn)


def _migrate_palpites(conn):
    cols = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(palpites)").fetchall()
    }
    if "concurso_data" not in cols:
        conn.execute("ALTER TABLE palpites ADD COLUMN concurso_data TEXT")


def is_db_empty() -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM resultados").fetchone()
        return row["cnt"] == 0


def get_last_concurso() -> Optional[int]:
    with get_db() as conn:
        row = conn.execute("SELECT MAX(concurso) as ultimo FROM resultados").fetchone()
        return row["ultimo"]


def get_total_concursos() -> int:
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM resultados").fetchone()
        return row["cnt"]


def inserir_palpite(concurso_alvo: int, dezenas: str, concurso_data: str = "") -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO palpites (concurso_alvo, concurso_data, dezenas) VALUES (?, ?, ?)",
            (concurso_alvo, concurso_data, dezenas),
        )
        return cursor.lastrowid


def listar_palpites(concurso_alvo: int) -> list:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, data_criacao, concurso_alvo, concurso_data, dezenas FROM palpites WHERE concurso_alvo = ? ORDER BY id",
            (concurso_alvo,),
        ).fetchall()
        return [dict(r) for r in rows]


def listar_todos_palpites(concurso_alvo: Optional[int] = None, limite: int = 100, offset: int = 0) -> list:
    with get_db() as conn:
        if concurso_alvo:
            rows = conn.execute(
                "SELECT id, data_criacao, concurso_alvo, concurso_data, dezenas "
                "FROM palpites WHERE concurso_alvo = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (concurso_alvo, limite, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, data_criacao, concurso_alvo, concurso_data, dezenas "
                "FROM palpites ORDER BY id DESC LIMIT ? OFFSET ?",
                (limite, offset),
            ).fetchall()
        return [dict(r) for r in rows]


def contar_palpites(concurso_alvo: Optional[int] = None) -> int:
    with get_db() as conn:
        if concurso_alvo:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM palpites WHERE concurso_alvo = ?",
                (concurso_alvo,),
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) as cnt FROM palpites").fetchone()
        return row["cnt"]


def deletar_palpite(palpite_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM palpites WHERE id = ?", (palpite_id,))
        return cursor.rowcount > 0


def obter_resultado(concurso: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT concurso, data, dezenas FROM resultados WHERE concurso = ?",
            (concurso,),
        ).fetchone()
        return dict(row) if row else None
