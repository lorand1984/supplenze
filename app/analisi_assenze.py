# app/analisi_assenze.py

from datetime import date
from typing import List, Dict, Tuple
from app.models import Docente, Assenza, VisitaIstruzione


def ore_classe_in_data(
    data: date,
    classe: str,
    docenti: List[Docente],
    visite: List[VisitaIstruzione]
) -> set:
    """Restituisce le ore effettive di lezione di una classe in una data (escluse le visite)."""
    giorno = data.weekday() + 1
    ore = set()
    for d in docenti:
        for (g, o), val in d.orario.items():
            if g == giorno and val == classe:
                ore.add(o)
    for v in visite:
        if v.data == data and v.classe == classe:
            ore -= set(v.ore_interessate())
    return ore


def analizza_assenze(
    docenti: List[Docente],
    assenze: List[Assenza],
    visite: List[VisitaIstruzione],
    ore_giornaliere: int = 6
) -> Tuple[List[Dict], List[Dict]]:
    """
    Restituisce due liste:
    - ignorate (US20): ore in cui il docente non aveva lezione (o era in visita).
    - senza_supplenza (US26): ore di lezione con preavviso >=48h e prima/ultima della classe.
    """
    doc_map = {d.nome: d for d in docenti}
    ignorate = []
    senza_supplenza = []

    for ass in assenze:
        docente = doc_map.get(ass.docente_nome)
        if not docente:
            ignorate.append({
                'docente': ass.docente_nome,
                'data': ass.data.isoformat(),
                'ora': f"{ass.ora_inizio}-{ass.ora_fine}",
                'classe': None,
                'motivo': "Docente non presente nell'orario"
            })
            continue

        giorno = ass.data.weekday() + 1

        for ora in ass.ore_interessate():
            classe = docente.get_classe(giorno, ora)

            # US20: nessuna lezione in quest'ora
            if classe is None:
                ignorate.append({
                    'docente': ass.docente_nome,
                    'data': ass.data.isoformat(),
                    'ora': ora,
                    'classe': None,
                    'motivo': "Il docente non aveva lezione in quest'ora"
                })
                continue

            # US20: classe in visita
            in_visita = any(
                v for v in visite
                if v.data == ass.data and ora in v.ore_interessate() and v.classe == classe
            )
            if in_visita:
                ignorate.append({
                    'docente': ass.docente_nome,
                    'data': ass.data.isoformat(),
                    'ora': ora,
                    'classe': classe,
                    'motivo': "La classe era in visita di istruzione"
                })
                continue

            # US26: preavviso sufficiente + prima/ultima ora
            if ass.preavviso_sufficiente:
                ore_classe = ore_classe_in_data(ass.data, classe, docenti, visite)
                if ore_classe:
                    prima = min(ore_classe)
                    ultima = max(ore_classe)
                    if ora == prima or ora == ultima:
                        posizione = "prima" if ora == prima else "ultima"
                        senza_supplenza.append({
                            'docente': ass.docente_nome,
                            'data': ass.data.isoformat(),
                            'ora': ora,
                            'classe': classe,
                            'motivo': f"Preavviso ≥48h e ora {posizione} della classe"
                        })

    return ignorate, senza_supplenza