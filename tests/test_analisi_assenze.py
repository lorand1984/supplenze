import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date
import pytest

from app.models import Docente, Assenza, VisitaIstruzione
from app.analisi_assenze import analizza_assenze, ore_classe_in_data


@pytest.fixture
def lunedi():
    return date(2025, 3, 10)


@pytest.fixture
def docente_rossi():
    return Docente(
        nome="Rossi",
        tipo="materia",
        orario={(1, 1): "1A", (1, 2): "1A", (1, 3): "1A"},
    )


class TestUS20AssenzeIgnorate:
    def test_docente_senza_lezione_in_ora(self, docente_rossi, lunedi):
        assenza = Assenza("Rossi", lunedi, 4, 4, "PERMESSO", lunedi)
        ignorate, senza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(ignorate) == 1
        assert "non aveva lezione" in ignorate[0]['motivo']
        assert len(senza) == 0

    def test_docente_non_presente_nell_orario(self, lunedi):
        docente = Docente(nome="Rossi", tipo="materia", orario={(1, 1): "1A"})
        assenza = Assenza("Bianchi", lunedi, 1, 1, "MALATTIA", lunedi)
        ignorate, senza = analizza_assenze([docente], [assenza], [])
        assert len(ignorate) == 1
        assert "non presente nell'orario" in ignorate[0]['motivo']

    def test_classe_in_visita(self, docente_rossi, lunedi):
        visita = VisitaIstruzione("1A", lunedi, 2, 2, [])
        assenza = Assenza("Rossi", lunedi, 2, 2, "PERMESSO", lunedi)
        ignorate, senza = analizza_assenze([docente_rossi], [assenza], [visita])
        assert len(ignorate) == 1
        assert "visita di istruzione" in ignorate[0]['motivo']

    def test_assenza_valida_non_e_ignorata(self, docente_rossi, lunedi):
        assenza = Assenza("Rossi", lunedi, 1, 1, "PERMESSO", lunedi)
        ignorate, senza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(ignorate) == 0
        assert len(senza) == 0


class TestUS26SenzaSupplenza:
    def test_preavviso_sufficiente_prima_ora(self, docente_rossi, lunedi):
        assenza = Assenza("Rossi", lunedi, 1, 1, "PERMESSO", date(2025, 3, 8))
        ignorate, senza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(ignorate) == 0
        assert len(senza) == 1
        assert "ora prima" in senza[0]['motivo']

    def test_preavviso_sufficiente_ultima_ora(self, docente_rossi, lunedi):
        assenza = Assenza("Rossi", lunedi, 3, 3, "PERMESSO", date(2025, 3, 8))
        ignorate, senza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(senza) == 1
        assert "ora ultima" in senza[0]['motivo']

    def test_preavviso_sufficiente_ora_intermedia(self, docente_rossi, lunedi):
        assenza = Assenza("Rossi", lunedi, 2, 2, "PERMESSO", date(2025, 3, 8))
        ignorate, senza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(senza) == 0

    def test_preavviso_insufficiente_prima_ora(self, docente_rossi, lunedi):
        assenza = Assenza("Rossi", lunedi, 1, 1, "PERMESSO", lunedi)
        ignorate, senza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(senza) == 0

    def test_visita_riduce_orario_effettivo(self, lunedi):
        docente = Docente(nome="Rossi", tipo="materia",
                          orario={(1, 1): "1A", (1, 2): "1A", (1, 3): "1A"})
        visita = VisitaIstruzione("1A", lunedi, 1, 1, [])
        assenza = Assenza("Rossi", lunedi, 2, 2, "PERMESSO", date(2025, 3, 8))
        ignorate, senza = analizza_assenze([docente], [assenza], [visita])
        assert len(senza) == 1
        assert "ora prima" in senza[0]['motivo']


class TestOreClasseInData:
    def test_ore_classe_base(self, docente_rossi, lunedi):
        assert ore_classe_in_data(lunedi, "1A", [docente_rossi], []) == {1, 2, 3}

    def test_ore_classe_con_visita(self, docente_rossi, lunedi):
        visita = VisitaIstruzione("1A", lunedi, 2, 2, [])
        assert ore_classe_in_data(lunedi, "1A", [docente_rossi], [visita]) == {1, 3}

    def test_ore_classe_inesistente(self, docente_rossi, lunedi):
        assert ore_classe_in_data(lunedi, "9Z", [docente_rossi], []) == set()