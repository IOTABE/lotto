import requests
import time
from typing import Optional
from src.database import get_db, is_db_empty, get_last_concurso

API_BASE = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 3

SEED_DATA = [
    (1, "29/09/2003", [1, 2, 4, 5, 7, 8, 9, 10, 12, 14, 15, 18, 20, 21, 24]),
    (2, "06/10/2003", [4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 17, 19, 22, 23]),
    (3, "13/10/2003", [1, 2, 3, 4, 6, 9, 11, 12, 13, 14, 15, 18, 20, 23, 25]),
    (4, "20/10/2003", [1, 2, 5, 7, 8, 9, 10, 12, 13, 15, 16, 18, 21, 22, 24]),
    (5, "27/10/2003", [2, 3, 4, 5, 8, 9, 11, 12, 14, 15, 18, 19, 21, 24, 25]),
    (6, "03/11/2003", [1, 3, 5, 6, 8, 10, 12, 13, 14, 16, 17, 19, 22, 23, 25]),
    (7, "10/11/2003", [2, 4, 6, 7, 9, 10, 11, 13, 15, 17, 18, 20, 22, 24, 25]),
    (8, "17/11/2003", [1, 2, 3, 5, 7, 9, 11, 12, 14, 16, 18, 20, 22, 23, 25]),
    (9, "24/11/2003", [3, 4, 6, 8, 10, 11, 13, 14, 15, 16, 17, 19, 21, 23, 24]),
    (10, "01/12/2003", [1, 5, 6, 7, 9, 11, 12, 13, 16, 17, 18, 19, 20, 22, 24]),
]


def parse_dezenas(dezenas_list: list) -> str:
    cleaned = [str(int(d)) for d in dezenas_list]
    cleaned.sort(key=int)
    return ",".join(cleaned)


def fetch_all_results() -> Optional[list]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(API_BASE, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                return data
            return None
        except requests.Timeout:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
                continue
            raise
        except requests.ConnectionError:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
                continue
            raise
        except requests.RequestException:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
                continue
            raise
    return None


def _load_seed_data():
    with get_db() as conn:
        for concurso, data, dezenas in SEED_DATA:
            dezenas_str = parse_dezenas(dezenas)
            conn.execute(
                "INSERT OR IGNORE INTO resultados (concurso, data, dezenas) VALUES (?, ?, ?)",
                (concurso, data, dezenas_str),
            )


def sync_results() -> dict:
    added = 0
    updated = 0
    errors = []

    try:
        data = fetch_all_results()
    except Exception as e:
        return {
            "status": "error",
            "message": f"Falha na conexão com a API após {MAX_RETRIES} tentativas: {e}",
        }

    if not data:
        return {
            "status": "error",
            "message": "API retornou dados vazios ou inválidos.",
        }

    last_local = get_last_concurso()

    with get_db() as conn:
        for concurso in data:
            try:
                concurso_num = int(concurso["concurso"])
                dezenas_str = parse_dezenas(concurso["dezenas"])
                data_str = concurso["data"]

                if last_local is None or concurso_num > last_local:
                    conn.execute(
                        "INSERT OR REPLACE INTO resultados (concurso, data, dezenas) VALUES (?, ?, ?)",
                        (concurso_num, data_str, dezenas_str),
                    )
                    if last_local is not None:
                        added += 1
                elif concurso_num <= last_local:
                    conn.execute(
                        "INSERT OR REPLACE INTO resultados (concurso, data, dezenas) VALUES (?, ?, ?)",
                        (concurso_num, data_str, dezenas_str),
                    )
                    updated += 1
            except (KeyError, ValueError, TypeError) as e:
                errors.append(f"Erro ao processar concurso {concurso.get('concurso', '?')}: {e}")
                continue

    if not last_local:
        added = len(data)

    return {
        "status": "ok",
        "added": added,
        "updated": updated,
        "total": len(data),
        "errors": errors,
    }


def ensure_data_loaded() -> dict:
    if is_db_empty():
        try:
            result = sync_results()
            if result["status"] == "ok":
                return result
            _load_seed_data()
            return {
                "status": "ok",
                "message": "API indisponível. Dados seed carregados (10 concursos históricos). Use o botão Sincronizar para obter dados completos.",
                "seed_only": True,
            }
        except Exception as e:
            _load_seed_data()
            return {
                "status": "ok",
                "message": f"Erro ao conectar à API: {e}. Dados seed carregados.",
                "seed_only": True,
            }
    return {"status": "ok", "message": "Dados já carregados no banco local."}
