import pytest
import os
from datetime import date
from unittest.mock import patch
from app.models import Docente, Assenza, VisitaIstruzione
from app.asp_solver import calcola_assegnazioni


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


def test_supplenza_automatica_da_compresenza():
    """US18: assenza del docente di materia in ora di compresenza → ITP subentra automaticamente."""
    rossi = Docente(nome="Rossi", tipo="materia", orario={(1, 1): "1A"})
    itp = Docente(nome="ITP1", tipo="itp", orario={(1, 1): "1A:Rossi"})
    ass = Assenza("Rossi", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 10))
    assegnazioni = calcola_assegnazioni([rossi, itp], [ass], [])
    assert len(assegnazioni) == 1
    assert assegnazioni[0].docente_supplente_nome == "ITP1"
    assert assegnazioni[0].ora_scoperta.classe == "1A"


def test_priorita_itp_su_sostegno():
    """US18: con ITP e sostegno, l'ITP subentra."""
    rossi = Docente(nome="Rossi", tipo="materia", orario={(1, 1): "1A"})
    itp = Docente(nome="ITP1", tipo="itp", orario={(1, 1): "1A:Rossi"})
    sost = Docente(nome="Sost1", tipo="sostegno", orario={(1, 1): "1A:Rossi"})
    ass = Assenza("Rossi", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 10))
    assegnazioni = calcola_assegnazioni([rossi, itp, sost], [ass], [])
    assert len(assegnazioni) == 1
    assert assegnazioni[0].docente_supplente_nome == "ITP1"


def test_supplenza_automatica_anche_su_prima_ora():
    """US18: l'ITP subentra anche sulla prima ora."""
    rossi = Docente(nome="Rossi", tipo="materia", orario={(1, 1): "1A"})
    itp = Docente(nome="ITP1", tipo="itp", orario={(1, 1): "1A:Rossi"})
    ass = Assenza("Rossi", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 8))
    assegnazioni = calcola_assegnazioni([rossi, itp], [ass], [])
    # Con preavviso sufficiente e prima ora, la richiesta normale sarebbe esclusa,
    # ma la supplenza automatica deve scattare comunque.
    assert len(assegnazioni) == 1
    assert assegnazioni[0].docente_supplente_nome == "ITP1"


def test_file_regole_mancante(docenti_base, assenza_rossi_ora2_insufficiente):
    with patch('builtins.open', side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_insufficiente], [])