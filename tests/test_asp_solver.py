import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import date
from unittest.mock import patch

from app.models import Docente, Assenza, VisitaIstruzione
from app.asp_solver import calcola_assegnazioni
from app.parser import parse_orario
from tests.generators.genera_orario_con_compresenze import genera_orario_con_compresenze


# ----------------------------------------------------------------------
# Fixture di base (senza compresenze)
# ----------------------------------------------------------------------

@pytest.fixture
def docenti_base():
    return [
        Docente(nome="Rossi", tipo="materia", orario={(1, 2): "1A"}),
        Docente(nome="Verdi", tipo="materia", orario={(1, 2): "D"}),
        Docente(nome="Neri", tipo="materia", orario={(1, 2): "D", (1, 3): "D"}),
    ]


@pytest.fixture
def assenza_rossi_ora2_insufficiente():
    return Assenza(
        docente_nome="Rossi",
        data=date(2025, 3, 10),
        ora_inizio=2,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 10),
    )


@pytest.fixture
def assenza_rossi_ora2_sufficiente():
    return Assenza(
        docente_nome="Rossi",
        data=date(2025, 3, 10),
        ora_inizio=2,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 8),
    )


# ----------------------------------------------------------------------
# Test di base
# ----------------------------------------------------------------------

def test_singola_richiesta_con_un_disponibile(docenti_base, assenza_rossi_ora2_insufficiente):
    assegnazioni = calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_insufficiente], [])
    assert len(assegnazioni) == 1
    assert assegnazioni[0].docente_supplente_nome in ["Verdi", "Neri"]


def test_singola_richiesta_con_piu_disponibili(docenti_base, assenza_rossi_ora2_insufficiente):
    assegnazioni = calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_insufficiente], [])
    assert len(assegnazioni) == 1


def test_due_richieste_stessa_ora_docenti_sufficienti(docenti_base):
    docente_bianchi = Docente(nome="Bianchi", tipo="materia", orario={(1, 2): "2B"})
    docenti = docenti_base + [docente_bianchi]

    ass1 = Assenza("Rossi", date(2025, 3, 10), 2, 2, "PERMESSO", date(2025, 3, 10))
    ass2 = Assenza("Bianchi", date(2025, 3, 10), 2, 2, "PERMESSO", date(2025, 3, 10))

    assegnazioni = calcola_assegnazioni(docenti, [ass1, ass2], [])
    assert len(assegnazioni) == 2
    assert set(a.docente_supplente_nome for a in assegnazioni) == {"Verdi", "Neri"}


def test_nessuna_richiesta(docenti_base):
    assert calcola_assegnazioni(docenti_base, [], []) == []


def test_richiesta_non_generata_per_preavviso_sufficiente(docenti_base, assenza_rossi_ora2_sufficiente):
    assert calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_sufficiente], []) == []


def test_richiesta_con_visita_classe(docenti_base, assenza_rossi_ora2_insufficiente):
    visita = VisitaIstruzione("1A", date(2025, 3, 10), 1, 6, ["Verdi"])
    assert calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_insufficiente], [visita]) == []


def test_docente_assente_inesistente_ignorato(docenti_base):
    ass = Assenza("Bianchi", date(2025, 3, 10), 3, 3, "MALATTIA", date(2025, 3, 10))
    assert calcola_assegnazioni(docenti_base, [ass], []) == []


def test_nessuna_soluzione_disponibile():
    docente_bianchi = Docente(nome="Bianchi", tipo="materia", orario={(1, 3): "2B"})
    ass = Assenza("Bianchi", date(2025, 3, 10), 3, 3, "PERMESSO", date(2025, 3, 10))
    with pytest.raises(RuntimeError, match="Nessuna soluzione di assegnazione trovata"):
        calcola_assegnazioni([docente_bianchi], [ass], [])


def test_file_regole_mancante(docenti_base, assenza_rossi_ora2_insufficiente):
    with patch('builtins.open', side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_insufficiente], [])


# ----------------------------------------------------------------------
# Fixture con compresenze (US18)
# ----------------------------------------------------------------------

@pytest.fixture(scope='module')
def orario_file_compresenza():
    return genera_orario_con_compresenze("tests/fixtures/orario_con_compresenze.xlsx")


@pytest.fixture
def docenti_compresenza(orario_file_compresenza):
    return parse_orario(orario_file_compresenza)


# ----------------------------------------------------------------------
# Test US18 – Supplenza automatica da compresenza
# ----------------------------------------------------------------------

def test_supplenza_automatica_da_compresenza(docenti_compresenza):
    """Assenza di Rossi in 1A Lun-1 → ITP Mario subentra automaticamente."""
    ass = Assenza("Rossi", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 10))
    assegnazioni = calcola_assegnazioni(docenti_compresenza, [ass], [])
    assert len(assegnazioni) == 1
    assert assegnazioni[0].docente_supplente_nome == "Mario"
    assert assegnazioni[0].ora_scoperta.classe == "1A"


def test_priorita_itp_su_sostegno(docenti_compresenza):
    """Mario (ITP) ha priorità su Anna (sostegno) in 1A Lun-1."""
    ass = Assenza("Rossi", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 10))
    assegnazioni = calcola_assegnazioni(docenti_compresenza, [ass], [])
    assert assegnazioni[0].docente_supplente_nome == "Mario"


def test_neri_assente_mar1_itp_luigi_subentra(docenti_compresenza):
    """Assenza di Neri in 1A Mar-1 → ITP Luigi subentra."""
    ass = Assenza("Neri", date(2025, 3, 11), 1, 1, "PERMESSO", date(2025, 3, 11))
    assegnazioni = calcola_assegnazioni(docenti_compresenza, [ass], [])
    assert len(assegnazioni) == 1
    assert assegnazioni[0].docente_supplente_nome == "Luigi"
    assert assegnazioni[0].ora_scoperta.classe == "1A"


def test_supplenza_automatica_anche_su_prima_ora(docenti_compresenza):
    """Con preavviso sufficiente, la regola prime/ultime ore non si applica in compresenza."""
    ass = Assenza("Rossi", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 7))
    assegnazioni = calcola_assegnazioni(docenti_compresenza, [ass], [])
    assert len(assegnazioni) == 1
    assert assegnazioni[0].docente_supplente_nome == "Mario"


def test_itp_assente_non_genera_supplenza_automatica(docenti_compresenza):
    """Se l'ITP è assente ma il titolare è presente, nessuna supplenza automatica."""
    ass = Assenza("Mario", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 10))
    assegnazioni = calcola_assegnazioni(docenti_compresenza, [ass], [])
    assert all(
        not (a.ora_scoperta.classe == "1A" and a.ora_scoperta.ora == 1)
        for a in assegnazioni
    )


def test_assenza_contemporanea_titolare_e_itp(docenti_compresenza):
    """Se titolare e ITP sono assenti, l'ora resta scoperta e va gestita normalmente."""
    ass_rossi = Assenza("Rossi", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 10))
    ass_mario = Assenza("Mario", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 10))

    try:
        assegnazioni = calcola_assegnazioni(docenti_compresenza, [ass_rossi, ass_mario], [])
    except RuntimeError as e:
        # Nessun docente disponibile: l'ora resta scoperta, comportamento atteso
        assert "Nessuna soluzione" in str(e)
        return

    # Se il solver trova una soluzione, Mario non deve comparire
    assert all(
        a.docente_supplente_nome != "Mario"
        for a in assegnazioni
        if a.ora_scoperta.classe == "1A" and a.ora_scoperta.ora == 1
    )


def test_assenza_contemporanea_con_supplente_normale(docenti_compresenza):
    """Con Rossi e Mario assenti, un altro docente con 'D' copre la classe."""
    verdi = Docente(nome="Verdi", tipo="materia", orario={(1, 1): "D"})
    docenti = docenti_compresenza + [verdi]

    ass_rossi = Assenza("Rossi", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 10))
    ass_mario = Assenza("Mario", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 10))

    assegnazioni = calcola_assegnazioni(docenti, [ass_rossi, ass_mario], [])
    assert len(assegnazioni) == 1
    assert assegnazioni[0].docente_supplente_nome == "Verdi"
    assert assegnazioni[0].ora_scoperta.classe == "1A"
    assert assegnazioni[0].ora_scoperta.ora == 1