from typing import List, Optional
from src.database import obter_resultado, listar_palpites


def conferir_palpites(concurso: int) -> Optional[dict]:
    resultado = obter_resultado(concurso)
    if not resultado:
        return None

    dezenas_resultado = {int(x) for x in resultado["dezenas"].split(",")}
    palpites = listar_palpites(concurso)

    if not palpites:
        return {
            "concurso": concurso,
            "data": resultado["data"],
            "dezenas_sorteadas": sorted(dezenas_resultado),
            "bilhetes": [],
        }

    bilhetes = []
    for p in palpites:
        dezenas_palpite = [int(x) for x in p["dezenas"].split(",")]
        acertos = len(set(dezenas_palpite) & dezenas_resultado)
        bilhetes.append(
            {
                "id": p["id"],
                "data_criacao": p["data_criacao"],
                "concurso_alvo": p["concurso_alvo"],
                "concurso_data": p.get("concurso_data", ""),
                "dezenas": dezenas_palpite,
                "acertos": acertos,
            }
        )

    return {
        "concurso": concurso,
        "data": resultado["data"],
        "dezenas_sorteadas": sorted(dezenas_resultado),
        "bilhetes": bilhetes,
    }
