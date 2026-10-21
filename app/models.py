from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple, Set


@dataclass
class Docente:
    """Rappresenta un docente con nome, email e orario settimanale."""
    nome: str
    tipo: str = "materia"  # "materia", "itp", "sostegno"
    email: Optional[str] = None
    # orario: dict[(giorno, ora)] -> valore:
    # - None: libero (non disponibile per supplenze)
    # - "D": disponibile per supplenze
    # - stringa senza ":" : nome della classe (es. "1A") -> lezione (solo materia)
    # - stringa con ":" : "classe:docente_materia" -> compresenza (solo itp/sostegno)
    orario: Dict[Tuple[int, int], Optional[str]] = field(default_factory=dict)

    ore_supplenza_assegnate: List['Assegnazione'] = field(default_factory=list)

    def __post_init__(self):
        if self.orario is None:
            self.orario = {}

    # ------------------------------------------------------------------
    # Metodi di base
    # ------------------------------------------------------------------

    def ha_lezione(self, giorno: int, ora: int) -> bool:
        val = self.orario.get((giorno, ora))
        if val is None or val == "D":
            return False
        return ":" not in val

    def get_classe(self, giorno: int, ora: int) -> Optional[str]:
        val = self.orario.get((giorno, ora))
        if val is None or val == "D":
            return None
        if ":" in val:
            return None
        return val

    def is_disponibile_per_supplenza(self, giorno: int, ora: int) -> bool:
        return self.orario.get((giorno, ora)) == "D"

    def e_libero(self, giorno: int, ora: int) -> bool:
        return self.orario.get((giorno, ora)) is None

    # ------------------------------------------------------------------
    # Compresenza (US18)
    # ------------------------------------------------------------------

    def is_compresenza(self, giorno: int, ora: int) -> bool:
        val = self.orario.get((giorno, ora))
        if val is None or val == "D":
            return False
        return ":" in val

    def get_classe_compresenza(self, giorno: int, ora: int) -> Optional[str]:
        val = self.orario.get((giorno, ora))
        if val is None or val == "D" or ":" not in val:
            return None
        return val.split(":", 1)[0].strip()

    def get_docente_materia_compresenza(self, giorno: int, ora: int) -> Optional[str]:
        val = self.orario.get((giorno, ora))
        if val is None or val == "D" or ":" not in val:
            return None
        return val.split(":", 1)[1].strip()

    # ------------------------------------------------------------------
    # Conteggio ore
    # ------------------------------------------------------------------

    def ore_curricolari_settimanali(self) -> int:
        return sum(1 for v in self.orario.values() if v is not None and v != "D")

    def ore_totali_settimanali(self) -> int:
        return self.ore_curricolari_settimanali() + len(self.ore_supplenza_assegnate)

    def verifica_max_consecutive(self, giorno: int, ora_candidata: int) -> bool:
        ore_occupate = set()
        for (g, o), val in self.orario.items():
            if g == giorno and val is not None and val != "D":
                ore_occupate.add(o)
        for ass in self.ore_supplenza_assegnate:
            if ass.ora_scoperta.data.weekday() + 1 == giorno:
                ore_occupate.add(ass.ora_scoperta.ora)
        ore_occupate.add(ora_candidata)
        ore_ordinate = sorted(ore_occupate)
        if not ore_ordinate:
            return True
        max_consec = 1
        curr = 1
        for i in range(1, len(ore_ordinate)):
            if ore_ordinate[i] == ore_ordinate[i - 1] + 1:
                curr += 1
                max_consec = max(max_consec, curr)
            else:
                curr = 1
        return max_consec <= 7

    def __repr__(self):
        return f'<Docente {self.nome} ({self.tipo})>'


@dataclass
class Assenza:
    docente_nome: str
    data: date
    ora_inizio: int
    ora_fine: int
    tipo_assenza: str
    data_comunicazione: date

    @property
    def preavviso_ore(self) -> int:
        delta = self.data - self.data_comunicazione
        return delta.days * 24

    @property
    def preavviso_sufficiente(self) -> bool:
        return self.preavviso_ore >= 48

    def ore_interessate(self) -> List[int]:
        return list(range(self.ora_inizio, self.ora_fine + 1))


@dataclass
class VisitaIstruzione:
    classe: str
    data: date
    ora_inizio: int
    ora_fine: int
    docenti_accompagnatori: List[str]

    def ore_interessate(self) -> List[int]:
        return list(range(self.ora_inizio, self.ora_fine + 1))


@dataclass
class OraScoperta:
    data: date
    ora: int
    classe: str
    docente_assente_nome: str
    richiede_supplenza: bool = True
    stato: str = "scoperta"
    assegnazione: Optional['Assegnazione'] = None

    def __repr__(self):
        return f'<OraScoperta {self.data} {self.ora} classe {self.classe} - {self.stato}>'


@dataclass
class Assegnazione:
    ora_scoperta: OraScoperta
    docente_supplente_nome: str
    timestamp: Optional[datetime] = field(default_factory=datetime.now)

    def __post_init__(self):
        self.ora_scoperta.assegnazione = self
        self.ora_scoperta.stato = "assegnata"


# ----------------------------------------------------------------------
# Funzioni di utilità (ex-US5)
# ----------------------------------------------------------------------

def ore_classe_in_data(
    data: date,
    classe: str,
    docenti: List[Docente],
    visite: List[VisitaIstruzione]
) -> Set[int]:
    """Restituisce le ore di lezione di una classe in una data (escluse le visite)."""
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


def calcola_ore_scoperte(
    docenti: List[Docente],
    assenze: List[Assenza],
    visite: Optional[List[VisitaIstruzione]] = None
) -> List[OraScoperta]:
    """
    Genera la lista delle ore che richiedono supplenza.
    - Preavviso < 48h: tutte le ore di lezione del docente assente.
    - Preavviso >= 48h: solo le ore che non sono né prima né ultima per la classe.
    """
    if visite is None:
        visite = []

    doc_map = {d.nome: d for d in docenti}
    ore_scoperte = []

    for ass in assenze:
        docente = doc_map.get(ass.docente_nome)
        if not docente:
            continue

        giorno_sett = ass.data.weekday() + 1
        ore_docente = []
        for ora in ass.ore_interessate():
            classe = docente.get_classe(giorno_sett, ora)
            if classe is not None:
                ore_docente.append((ora, classe))

        if not ore_docente:
            continue

        ore_per_classe = {}
        for ora, classe in ore_docente:
            ore_per_classe.setdefault(classe, []).append(ora)

        for classe, ore_list in ore_per_classe.items():
            tutte_ore = ore_classe_in_data(ass.data, classe, docenti, visite)
            if not tutte_ore:
                continue
            prima = min(tutte_ore)
            ultima = max(tutte_ore)

            for ora in ore_list:
                if ora not in tutte_ore:
                    continue

                if ass.preavviso_sufficiente:
                    if ora == prima or ora == ultima:
                        continue
                    else:
                        ore_scoperte.append(OraScoperta(
                            data=ass.data, ora=ora, classe=classe,
                            docente_assente_nome=ass.docente_nome,
                            richiede_supplenza=True
                        ))
                else:
                    ore_scoperte.append(OraScoperta(
                        data=ass.data, ora=ora, classe=classe,
                        docente_assente_nome=ass.docente_nome,
                        richiede_supplenza=True
                    ))

    return ore_scoperte


def docenti_disponibili_per_ora(
    docenti: List[Docente],
    data: date,
    ora: int,
    visite: List[VisitaIstruzione]
) -> List[Docente]:
    """Restituisce i docenti effettivamente disponibili per supplenza in quell'ora."""
    giorno = data.weekday() + 1
    disponibili = []
    for doc in docenti:
        if any(v for v in visite if v.data == data and ora in v.ore_interessate()
               and doc.nome in v.docenti_accompagnatori):
            continue

        if doc.is_disponibile_per_supplenza(giorno, ora):
            disponibili.append(doc)
            continue

        classe_in_orario = doc.get_classe(giorno, ora)
        if classe_in_orario is not None:
            if any(v for v in visite if v.data == data and ora in v.ore_interessate()
                   and v.classe == classe_in_orario):
                disponibili.append(doc)
    return disponibili