import pytest
import os
from datetime import date
from unittest.mock import patch
from app.models import Docente, Assenza, VisitaIstruzione
from app.asp_solver import calcola_assegnazioni

# ----------------------------------------------------------------------
# Fixture per dati di test
# ----------------------------------------------------------------------

@pytest.fixture
def docenti_base():
    """Crea docenti con orari semplici."""
    # Rossi: lezione 1A lunedì ore 2
    orario_rossi = {(1, 2): "1A"}
    # Verdi: disponibile lunedì ore 2
    orario_verdi = {(1, 2): "D"}
    # Neri: disponibile lunedì ore 2 e 3
    orario_neri = {(1, 2): "D", (1, 3): "D"}
    return [
        Docente(nome="Rossi", orario=orario_rossi),
        Docente(nome="Verdi", orario=orario_verdi),
        Docente(nome="Neri", orario=orario_neri),
    ]

@pytest.fixture
def assenza_rossi_ora2_insufficiente():
    """Assenza di Rossi all'ora 2 con preavviso insufficiente (genera supplenza)."""
    return Assenza(
        docente_nome="Rossi",
        data=date(2025, 3, 10),  # lunedì
        ora_inizio=2,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 10)  # stesso giorno → <48h
    )

@pytest.fixture
def assenza_rossi_ora2_sufficiente():
    """Assenza di Rossi all'ora 2 con preavviso sufficiente (in una sequenza di 1 ora non genera supplenza)."""
    return Assenza(
        docente_nome="Rossi",
        data=date(2025, 3, 10),
        ora_inizio=2,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 8)  # 48h
    )

@pytest.fixture
def assenza_bianchi_ora3_insufficiente():
    return Assenza(
        docente_nome="Bianchi",  # docente non presente in docenti_base
        data=date(2025, 3, 10),
        ora_inizio=3,
        ora_fine=3,
        tipo_assenza="MALATTIA",
        data_comunicazione=date(2025, 3, 10)
    )

# ----------------------------------------------------------------------
# Test casi positivi
# ----------------------------------------------------------------------

def test_singola_richiesta_con_un_disponibile(docenti_base, assenza_rossi_ora2_insufficiente):
    """Una richiesta, più docenti disponibili → assegnazione singola (accettiamo uno qualsiasi)."""
    assegnazioni = calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_insufficiente], [])
    assert len(assegnazioni) == 1
    assert assegnazioni[0].docente_supplente_nome in ["Verdi", "Neri"]
    assert assegnazioni[0].ora_scoperta.ora == 2
    assert assegnazioni[0].ora_scoperta.classe == "1A"
    assert assegnazioni[0].ora_scoperta.data == date(2025, 3, 10)

def test_singola_richiesta_con_piu_disponibili(docenti_base, assenza_rossi_ora2_insufficiente):
    """Una richiesta, più docenti disponibili → stessa logica del test precedente."""
    assegnazioni = calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_insufficiente], [])
    assert len(assegnazioni) == 1
    assert assegnazioni[0].docente_supplente_nome in ["Verdi", "Neri"]

def test_due_richieste_stessa_ora_docenti_sufficienti(docenti_base):
    """Due richieste nella stessa ora, due docenti disponibili → entrambe assegnate."""
    # Creiamo una seconda assenza per un altro docente
    orario_bianchi = {(1, 2): "2B"}  # Bianchi lezione 2B all'ora 2
    docente_bianchi = Docente(nome="Bianchi", orario=orario_bianchi)
    docenti = docenti_base + [docente_bianchi]

    ass1 = Assenza(
        docente_nome="Rossi",
        data=date(2025, 3, 10),
        ora_inizio=2,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 10)
    )
    ass2 = Assenza(
        docente_nome="Bianchi",
        data=date(2025, 3, 10),
        ora_inizio=2,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 10)
    )

    assegnazioni = calcola_assegnazioni(docenti, [ass1, ass2], [])
    assert len(assegnazioni) == 2
    docenti_assegnati = [a.docente_supplente_nome for a in assegnazioni]
    # Verdi e Neri sono disponibili, devono coprire entrambe
    assert set(docenti_assegnati) == {"Verdi", "Neri"}

def test_richieste_ore_diverse(docenti_base):
    """Due richieste a ore diverse, docenti disponibili in entrambe."""
    orario_bianchi = {(1, 3): "2B"}
    docente_bianchi = Docente(nome="Bianchi", orario=orario_bianchi)
    docenti = docenti_base + [docente_bianchi]

    ass1 = Assenza(
        docente_nome="Rossi",
        data=date(2025, 3, 10),
        ora_inizio=2,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 10)
    )
    ass2 = Assenza(
        docente_nome="Bianchi",
        data=date(2025, 3, 10),
        ora_inizio=3,
        ora_fine=3,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 10)
    )

    assegnazioni = calcola_assegnazioni(docenti, [ass1, ass2], [])
    assert len(assegnazioni) == 2
    # Non controlliamo l'esatta assegnazione perché può variare, ma deve essere valida
    # (cioè non ci sono conflitti)

def test_nessuna_richiesta(docenti_base):
    """Nessuna assenza → lista vuota."""
    assegnazioni = calcola_assegnazioni(docenti_base, [], [])
    assert assegnazioni == []

def test_richiesta_non_generata_per_preavviso_sufficiente(docenti_base, assenza_rossi_ora2_sufficiente):
    """Assenza con preavviso sufficiente su unica ora → non genera richiesta, quindi lista vuota."""
    assegnazioni = calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_sufficiente], [])
    assert assegnazioni == []

def test_richiesta_con_visita_classe(docenti_base, assenza_rossi_ora2_insufficiente):
    """Classe in visita → nessuna richiesta."""
    visita = VisitaIstruzione(
        classe="1A",
        data=date(2025, 3, 10),
        ora_inizio=1,
        ora_fine=6,
        docenti_accompagnatori=["Verdi"]
    )
    assegnazioni = calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_insufficiente], [visita])
    assert assegnazioni == []

def test_docente_assente_inesistente_ignorato(docenti_base, assenza_bianchi_ora3_insufficiente):
    """Docente non presente nei docenti → assenza ignorata, nessuna richiesta."""
    assegnazioni = calcola_assegnazioni(docenti_base, [assenza_bianchi_ora3_insufficiente], [])
    assert assegnazioni == []

# ----------------------------------------------------------------------
# Test casi di errore (insoddisfacibilità)
# ----------------------------------------------------------------------

def test_nessuna_soluzione_disponibile():
    """Richiesta senza docenti disponibili → deve sollevare eccezione (insoddisfacibile)."""
    # Docente con lezione all'ora 3
    orario_bianchi = {(1, 3): "2B"}
    docente_bianchi = Docente(nome="Bianchi", orario=orario_bianchi)
    # Nessun altro docente disponibile all'ora 3
    docenti = [docente_bianchi]  # solo Bianchi, che ha lezione e non è disponibile

    ass = Assenza(
        docente_nome="Bianchi",
        data=date(2025, 3, 10),
        ora_inizio=3,
        ora_fine=3,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 10)  # preavviso insufficiente
    )

    with pytest.raises(RuntimeError, match="Nessuna soluzione di assegnazione trovata"):
        calcola_assegnazioni(docenti, [ass], [])

# ----------------------------------------------------------------------
# Test di robustezza
# ----------------------------------------------------------------------

def test_file_regole_mancante(docenti_base, assenza_rossi_ora2_insufficiente):
    """Se un file di regole non esiste, deve sollevare eccezione."""
    with patch('builtins.open', side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            calcola_assegnazioni(docenti_base, [assenza_rossi_ora2_insufficiente], [])

# Nota: il test per clingo non installato è difficile da mockare perché l'import avviene all'inizio.
# Lo rimuoviamo per semplicità; in produzione, se clingo non è installato, l'applicazione fallirà all'avvio.