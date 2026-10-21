from app.models import Docente, Assenza, VisitaIstruzione
from app.asp_facts import generate_asp_facts
from datetime import date


def test_facts_with_simple_docente():
    docente = Docente(nome="Rossi", tipo="materia", orario={(1, 1): "1A", (1, 2): "D"})
    fatti = generate_asp_facts([docente], [], [])
    assert 'lezione("Rossi", 1, 1, "1A").' in fatti
    assert 'disponibile("Rossi", 1, 2).' in fatti


def test_facts_with_multiple_docenti():
    d1 = Docente(nome="Rossi", tipo="materia", orario={(1, 1): "1A"})
    d2 = Docente(nome="Maria Rossi", tipo="materia", orario={(1, 2): "2B"})
    fatti = generate_asp_facts([d1, d2], [], [])
    assert 'lezione("Rossi", 1, 1, "1A").' in fatti
    assert 'lezione("Maria Rossi", 1, 2, "2B").' in fatti


def test_facts_with_assenze():
    ass1 = Assenza("Rossi", date(2025, 3, 10), 1, 2, "PERMESSO", date(2025, 3, 8))
    ass2 = Assenza("Bianchi", date(2025, 3, 11), 3, 3, "MALATTIA", date(2025, 3, 11))
    docenti = [Docente(nome="Rossi", tipo="materia", orario={}),
               Docente(nome="Bianchi", tipo="materia", orario={})]
    fatti = generate_asp_facts(docenti, [ass1, ass2], [])
    assert 'assenza("Rossi", 1, 1, 2, true).' in fatti
    assert 'assenza("Bianchi", 2, 3, 3, false).' in fatti


def test_facts_with_visite():
    visita = VisitaIstruzione("1A", date(2025, 3, 10), 1, 6, ["Verdi"])
    fatti = generate_asp_facts([], [], [visita], ore_giornaliere=6)
    assert 'visita("1A", 1, 1, 6).' in fatti


def test_facts_con_compresenza():
    rossi = Docente(nome="Rossi", tipo="materia", orario={(1, 1): "1A"})
    itp = Docente(nome="ITP1", tipo="itp", orario={(1, 1): "1A:Rossi"})
    fatti = generate_asp_facts([rossi, itp], [], [])
    assert 'lezione("Rossi", 1, 1, "1A").' in fatti
    assert 'compresenza("ITP1", "Rossi", 1, 1, "1A").' in fatti
    assert 'lezione("ITP1"' not in fatti


def test_priorita_itp_su_sostegno():
    rossi = Docente(nome="Rossi", tipo="materia", orario={(1, 1): "1A"})
    itp = Docente(nome="ITP1", tipo="itp", orario={(1, 1): "1A:Rossi"})
    sost = Docente(nome="Sost1", tipo="sostegno", orario={(1, 1): "1A:Rossi"})
    fatti = generate_asp_facts([rossi, itp, sost], [], [])
    assert fatti.count('compresenza("ITP1", "Rossi", 1, 1, "1A").') == 1
    assert 'compresenza("Sost1"' not in fatti


def test_weekend_ignored():
    sabato = date(2025, 3, 15)
    ass = Assenza("Rossi", sabato, 1, 2, "PERMESSO", sabato)
    fatti = generate_asp_facts([Docente(nome="Rossi", tipo="materia", orario={})], [ass], [])
    assert 'assenza' not in fatti