import os
import clingo
from datetime import date
from typing import List, Optional, Dict, Tuple, Any
from app.models import Docente, Assenza, VisitaIstruzione, Assegnazione, OraScoperta
from app.asp_facts import generate_asp_facts

def _estrai_modello(model, richieste_trovate, mappa_data):
    """Converte un modello Clingo in lista di oggetti Assegnazione."""
    assegnazioni = []
    for sym in model.symbols(shown=True):
        if sym.name == "assegna" and len(sym.arguments) == 4:
            docente = str(sym.arguments[0]).strip('"')
            giorno = sym.arguments[1].number
            ora = sym.arguments[2].number
            classe = str(sym.arguments[3]).strip('"')
            docente_assente = richieste_trovate.get((giorno, ora, classe), "")
            data = mappa_data.get((giorno, ora, classe))
            if data:
                ora_scoperta = OraScoperta(
                    data=data,
                    ora=ora,
                    classe=classe,
                    docente_assente_nome=docente_assente,
                    richiede_supplenza=True,
                    stato="assegnata"
                )
                assegnazioni.append(Assegnazione(ora_scoperta=ora_scoperta, docente_supplente_nome=docente))
    return assegnazioni

def calcola_assegnazioni(
    docenti: List[Docente],
    assenze: List[Assenza],
    visite: Optional[List[VisitaIstruzione]] = None,
    ore_giornaliere: int = 6,
    tutti_modelli: bool = False,
    max_modelli: int = 10
) -> List[Any]:
    """
    Esegue il solver ASP per determinare le assegnazioni delle supplenze.
    Se tutti_modelli=True, restituisce una lista di liste di Assegnazione (tutti i modelli, limitati a max_modelli).
    Altrimenti restituisce una lista di Assegnazione (primo modello).
    Solleva RuntimeError se il problema è insoddisfacibile.
    """
    if visite is None:
        visite = []

    fatti = generate_asp_facts(docenti, assenze, visite, ore_giornaliere)

    base_dir = os.path.dirname(__file__)
    with open(os.path.join(base_dir, 'asp', 'regole_ore_scoperte.lp'), 'r', encoding='utf-8') as f:
        regole_us6 = f.read()
    with open(os.path.join(base_dir, 'asp', 'regole_assegnazione.lp'), 'r', encoding='utf-8') as f:
        regole_us7 = f.read()

    program = regole_us6 + "\n" + regole_us7 + "\n" + fatti

    # Raccogli i fatti richiede_supplenza (per docente_assente)
    richieste_trovate: Dict[Tuple[int, int, str], str] = {}
    mappa_data: Dict[Tuple[int, int, str], date] = {}

    # Costruisci mappa data dalle assenze
    for ass in assenze:
        giorno_sett = ass.data.weekday() + 1
        for ora in range(ass.ora_inizio, ass.ora_fine + 1):
            docente_trovato = next((d for d in docenti if d.nome == ass.docente_nome), None)
            if docente_trovato:
                classe = docente_trovato.get_classe(giorno_sett, ora)
                if classe:
                    mappa_data[(giorno_sett, ora, classe)] = ass.data

    # Prima esecuzione per raccogliere richieste
    ctl_temp = clingo.Control()
    ctl_temp.add("base", [], program)
    ctl_temp.ground([("base", [])])
    def collect_richieste(model):
        for sym in model.symbols(shown=True):
            if sym.name == "richiede_supplenza" and len(sym.arguments) == 4:
                docente_assente = str(sym.arguments[0]).strip('"')
                giorno = sym.arguments[1].number
                ora = sym.arguments[2].number
                classe = str(sym.arguments[3]).strip('"')
                richieste_trovate[(giorno, ora, classe)] = docente_assente
    ctl_temp.solve(on_model=collect_richieste)

    # Ora esegui la ricerca dei modelli di assegnazione
    ctl = clingo.Control()
    ctl.add("base", [], program)
    ctl.ground([("base", [])])

    if tutti_modelli:
        # Imposta il limite massimo di modelli (parametro configurabile)
        ctl.configuration.solve.models = max_modelli
        modelli = []

        def on_model(model):
            modelli.append(_estrai_modello(model, richieste_trovate, mappa_data))

        result = ctl.solve(on_model=on_model)

        if result.satisfiable is False:
            raise RuntimeError("Nessuna soluzione di assegnazione trovata. I vincoli sono insoddisfacibili.")

        return modelli

    else:
        # Solo il primo modello
        modello_trovato = None

        def on_model(model):
            nonlocal modello_trovato
            if modello_trovato is not None:
                return
            modello_trovato = _estrai_modello(model, richieste_trovate, mappa_data)

        result = ctl.solve(on_model=on_model)

        if result.satisfiable is False:
            raise RuntimeError("Nessuna soluzione di assegnazione trovata. I vincoli sono insoddisfacibili.")

        return modello_trovato if modello_trovato is not None else []