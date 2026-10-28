import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import date, timedelta

from app.parser import parse_orario
from app.models import Assenza
from app.asp_facts import generate_asp_facts
from app.asp_solver import calcola_assegnazioni
from tests.generators.genera_orario_con_compresenze import genera_orario_con_compresenze


@pytest.fixture(scope='module')
def orario_file():
    return genera_orario_con_compresenze("tests/fixtures/orario_con_compresenze.xlsx")


@pytest.fixture
def docenti(orario_file):
    return parse_orario(orario_file)


def _assenza(docente, giorno=1, ora=1, preavviso_ore=0):
    data = date(2025, 3, 10) + timedelta(days=giorno - 1)
    data_com = data - timedelta(days=preavviso_ore // 24)
    return Assenza(docente, data, ora, ora, "PERMESSO", data_com)


# ----------------------------------------------------------------------
# Parsing: tipo inferito dal prefisso
# ----------------------------------------------------------------------

class TestParsingSenzaTipo:
    def test_tipi_inferiti(self, docenti):
        tipi = {d.nome: d.tipo for d in docenti}
        assert tipi["Rossi"] == "materia"
        assert tipi["Bianchi"] == "materia"
        assert tipi["Neri"] == "materia"
        assert tipi["Mario"] == "itp"        # da ITP_Mario
        assert tipi["Luigi"] == "itp"        # da ITP_Luigi
        assert tipi["Anna"] == "sostegno"    # da Sost_Anna
        assert tipi["Paolo"] == "sostegno"   # da Sost_Paolo

    def test_compresenza_letta(self, docenti):
        mario = next(d for d in docenti if d.nome == "Mario")
        assert mario.is_compresenza(1, 1) is True
        assert mario.get_classe_compresenza(1, 1) == "1A"
        assert mario.get_docente_materia_compresenza(1, 1) == "Rossi"

    def test_riga_vuota_saltata(self, docenti):
        # La riga vuota tra materia e ITP non deve creare un docente
        nomi = [d.nome for d in docenti]
        assert "" not in nomi
        assert len(docenti) == 7


# ----------------------------------------------------------------------
# Fatti ASP: priorità ITP > sostegno
# ----------------------------------------------------------------------

class TestFattiASPSenzaTipo:
    def test_compresenza_generata(self, docenti):
        fatti = generate_asp_facts(docenti, [], [])
        assert 'compresenza("Mario", "Rossi", 1, 1, "1A").' in fatti
        assert 'compresenza("Luigi", "Neri", 2, 1, "1A").' in fatti

    def test_priorita_itp_su_sostegno(self, docenti):
        """Mario (ITP) e Paolo (sostegno) sono entrambi in compresenza con Bianchi
        in 2B Lun-1? No: Paolo è con Bianchi in 2B Lun-1, Mario è con Bianchi in 2B Mar-1.
        Per testare la priorità, serve una stessa (ora, classe, docente_materia) con ITP e sostegno.
        Aggiungiamo un caso apposito: entrambi con Rossi in 1A Lun-1 (Mario + Anna)."""
        fatti = generate_asp_facts(docenti, [], [])
        # Mario e Anna sono entrambi con Rossi in 1A Lun-1: vince Mario (ITP)
        assert 'compresenza("Mario", "Rossi", 1, 1, "1A").' in fatti
        assert 'compresenza("Anna", "Rossi", 1, 1, "1A").' not in fatti


# ----------------------------------------------------------------------
# Solver: supplenza automatica
# ----------------------------------------------------------------------

class TestSolverSenzaTipo:
    def test_rossi_assente_lun1_itp_subentra(self, docenti):
        ass = _assenza("Rossi", giorno=1, ora=1)
        assegnazioni = calcola_assegnazioni(docenti, [ass], [])
        assert len(assegnazioni) == 1
        assert assegnazioni[0].docente_supplente_nome == "Mario"
        assert assegnazioni[0].ora_scoperta.classe == "1A"

    def test_priorita_itp_su_sostegno_nel_solver(self, docenti):
        # Rossi assente Lun-1: Mario (ITP) e Anna (sostegno) sono in compresenza.
        # Il fatto compresenza esiste solo per Mario → Mario subentra.
        ass = _assenza("Rossi", giorno=1, ora=1)
        assegnazioni = calcola_assegnazioni(docenti, [ass], [])
        assert assegnazioni[0].docente_supplente_nome == "Mario"

    def test_neri_assente_mar1_itp_luigi_subentra(self, docenti):
        ass = _assenza("Neri", giorno=2, ora=1)
        assegnazioni = calcola_assegnazioni(docenti, [ass], [])
        assert len(assegnazioni) == 1
        assert assegnazioni[0].docente_supplente_nome == "Luigi"
        assert assegnazioni[0].ora_scoperta.classe == "1A"

    def test_supplenza_automatica_su_prima_ora_con_preavviso_sufficiente(self, docenti):
        ass = _assenza("Rossi", giorno=1, ora=1, preavviso_ore=72)
        assegnazioni = calcola_assegnazioni(docenti, [ass], [])
        assert len(assegnazioni) == 1
        assert assegnazioni[0].docente_supplente_nome == "Mario"

    def test_itp_assente_non_genera_supplenza_automatica(self, docenti):
        # Mario (ITP) assente, Rossi presente: la lezione di Rossi non è scoperta
        ass = _assenza("Mario", giorno=1, ora=1)
        assegnazioni = calcola_assegnazioni(docenti, [ass], [])
        assert all(not (a.ora_scoperta.classe == "1A" and a.ora_scoperta.ora == 1)
                   for a in assegnazioni)