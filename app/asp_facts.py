from typing import List, Optional
from datetime import date
from app.models import Docente, Assenza, VisitaIstruzione

def generate_asp_facts(
    docenti: List[Docente],
    assenze: List[Assenza],
    visite: Optional[List[VisitaIstruzione]] = None,
    ore_giornaliere: int = 6
) -> str:
    """
    Genera una stringa contenente i fatti ASP a partire dai modelli Python.
    I fatti generati sono:
      - lezione(docente, giorno, ora, classe)
      - disponibile(docente, giorno, ora)
      - assenza(docente, giorno, inizio, fine, preavviso)  (preavviso: true/false)
      - visita(classe, giorno, inizio, fine)               (intera giornata)
      - disponibilita_totale(docente, numero)              (ore totali "D" del docente)
      - insegna_in_classe(docente, classe)                 (docente insegna in quella classe)
    Il giorno è il numero del giorno della settimana (1=Lunedì ... 5=Venerdì).
    Tutti i nomi (docenti e classi) sono racchiusi tra doppi apici.
    """
    if visite is None:
        visite = []

    lines = []

    # Helper per quotare sempre le stringhe
    def quote(s: str) -> str:
        return f'"{s}"'

    # ------------------------------------------------------------------
    # Fatti lezione, disponibile, e raccolta per disponibilita_totale e insegna_in_classe
    # ------------------------------------------------------------------
    conteggio_disponibilita = {}  # docente -> totale ore "D"
    coppie_insegna = set()        # (docente, classe) per evitare duplicati

    for doc in docenti:
        nome_doc = quote(doc.nome)
        # Inizializza conteggio per questo docente
        conteggio_disponibilita[nome_doc] = 0

        for (giorno, ora), valore in doc.orario.items():
            if valore is None:
                continue
            if valore == "D":
                lines.append(f'disponibile({nome_doc}, {giorno}, {ora}).')
                conteggio_disponibilita[nome_doc] += 1
            else:
                classe = quote(valore)
                lines.append(f'lezione({nome_doc}, {giorno}, {ora}, {classe}).')
                coppie_insegna.add((nome_doc, classe))

    # Fatti disponibilita_totale
    for docente, totale in conteggio_disponibilita.items():
        lines.append(f'disponibilita_totale({docente}, {totale}).')

    # Fatti insegna_in_classe
    for (docente, classe) in coppie_insegna:
        lines.append(f'insegna_in_classe({docente}, {classe}).')

    # ------------------------------------------------------------------
    # Fatti assenza
    # ------------------------------------------------------------------
    for ass in assenze:
        giorno = ass.data.weekday() + 1
        if giorno > 5:
            continue  # sabato/domingo ignorati
        docente = quote(ass.docente_nome)
        preavviso = "true" if ass.preavviso_sufficiente else "false"
        lines.append(
            f'assenza({docente}, {giorno}, {ass.ora_inizio}, {ass.ora_fine}, {preavviso}).'
        )

    # ------------------------------------------------------------------
    # Fatti visita (intera giornata)
    # ------------------------------------------------------------------
    for vis in visite:
        giorno = vis.data.weekday() + 1
        if giorno > 5:
            continue
        classe = quote(vis.classe)
        lines.append(
            f'visita({classe}, {giorno}, 1, {ore_giornaliere}).'
        )

    return "\n".join(lines)