import pytest
from datetime import date
from app.models import Docente, Assenza, VisitaIstruzione
from app.asp_facts import generate_asp_facts

def test_facts_with_simple_docente():
    """Test con un docente che ha lezioni e disponibilità."""
    orario = {
        (1, 1): "1A",      # lunedì ora 1 lezione 1A
        (1, 2): "D",       # lunedì ora 2 disponibile
        (2, 3): None,      # martedì ora 3 vuoto (nessun fatto)
    }
    docente = Docente(nome="Rossi", orario=orario)
    docenti = [docente]
    assenze = []
    visite = []

    fatti = generate_asp_facts(docenti, assenze, visite)

    # Verifichiamo che i fatti attesi siano presenti (con virgolette)
    assert 'lezione("Rossi", 1, 1, "1A").' in fatti
    assert 'disponibile("Rossi", 1, 2).' in fatti
    assert 'lezione("Rossi", 2, 3, "1A").' not in fatti  # non c'è lezione
    assert 'disponibile("Rossi", 2, 3).' not in fatti    # non c'è disponibile


def test_facts_with_multiple_docenti():
    """Test con due docenti, uno con nome con spazio."""
    orario1 = {(1,1): "1A"}
    orario2 = {(1,2): "2B"}
    docente1 = Docente(nome="Rossi", orario=orario1)
    docente2 = Docente(nome="Maria Rossi", orario=orario2)  # nome con spazio
    docenti = [docente1, docente2]
    assenze = []
    visite = []

    fatti = generate_asp_facts(docenti, assenze, visite)

    assert 'lezione("Rossi", 1, 1, "1A").' in fatti
    assert 'lezione("Maria Rossi", 1, 2, "2B").' in fatti


def test_facts_with_assenze():
    """Test con assenze di vario tipo."""
    oggi = date(2025, 3, 10)  # lunedì
    ass1 = Assenza(
        docente_nome="Rossi",
        data=oggi,
        ora_inizio=1,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 8)  # preavviso sufficiente (2 giorni)
    )
    ass2 = Assenza(
        docente_nome="Bianchi",
        data=date(2025, 3, 11),  # martedì
        ora_inizio=3,
        ora_fine=3,
        tipo_assenza="MALATTIA",
        data_comunicazione=date(2025, 3, 11)  # preavviso insufficiente (stesso giorno)
    )
    docenti = [Docente(nome="Rossi", orario={}), Docente(nome="Bianchi", orario={})]
    fatti = generate_asp_facts(docenti, [ass1, ass2], [])

    assert 'assenza("Rossi", 1, 1, 2, true).' in fatti
    assert 'assenza("Bianchi", 2, 3, 3, false).' in fatti


def test_facts_with_visite():
    """Test con visite di istruzione."""
    visita = VisitaIstruzione(
        classe="1A",
        data=date(2025, 3, 10),  # lunedì
        ora_inizio=1,  # in realtà non usato perché copre tutta la giornata
        ora_fine=6,
        docenti_accompagnatori=["Verdi"]
    )
    docenti = []
    assenze = []
    fatti = generate_asp_facts(docenti, assenze, [visita], ore_giornaliere=6)

    assert 'visita("1A", 1, 1, 6).' in fatti


def test_weekend_ignored():
    """Test che le date nel weekend vengano ignorate."""
    sabato = date(2025, 3, 15)  # sabato
    ass = Assenza(
        docente_nome="Rossi",
        data=sabato,
        ora_inizio=1,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=sabato
    )
    docenti = [Docente(nome="Rossi", orario={})]
    fatti = generate_asp_facts(docenti, [ass], [])

    assert 'assenza' not in fatti


def test_nomi_con_spazi_quotati():
    """Verifica che i nomi con spazi siano correttamente quotati."""
    orario = {(1,1): "1A"}
    docente = Docente(nome="Mario Rossi", orario=orario)
    docenti = [docente]
    fatti = generate_asp_facts(docenti, [], [])

    assert 'lezione("Mario Rossi", 1, 1, "1A").' in fatti