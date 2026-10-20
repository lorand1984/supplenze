# tests/test_analisi_assenze.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date
import pytest

from app.models import Docente, Assenza, VisitaIstruzione
from app.analisi_assenze import analizza_assenze, ore_classe_in_data


# ----------------------------------------------------------------------
# Fixture comuni
# ----------------------------------------------------------------------

@pytest.fixture
def lunedi():
    """Data di lunedì (giorno_sett = 1)."""
    return date(2025, 3, 10)


@pytest.fixture
def docente_rossi():
    """
    Rossi insegna 1A alle ore 1, 2 e 3 del lunedì.
    """
    orario = {
        (1, 1): "1A",
        (1, 2): "1A",
        (1, 3): "1A",
    }
    return Docente(nome="Rossi", orario=orario)


# ----------------------------------------------------------------------
# Test US20 – Assenze ignorate
# ----------------------------------------------------------------------

class TestUS20AssenzeIgnorate:

    def test_docente_senza_lezione_in_ora(self, docente_rossi, lunedi):
        """Assenza in un'ora in cui il docente non ha lezione → ignorata."""
        assenza = Assenza(
            docente_nome="Rossi",
            data=lunedi,
            ora_inizio=4,     # Rossi non ha lezione alla 4ª ora
            ora_fine=4,
            tipo_assenza="PERMESSO",
            data_comunicazione=lunedi,
        )
        ignorate, senza_supplenza = analizza_assenze(
            [docente_rossi], [assenza], []
        )
        assert len(ignorate) == 1
        assert ignorate[0]['docente'] == "Rossi"
        assert ignorate[0]['ora'] == 4
        assert "non aveva lezione" in ignorate[0]['motivo']
        assert len(senza_supplenza) == 0

    def test_docente_non_presente_nell_orario(self, lunedi):
        """Assenza di un docente che non compare nell'orario → ignorata."""
        docente = Docente(nome="Rossi", orario={(1, 1): "1A"})
        assenza = Assenza(
            docente_nome="Bianchi",
            data=lunedi,
            ora_inizio=1,
            ora_fine=1,
            tipo_assenza="MALATTIA",
            data_comunicazione=lunedi,
        )
        ignorate, senza_supplenza = analizza_assenze([docente], [assenza], [])
        assert len(ignorate) == 1
        assert ignorate[0]['docente'] == "Bianchi"
        assert "non presente nell'orario" in ignorate[0]['motivo']
        assert len(senza_supplenza) == 0

    def test_classe_in_visita(self, docente_rossi, lunedi):
        """Assenza in un'ora in cui la classe è in visita → ignorata."""
        visita = VisitaIstruzione(
            classe="1A",
            data=lunedi,
            ora_inizio=2,
            ora_fine=2,
            docenti_accompagnatori=[],
        )
        assenza = Assenza(
            docente_nome="Rossi",
            data=lunedi,
            ora_inizio=2,
            ora_fine=2,
            tipo_assenza="PERMESSO",
            data_comunicazione=lunedi,   # preavviso insufficiente
        )
        ignorate, senza_supplenza = analizza_assenze(
            [docente_rossi], [assenza], [visita]
        )
        assert len(ignorate) == 1
        assert ignorate[0]['classe'] == "1A"
        assert "visita di istruzione" in ignorate[0]['motivo']
        assert len(senza_supplenza) == 0

    def test_assenza_valida_non_e_ignorata(self, docente_rossi, lunedi):
        """Assenza con lezione e preavviso insufficiente → NON ignorata (va in supplenza)."""
        assenza = Assenza(
            docente_nome="Rossi",
            data=lunedi,
            ora_inizio=1,
            ora_fine=1,
            tipo_assenza="PERMESSO",
            data_comunicazione=lunedi,   # preavviso < 48h
        )
        ignorate, senza_supplenza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(ignorate) == 0
        assert len(senza_supplenza) == 0   # preavviso insufficiente ⇒ va in supplenza


# ----------------------------------------------------------------------
# Test US26 – Assenze senza necessità di supplenza
# ----------------------------------------------------------------------

class TestUS26SenzaSupplenza:

    def test_preavviso_sufficiente_prima_ora(self, docente_rossi, lunedi):
        """Preavviso ≥48h e assenza sulla prima ora della classe → senza supplenza."""
        assenza = Assenza(
            docente_nome="Rossi",
            data=lunedi,
            ora_inizio=1,      # prima ora della classe 1A
            ora_fine=1,
            tipo_assenza="PERMESSO",
            data_comunicazione=date(2025, 3, 8),   # 48h prima
        )
        ignorate, senza_supplenza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(ignorate) == 0
        assert len(senza_supplenza) == 1
        assert senza_supplenza[0]['ora'] == 1
        assert senza_supplenza[0]['classe'] == "1A"
        assert "ora prima" in senza_supplenza[0]['motivo']

    def test_preavviso_sufficiente_ultima_ora(self, docente_rossi, lunedi):
        """Preavviso ≥48h e assenza sull'ultima ora della classe → senza supplenza."""
        assenza = Assenza(
            docente_nome="Rossi",
            data=lunedi,
            ora_inizio=3,      # ultima ora della classe 1A (Rossi fa 1-2-3)
            ora_fine=3,
            tipo_assenza="PERMESSO",
            data_comunicazione=date(2025, 3, 8),
        )
        ignorate, senza_supplenza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(ignorate) == 0
        assert len(senza_supplenza) == 1
        assert senza_supplenza[0]['ora'] == 3
        assert "ora ultima" in senza_supplenza[0]['motivo']

    def test_preavviso_sufficiente_ora_intermedia(self, docente_rossi, lunedi):
        """Preavviso ≥48h ma assenza su ora intermedia → NON in senza_supplenza (va in supplenza)."""
        assenza = Assenza(
            docente_nome="Rossi",
            data=lunedi,
            ora_inizio=2,      # ora intermedia (la classe 1A ha lezioni 1,2,3)
            ora_fine=2,
            tipo_assenza="PERMESSO",
            data_comunicazione=date(2025, 3, 8),
        )
        ignorate, senza_supplenza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(ignorate) == 0
        assert len(senza_supplenza) == 0

    def test_preavviso_insufficiente_prima_ora(self, docente_rossi, lunedi):
        """Preavviso <48h e assenza sulla prima ora → NON in senza_supplenza (va in supplenza)."""
        assenza = Assenza(
            docente_nome="Rossi",
            data=lunedi,
            ora_inizio=1,
            ora_fine=1,
            tipo_assenza="PERMESSO",
            data_comunicazione=lunedi,   # preavviso 0h
        )
        ignorate, senza_supplenza = analizza_assenze([docente_rossi], [assenza], [])
        assert len(ignorate) == 0
        assert len(senza_supplenza) == 0

    def test_visita_riduce_orario_effettivo(self, lunedi):
        """
        La visita rende effettive solo alcune ore della classe.
        Se la prima ora effettiva è la 2, un'assenza all'ora 2 con preavviso ≥48h è 'senza supplenza'.
        """
        docente = Docente(
            nome="Rossi",
            orario={(1, 1): "1A", (1, 2): "1A", (1, 3): "1A"},
        )
        visita = VisitaIstruzione(
            classe="1A",
            data=lunedi,
            ora_inizio=1,
            ora_fine=1,
            docenti_accompagnatori=[],
        )
        assenza = Assenza(
            docente_nome="Rossi",
            data=lunedi,
            ora_inizio=2,
            ora_fine=2,
            tipo_assenza="PERMESSO",
            data_comunicazione=date(2025, 3, 8),
        )
        ignorate, senza_supplenza = analizza_assenze([docente], [assenza], [visita])
        assert len(ignorate) == 0
        assert len(senza_supplenza) == 1
        assert senza_supplenza[0]['ora'] == 2
        assert "ora prima" in senza_supplenza[0]['motivo']


# ----------------------------------------------------------------------
# Test di ore_classe_in_data
# ----------------------------------------------------------------------

class TestOreClasseInData:

    def test_ore_classe_base(self, docente_rossi, lunedi):
        ore = ore_classe_in_data(lunedi, "1A", [docente_rossi], [])
        assert ore == {1, 2, 3}

    def test_ore_classe_con_visita(self, docente_rossi, lunedi):
        visita = VisitaIstruzione(
            classe="1A",
            data=lunedi,
            ora_inizio=2,
            ora_fine=2,
            docenti_accompagnatori=[],
        )
        ore = ore_classe_in_data(lunedi, "1A", [docente_rossi], [visita])
        assert ore == {1, 3}

    def test_ore_classe_inesistente(self, docente_rossi, lunedi):
        ore = ore_classe_in_data(lunedi, "9Z", [docente_rossi], [])
        assert ore == set()