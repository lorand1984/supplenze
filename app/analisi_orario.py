from collections import defaultdict
from typing import List, Tuple, Dict, Set
from app.models import Docente

def analizza_copertura_D(
    docenti: List[Docente],
    giorni: int = 5,
    ore: int = 7
) -> Tuple[List[Tuple[int, int]], Dict[Tuple[int, int], Set[str]]]:
    """
    Analizza l'orario dei docenti e restituisce:
    1. Lista di (giorno, ora) in cui nessun docente ha una "D".
    2. Dizionario (giorno, ora) -> set di nomi docenti con "D" in quella ora.

    Args:
        docenti: lista di oggetti Docente.
        giorni: numero di giorni della settimana (default 5).
        ore: numero di ore per giorno (default 7).

    Returns:
        (ore_scoperte, copertura)
    """
    copertura: Dict[Tuple[int, int], Set[str]] = defaultdict(set)

    for docente in docenti:
        for (g, o), valore in docente.orario.items():
            if valore == "D":
                copertura[(g, o)].add(docente.nome)

    ore_scoperte = []
    for giorno in range(1, giorni + 1):
        for ora in range(1, ore + 1):
            if (giorno, ora) not in copertura:
                ore_scoperte.append((giorno, ora))

    return ore_scoperte, dict(copertura)