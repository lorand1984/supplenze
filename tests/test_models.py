# tests/test_models.py

import pytest
from datetime import date, timedelta
from app.models import (
    Docente,
    Assenza,
    VisitaIstruzione,
    OraScoperta,
    Assegnazione,
    calcola_ore_scoperte,
    docenti_disponibili_per_ora
)

# -------------------------------------------------------------------
# Fixtures per dati di test
# -------------------------------------------------------------------

@pytest.fixture
def orario_rossi():
    """Orario del docente Rossi con lezioni, D e libero."""
    return {
        (1, 1): "1A",   # lunedì 1: lezione 1A
        (1, 2): "1A",   # lunedì 2: lezione 1A
        (1, 3): None,   # lunedì 3: libero (non disponibile)
        (1, 4): "D",    # lunedì 4: disponibile
        (2, 1): "2B",   # martedì 1: lezione 2B
        (2, 2): None,   # martedì 2: libero
        (3, 1): "3A",   # mercoledì 1: lezione 3A
        (3, 2): "3A",   # mercoledì 2: lezione 3A
        (3, 3): "D",    # mercoledì 3: disponibile
        (4, 1): None,   # giovedì 1: libero
        (4, 2): "2B",   # giovedì 2: lezione 2B
        (5, 1): "1A",   # venerdì 1: lezione 1A
        (5, 2): "1A",   # venerdì 2: lezione 1A
        (5, 3): "D",    # venerdì 3: disponibile
    }

@pytest.fixture
def orario_bianchi():
    return {
        (1, 1): "1A",   # lunedì 1: lezione 1A
        (1, 2): None,   # lunedì 2: libero
        (1, 3): "2B",   # lunedì 3: lezione 2B
        (2, 1): "D",    # martedì 1: disponibile
        (2, 2): "3A",   # martedì 2: lezione 3A
        (4, 2): "3A",   # giovedì 2: lezione 3A
    }

@pytest.fixture
def docente_rossi(orario_rossi):
    return Docente(nome="Rossi", orario=orario_rossi.copy())

@pytest.fixture
def docente_bianchi(orario_bianchi):
    return Docente(nome="Bianchi", orario=orario_bianchi.copy())

@pytest.fixture
def docenti_list(docente_rossi, docente_bianchi):
    return [docente_rossi, docente_bianchi]

@pytest.fixture
def assenza_rossi_venerdi():
    return Assenza(
        docente_nome="Rossi",
        data=date(2025, 3, 14),  # venerdì (weekday 4)
        ora_inizio=1,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 13)  # preavviso 24h
    )

@pytest.fixture
def assenza_bianchi_giovedi():
    return Assenza(
        docente_nome="Bianchi",
        data=date(2025, 3, 13),  # giovedì (weekday 3)
        ora_inizio=2,
        ora_fine=2,
        tipo_assenza="PERMESSO",
        data_comunicazione=date(2025, 3, 12)  # preavviso 24h
    )

@pytest.fixture
def visita_1A_venerdi():
    return VisitaIstruzione(
        classe="1A",
        data=date(2025, 3, 14),  # venerdì
        ora_inizio=1,
        ora_fine=2,
        docenti_accompagnatori=["Verdi", "Neri"]
    )

# -------------------------------------------------------------------
# Test per la classe Docente (nuovi metodi)
# -------------------------------------------------------------------

class TestDocente:
    def test_ha_lezione(self, docente_rossi):
        assert docente_rossi.ha_lezione(1, 1) is True   # 1A
        assert docente_rossi.ha_lezione(1, 2) is True   # 1A
        assert docente_rossi.ha_lezione(1, 3) is False  # None
        assert docente_rossi.ha_lezione(1, 4) is False  # D
        assert docente_rossi.ha_lezione(5, 1) is True   # 1A

    def test_get_classe(self, docente_rossi):
        assert docente_rossi.get_classe(1, 1) == "1A"
        assert docente_rossi.get_classe(1, 2) == "1A"
        assert docente_rossi.get_classe(1, 3) is None
        assert docente_rossi.get_classe(1, 4) is None   # D
        assert docente_rossi.get_classe(5, 1) == "1A"

    def test_is_disponibile_per_supplenza(self, docente_rossi):
        assert docente_rossi.is_disponibile_per_supplenza(1, 4) is True
        assert docente_rossi.is_disponibile_per_supplenza(3, 3) is True
        assert docente_rossi.is_disponibile_per_supplenza(5, 3) is True
        assert docente_rossi.is_disponibile_per_supplenza(1, 1) is False  # lezione
        assert docente_rossi.is_disponibile_per_supplenza(1, 3) is False  # libero

    def test_e_libero(self, docente_rossi):
        assert docente_rossi.e_libero(1, 3) is True
        assert docente_rossi.e_libero(2, 2) is True
        assert docente_rossi.e_libero(4, 1) is True
        assert docente_rossi.e_libero(1, 1) is False  # lezione
        assert docente_rossi.e_libero(1, 4) is False  # D

    def test_ore_curricolari_settimanali(self, docente_rossi):
        # Nell'orario_rossi le ore di lezione sono: (1,1),(1,2),(2,1),(3,1),(3,2),(4,2),(5,1),(5,2) = 8
        # (5,2) è lezione, sì.
        assert docente_rossi.ore_curricolari_settimanali() == 8

    def test_ore_totali_settimanali(self, docente_rossi):
        # Aggiungiamo una supplenza
        ora_scoperta = OraScoperta(
            data=date(2025, 3, 14),
            ora=3,
            classe="2B",
            docente_assente_nome="Bianchi"
        )
        assegnazione = Assegnazione(ora_scoperta=ora_scoperta, docente_supplente_nome="Rossi")
        docente_rossi.ore_supplenza_assegnate.append(assegnazione)
        # 8 lezioni + 1 supplenza = 9
        assert docente_rossi.ore_totali_settimanali() == 9

    def test_verifica_max_consecutive_senza_supplenze(self, docente_rossi):
        # lunedì: lezioni in 1,2; D in 4 (non conta), libero in 3
        # aggiungiamo candidata ora 3 -> ore occupate: 1,2,3 -> consecutive 3 -> ok
        assert docente_rossi.verifica_max_consecutive(1, 3) is True
        # candidata ora 5 -> ore occupate: 1,2,5 -> max consec 2 -> ok
        assert docente_rossi.verifica_max_consecutive(1, 5) is True
        # venerdì: lezioni 1,2; D in 3; aggiungiamo candidata 3 (che però è D, ma l'ora candidata è 3)
        # ore occupate: lezioni 1,2 + candidata 3 = 1,2,3 -> max 3 -> ok
        assert docente_rossi.verifica_max_consecutive(5, 3) is True
        # creiamo un caso con 7 ore consecutive
        orario_molto = {(1, i): "classe" for i in range(1, 7)}  # 1-6 lezione
        docente = Docente(nome="Test", orario=orario_molto)
        # candidata ora 7 -> 1-7 consecutive 7 -> ok
        assert docente.verifica_max_consecutive(1, 7) is True
        # candidata ora 8 -> 1-6 + 8 -> max 6 -> ok
        assert docente.verifica_max_consecutive(1, 8) is True

    def test_verifica_max_consecutive_con_supplenze(self, docente_rossi):
        # assegna supplenza in (1,4) (lunedì ora 4)
        ora_scoperta = OraScoperta(
            data=date(2025, 3, 10),  # lunedì
            ora=4,
            classe="2B",
            docente_assente_nome="Bianchi"
        )
        assegnazione = Assegnazione(ora_scoperta=ora_scoperta, docente_supplente_nome="Rossi")
        docente_rossi.ore_supplenza_assegnate.append(assegnazione)
        # lunedì: lezioni 1,2; supplenza in 4; liberi 3,5,...
        # candidata ora 3 -> ore occupate: 1,2,3,4 -> consecutive 1-4 (max 4) -> ok
        assert docente_rossi.verifica_max_consecutive(1, 3) is True
        # candidata ora 5 -> ore occupate: 1,2,4,5 -> consecutive: 1-2 (2) e 4-5 (2) -> max 2 -> ok
        assert docente_rossi.verifica_max_consecutive(1, 5) is True


# -------------------------------------------------------------------
# Test per Assenza
# -------------------------------------------------------------------

class TestAssenza:
    def test_preavviso_ore(self):
        a = Assenza(
            docente_nome="Rossi",
            data=date(2025, 3, 15),
            ora_inizio=1,
            ora_fine=2,
            tipo_assenza="MALATTIA",
            data_comunicazione=date(2025, 3, 13)
        )
        assert a.preavviso_ore == 48

    def test_preavviso_sufficiente(self):
        a1 = Assenza(
            docente_nome="Rossi",
            data=date(2025, 3, 15),
            ora_inizio=1,
            ora_fine=2,
            tipo_assenza="MALATTIA",
            data_comunicazione=date(2025, 3, 13)
        )
        assert a1.preavviso_sufficiente is True
        a2 = Assenza(
            docente_nome="Rossi",
            data=date(2025, 3, 15),
            ora_inizio=1,
            ora_fine=2,
            tipo_assenza="MALATTIA",
            data_comunicazione=date(2025, 3, 14)
        )
        assert a2.preavviso_sufficiente is False

    def test_ore_interessate(self):
        a = Assenza(
            docente_nome="Rossi",
            data=date(2025, 3, 15),
            ora_inizio=2,
            ora_fine=5,
            tipo_assenza="MALATTIA",
            data_comunicazione=date(2025, 3, 13)
        )
        assert a.ore_interessate() == [2, 3, 4, 5]


# -------------------------------------------------------------------
# Test per VisitaIstruzione
# -------------------------------------------------------------------

class TestVisitaIstruzione:
    def test_ore_interessate(self):
        v = VisitaIstruzione(
            classe="1A",
            data=date(2025, 3, 14),
            ora_inizio=3,
            ora_fine=5,
            docenti_accompagnatori=["Rossi"]
        )
        assert v.ore_interessate() == [3, 4, 5]


# -------------------------------------------------------------------
# Test per OraScoperta e Assegnazione
# -------------------------------------------------------------------

class TestOraScopertaAssegnazione:
    def test_assegnazione_collega_ora(self):
        ora = OraScoperta(
            data=date(2025, 3, 14),
            ora=1,
            classe="1A",
            docente_assente_nome="Rossi"
        )
        assert ora.stato == "scoperta"
        assert ora.assegnazione is None

        assegnazione = Assegnazione(ora_scoperta=ora, docente_supplente_nome="Bianchi")
        assert ora.stato == "assegnata"
        assert ora.assegnazione is assegnazione
        assert assegnazione.ora_scoperta is ora


# -------------------------------------------------------------------
# Test per calcola_ore_scoperte
# -------------------------------------------------------------------

class TestCalcolaOreScoperte:
    def test_assenze_con_preavviso_insufficiente_genera_ore(self, docenti_list, assenza_rossi_venerdi):
        # Rossi ha lezione venerdì ore 1-2 (classe 1A)
        ore = calcola_ore_scoperte(docenti_list, [assenza_rossi_venerdi])
        assert len(ore) == 2
        for o in ore:
            assert o.data == date(2025, 3, 14)
            assert o.classe == "1A"
            assert o.docente_assente_nome == "Rossi"
            assert o.richiede_supplenza is True  # preavviso insufficiente

    def test_assenze_con_preavviso_sufficiente_genera_ore_non_richiedenti(self, docenti_list, assenza_rossi_venerdi):
        assenza_rossi_venerdi.data_comunicazione = date(2025, 3, 12)  # 48h
        ore = calcola_ore_scoperte(docenti_list, [assenza_rossi_venerdi])
        assert len(ore) == 2
        for o in ore:
            assert o.richiede_supplenza is False

    def test_assenze_in_ore_libere_non_generano_ore(self, docenti_list, assenza_rossi_venerdi):
        # modifica orario di Rossi: venerdì ore 1-2 diventano libere (None)
        docenti_list[0].orario[(5, 1)] = None
        docenti_list[0].orario[(5, 2)] = None
        ore = calcola_ore_scoperte(docenti_list, [assenza_rossi_venerdi])
        assert len(ore) == 0

    def test_assenze_in_ore_D_non_generano_ore(self, docenti_list, assenza_rossi_venerdi):
        # trasforma le ore in D
        docenti_list[0].orario[(5, 1)] = "D"
        docenti_list[0].orario[(5, 2)] = "D"
        ore = calcola_ore_scoperte(docenti_list, [assenza_rossi_venerdi])
        assert len(ore) == 0

    def test_assenze_con_classe_in_visita_non_generano_ore(self, docenti_list, assenza_rossi_venerdi, visita_1A_venerdi):
        ore = calcola_ore_scoperte(docenti_list, [assenza_rossi_venerdi], visite=[visita_1A_venerdi])
        assert len(ore) == 0

    def test_docente_non_trovato_skip(self, docenti_list, assenza_rossi_venerdi):
        assenza_rossi_venerdi.docente_nome = "Inesistente"
        ore = calcola_ore_scoperte(docenti_list, [assenza_rossi_venerdi])
        assert len(ore) == 0

    def test_molteplici_assenze(self, docenti_list, assenza_rossi_venerdi, assenza_bianchi_giovedi):
        ore = calcola_ore_scoperte(docenti_list, [assenza_rossi_venerdi, assenza_bianchi_giovedi])
        # Rossi: 2 ore, Bianchi: 1 ora (giovedì ora 2, classe 3A) = 3
        assert len(ore) == 3
        assert any(o.docente_assente_nome == "Bianchi" and o.ora == 2 and o.classe == "3A" for o in ore)


# -------------------------------------------------------------------
# Test per docenti_disponibili_per_ora
# -------------------------------------------------------------------

class TestDocentiDisponibiliPerOra:
    def test_docenti_con_D_disponibili(self, docenti_list):
        # venerdì ora 3: Rossi ha D, Bianchi non ha orario definito (libero, ma non disponibile)
        disponibili = docenti_disponibili_per_ora(docenti_list, date(2025, 3, 14), 3, [])
        assert len(disponibili) == 1
        assert disponibili[0].nome == "Rossi"

    def test_docenti_con_lezione_non_disponibili(self, docenti_list):
        # venerdì ora 1: Rossi ha lezione, Bianchi libero (non D) -> nessuno disponibile
        disponibili = docenti_disponibili_per_ora(docenti_list, date(2025, 3, 14), 1, [])
        assert len(disponibili) == 0

    def test_docenti_con_lezione_ma_classe_in_visita_disponibili(self, docenti_list, visita_1A_venerdi):
        # venerdì ora 1: Rossi ha lezione 1A, ma 1A è in visita -> Rossi diventa disponibile
        # Bianchi libero (non D) non disponibile
        disponibili = docenti_disponibili_per_ora(docenti_list, date(2025, 3, 14), 1, [visita_1A_venerdi])
        assert len(disponibili) == 1
        assert disponibili[0].nome == "Rossi"

    def test_docenti_accompagnatori_non_disponibili(self, docenti_list, visita_1A_venerdi):
        # Aggiungiamo un docente Verdi con D in quell'ora
        verdi = Docente(nome="Verdi", orario={(5,1): "D"})
        docenti_list.append(verdi)
        visita_1A_venerdi.docenti_accompagnatori.append("Verdi")  # Verdi è accompagnatore
        # venerdì ora 1: Verdi ha D ma è accompagnatore -> escluso, Rossi disponibile per visita
        disponibili = docenti_disponibili_per_ora(docenti_list, date(2025, 3, 14), 1, [visita_1A_venerdi])
        assert len(disponibili) == 1
        assert disponibili[0].nome == "Rossi"
        docenti_list.remove(verdi)

    def test_solo_D_con_visita(self, docenti_list, visita_1A_venerdi):
        # venerdì ora 3: Rossi ha D, Bianchi non ha niente
        # Con visita, Rossi rimane disponibile (D) e Bianchi no
        disponibili = docenti_disponibili_per_ora(docenti_list, date(2025, 3, 14), 3, [visita_1A_venerdi])
        assert len(disponibili) == 1
        assert disponibili[0].nome == "Rossi"