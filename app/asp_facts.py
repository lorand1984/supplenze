# app/asp_facts.py

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
    Genera i fatti ASP:
      - lezione(Docente, Giorno, Ora, Classe)
      - disponibile(Docente, Giorno, Ora)
      - compresenza(ITP, DocenteMateria, Giorno, Ora, Classe)
      - assenza(Docente, Giorno, Inizio, Fine, Preavviso)
      - visita(Classe, Giorno, Inizio, Fine)
      - disponibilita_totale(Docente, N)
      - insegna_in_classe(Docente, Classe)
    La priorità ITP > sostegno è gestita a monte: per ogni
    (giorno, ora, classe, docente_materia) viene generata una sola compresenza.
    """
    if visite is None:
        visite = []

    lines = []

    def quote(s: str) -> str:
        return f'"{s}"'

    conteggio_disponibilita = {}
    coppie_insegna = set()

    # Raccolta compresenze: chiave (giorno, ora, classe, docente_materia)
    # valore: (priorita, tipo, nome_itp)  priorita 2=itp, 1=sostegno
    compresenze: dict = {}

    for doc in docenti:
        nome_doc = quote(doc.nome)
        conteggio_disponibilita[nome_doc] = 0

        for (giorno, ora), valore in doc.orario.items():
            if valore is None:
                continue
            if valore == "D":
                lines.append(f'disponibile({nome_doc}, {giorno}, {ora}).')
                conteggio_disponibilita[nome_doc] += 1
                continue

            if ":" in valore:
                # Compresenza (solo ITP/sostegno)
                classe, materia = valore.split(":", 1)
                classe = classe.strip()
                materia = materia.strip()
                priorita = 2 if doc.tipo == "itp" else 1
                chiave = (giorno, ora, classe, materia)
                if chiave not in compresenze or priorita > compresenze[chiave][0]:
                    compresenze[chiave] = (priorita, doc.tipo, doc.nome)
                # L'ITP/sostegno in compresenza non genera lezione
                continue

            # Lezione autonoma (solo materia)
            if doc.tipo == "materia":
                classe = quote(valore)
                lines.append(f'lezione({nome_doc}, {giorno}, {ora}, {classe}).')
                coppie_insegna.add((nome_doc, classe))
            # Se un ITP/sostegno ha un valore senza ":" diverso da "D", è un errore
            # ma non dovrebbe accadere grazie alla validazione del parser.

    # Fatti disponibilita_totale
    for docente, totale in conteggio_disponibilita.items():
        lines.append(f'disponibilita_totale({docente}, {totale}).')

    # Fatti insegna_in_classe
    for (docente, classe) in coppie_insegna:
        lines.append(f'insegna_in_classe({docente}, {classe}).')

    # Fatti compresenza (uno per chiave, con priorità ITP > sostegno)
    for (giorno, ora, classe, materia), (priorita, tipo, nome_itp) in compresenze.items():
        lines.append(
            f'compresenza({quote(nome_itp)}, {quote(materia)}, '
            f'{giorno}, {ora}, {quote(classe)}).'
        )

    # Fatti assenza
    for ass in assenze:
        giorno = ass.data.weekday() + 1
        if giorno > 5:
            continue
        docente = quote(ass.docente_nome)
        preavviso = "true" if ass.preavviso_sufficiente else "false"
        lines.append(
            f'assenza({docente}, {giorno}, {ass.ora_inizio}, {ass.ora_fine}, {preavviso}).'
        )

    # Fatti visita
    for vis in visite:
        giorno = vis.data.weekday() + 1
        if giorno > 5:
            continue
        classe = quote(vis.classe)
        lines.append(f'visita({classe}, {giorno}, 1, {ore_giornaliere}).')

    return "\n".join(lines)