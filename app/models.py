# app/models.py

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple, Set

@dataclass
class Docente:
    """Rappresenta un docente con nome, email e orario settimanale."""
    nome: str
    email: Optional[str] = None
    # orario: dict[(giorno, ora)] -> valore:
    #   - None: libero (non disponibile per supplenze)
    #   - "D": disponibile per supplenze
    #   - stringa: nome della classe (es. "1A") -> lezione
    orario: Dict[Tuple[int, int], Optional[str]] = field(default_factory=dict)

    # Campi dinamici (popolati durante l'assegnazione)
    ore_supplenza_assegnate: List['Assegnazione'] = field(default_factory=list)

    def __post_init__(self):
        if self.orario is None:
            self.orario = {}

    def ha_lezione(self, giorno: int, ora: int) -> bool:
        """Restituisce True se il docente ha lezione in quel giorno/ora (valore diverso da None e "D")."""
        val = self.orario.get((giorno, ora))
        return val is not None and val != "D"

    def get_classe(self, giorno: int, ora: int) -> Optional[str]:
        """Restituisce la classe se il docente ha lezione, altrimenti None."""
        val = self.orario.get((giorno, ora))
        return val if val is not None and val != "D" else None

    def is_disponibile_per_supplenza(self, giorno: int, ora: int) -> bool:
        """Restituisce True se il docente è marcato come 'D' in quella ora."""
        return self.orario.get((giorno, ora)) == "D"

    def e_libero(self, giorno: int, ora: int) -> bool:
        """Restituisce True se il docente non ha impegni (né lezione né disponibilità)."""
        return self.orario.get((giorno, ora)) is None

    def ore_curricolari_settimanali(self) -> int:
        """Calcola il totale delle ore di lezione (classi, non D)."""
        return sum(1 for v in self.orario.values() if v is not None and v != "D")

    def ore_totali_settimanali(self) -> int:
        """Ore di lezione + supplenze assegnate."""
        return self.ore_curricolari_settimanali() + len(self.ore_supplenza_assegnate)

    def verifica_max_consecutive(self, giorno: int, ora_candidata: int) -> bool:
        """
        Verifica se assegnare una supplenza in (giorno, ora_candidata) farebbe superare 7 ore consecutive.
        Considera solo le ore di lezione e le supplenze già assegnate (non le D).
        """
        ore_occupate = set()
        # Ore di lezione
        for (g, o), val in self.orario.items():
            if g == giorno and val is not None and val != "D":
                ore_occupate.add(o)
        # Ore di supplenza già assegnate
        for ass in self.ore_supplenza_assegnate:
            if ass.ora_scoperta.data.weekday() + 1 == giorno:
                ore_occupate.add(ass.ora_scoperta.ora)
        # Aggiungi l'ora candidata
        ore_occupate.add(ora_candidata)
        # Calcola massimo consecutivo
        ore_ordinate = sorted(ore_occupate)
        if not ore_ordinate:
            return True
        max_consec = 1
        curr = 1
        for i in range(1, len(ore_ordinate)):
            if ore_ordinate[i] == ore_ordinate[i-1] + 1:
                curr += 1
                max_consec = max(max_consec, curr)
            else:
                curr = 1
        return max_consec <= 7

    def __repr__(self):
        return f'<Docente {self.nome}>'


@dataclass
class Assenza:
    """
    Rappresenta un'assenza comunicata.
    Vincoli 5 e 6: gestione preavviso.
    """
    docente_nome: str
    data: date
    ora_inizio: int      # 1..7
    ora_fine: int        # 1..7 (inclusa)
    tipo_assenza: str    # es. "PERMESSO", "MALATTIA", "VISITA" (per visite accompagnate)
    data_comunicazione: date

    @property
    def preavviso_ore(self) -> int:
        """Calcola il preavviso in ore (24h = 1 giorno)."""
        delta = self.data - self.data_comunicazione
        return delta.days * 24  # approssimazione: non considera l'ora della comunicazione

    @property
    def preavviso_sufficiente(self) -> bool:
        """Vincolo 5: preavviso >= 48 ore."""
        return self.preavviso_ore >= 48

    def ore_interessate(self) -> List[int]:
        """Restituisce la lista delle ore coinvolte dall'assenza."""
        return list(range(self.ora_inizio, self.ora_fine + 1))


@dataclass
class VisitaIstruzione:
    """
    Rappresenta una visita di istruzione (Vincolo 7).
    """
    classe: str
    data: date
    ora_inizio: int
    ora_fine: int
    docenti_accompagnatori: List[str]  # nomi dei docenti

    def ore_interessate(self) -> List[int]:
        return list(range(self.ora_inizio, self.ora_fine + 1))


@dataclass
class OraScoperta:
    """
    Ora in cui un docente è assente e quindi serve un supplente.
    Viene generata dal solver incrociando assenze e visite.
    """
    data: date
    ora: int
    classe: str
    docente_assente_nome: str
    richiede_supplenza: bool = True
    stato: str = "scoperta"  # "scoperta" o "assegnata"
    assegnazione: Optional['Assegnazione'] = None

    def __repr__(self):
        return f'<OraScoperta {self.data} {self.ora} classe {self.classe} - {self.stato}>'


@dataclass
class Assegnazione:
    """
    Assegnazione di un supplente a un'ora scoperta.
    """
    ora_scoperta: OraScoperta
    docente_supplente_nome: str
    timestamp: Optional[datetime] = field(default_factory=datetime.now)

    def __post_init__(self):
        # Collega l'assegnazione all'ora scoperta
        self.ora_scoperta.assegnazione = self
        self.ora_scoperta.stato = "assegnata"


# ---------------------------------------------------------------------
# Funzioni di utilità per il solver
# ---------------------------------------------------------------------

def calcola_ore_scoperte(docenti: List[Docente], assenze: List[Assenza], visite: List[VisitaIstruzione] = None) -> List[OraScoperta]:
    """
    Genera la lista delle ore scoperte incrociando le assenze con l'orario dei docenti.
    Tiene conto del preavviso (vincoli 5 e 6) e delle visite (vincolo 7).
    """
    if visite is None:
        visite = []

    doc_map = {d.nome: d for d in docenti}
    ore_scoperte = []

    for ass in assenze:
        docente = doc_map.get(ass.docente_nome)
        if not docente:
            continue

        richiede = not ass.preavviso_sufficiente

        for ora in ass.ore_interessate():
            giorno_sett = ass.data.weekday() + 1
            classe = docente.get_classe(giorno_sett, ora)
            if classe is None:
                # Il docente non aveva lezione (era libero o in D), quindi l'assenza non crea scopertura
                continue

            # Controlla se la classe è in visita
            in_visita = any(
                v for v in visite
                if v.data == ass.data and ora in v.ore_interessate() and v.classe == classe
            )
            if in_visita:
                continue

            ora_scoperta = OraScoperta(
                data=ass.data,
                ora=ora,
                classe=classe,
                docente_assente_nome=ass.docente_nome,
                richiede_supplenza=richiede
            )
            ore_scoperte.append(ora_scoperta)

    return ore_scoperte


def docenti_disponibili_per_ora(docenti: List[Docente], data: date, ora: int, visite: List[VisitaIstruzione]) -> List[Docente]:
    """
    Restituisce la lista dei docenti disponibili per una specifica ora, tenendo conto:
    - Disponibilità esplicita (marcata "D" nell'orario)
    - Disponibilità temporanea per visite (se la classe che insegnano è in visita)
    - Esclusione dei docenti accompagnatori in visita
    """
    giorno = data.weekday() + 1
    disponibili = []
    for doc in docenti:
        # Se il docente è accompagnatore in una visita in quest'ora, non è disponibile
        if any(v for v in visite if v.data == data and ora in v.ore_interessate() and doc.nome in v.docenti_accompagnatori):
            continue

        # Caso 1: Disponibilità esplicita "D"
        if doc.is_disponibile_per_supplenza(giorno, ora):
            disponibili.append(doc)
            continue

        # Caso 2: Lezione con classe in visita -> diventa disponibile
        classe_in_orario = doc.get_classe(giorno, ora)
        if classe_in_orario is not None:
            if any(v for v in visite if v.data == data and ora in v.ore_interessate() and v.classe == classe_in_orario):
                disponibili.append(doc)
            # altrimenti non disponibile (ha lezione normale)
        # Caso 3: Libero (cella vuota) -> non disponibile (non si aggiunge)
    return disponibili