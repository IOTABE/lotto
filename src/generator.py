import random
import itertools
from typing import List, Optional
from src.database import get_db

PRIMES = {2, 3, 5, 7, 11, 13, 17, 19, 23}
BORDER = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}
ALL_NUMBERS = list(range(1, 26))


def _count_odd(numeros: List[int]) -> int:
    return sum(1 for n in numeros if n % 2 == 1)


def _count_even(numeros: List[int]) -> int:
    return 15 - _count_odd(numeros)


def _count_primes(numeros: List[int]) -> int:
    return sum(1 for n in numeros if n in PRIMES)


def _count_border(numeros: List[int]) -> int:
    return sum(1 for n in numeros if n in BORDER)


def _get_previous_draw(concurso_alvo: int) -> Optional[List[int]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT dezenas FROM resultados WHERE concurso = ?",
            (concurso_alvo - 1,),
        ).fetchone()
        if row:
            return [int(x) for x in row[0].split(",")]
    return None


def _count_repeated(combination: List[int], previous: List[int]) -> int:
    return len(set(combination) & set(previous))


def check_filters(combination: List[int], previous: Optional[List[int]] = None) -> bool:
    odd = _count_odd(combination)
    even = _count_even(combination)
    if abs(odd - even) != 1:
        return False

    prime_count = _count_primes(combination)
    if prime_count not in (5, 6):
        return False

    border_count = _count_border(combination)
    if border_count not in (9, 10):
        return False

    if previous is not None:
        repeated = _count_repeated(combination, previous)
        if not (8 <= repeated <= 10):
            return False

    return True


def generate_palpites(concurso_alvo: int, quantidade: int = 10) -> List[List[int]]:
    previous = _get_previous_draw(concurso_alvo)
    palpites = []
    seen = set()
    max_attempts = 200_000
    attempts = 0

    while len(palpites) < quantidade and attempts < max_attempts:
        attempts += 1
        combination = tuple(sorted(random.sample(ALL_NUMBERS, 15)))

        if combination in seen:
            continue
        seen.add(combination)

        if check_filters(list(combination), previous):
            palpites.append(list(combination))

    return palpites


def gerar_fechamento(
    concurso_alvo: int, numeros_matriz: List[int]
) -> List[List[int]]:
    if len(numeros_matriz) < 17 or len(numeros_matriz) > 20:
        raise ValueError("A matriz deve conter entre 17 e 20 números.")

    unique_numbers = sorted(set(numeros_matriz))
    if len(unique_numbers) < 17:
        raise ValueError(
            f"A matriz possui apenas {len(unique_numbers)} números únicos (mínimo 17)."
        )

    previous = _get_previous_draw(concurso_alvo)
    results = []
    seen = set()

    for combo in itertools.combinations(unique_numbers, 15):
        if combo in seen:
            continue
        seen.add(combo)

        combination = list(combo)
        if check_filters(combination, previous):
            results.append(combination)

    return results


def explicar_filtros(combinacao: List[int], concurso_alvo: int) -> dict:
    previous = _get_previous_draw(concurso_alvo)
    odd = _count_odd(combinacao)
    even = _count_even(combinacao)
    primes = _count_primes(combinacao)
    border = _count_border(combinacao)
    repeated = _count_repeated(combinacao, previous) if previous else None

    return {
        "pares": even,
        "impares": odd,
        "primos": primes,
        "moldura": border,
        "repetidos": repeated,
        "valido": check_filters(combinacao, previous),
    }
