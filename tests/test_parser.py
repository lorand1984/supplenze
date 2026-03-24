import pytest
import os
import tempfile
from datetime import date, datetime
from openpyxl import Workbook

from app.parser import parse_orario, parse_assenze, parse_all, parse_visite
from app.models import Docente, Assenza

# ----------------------------------------------------------------------
# Helper per creare file Excel temporanei
# ----------------------------------------------------------------------

def crea_excel_orario(docenti_data):
    """Crea un file Excel di orario con i dati forniti.
    docenti_data: lista di tuple (nome, lista_valori_per_colonne)
    Le colonne sono: Docente, Lun-1, Lun-2, ..., Ven-7 (35 colonne dopo il nome)
    """
    wb = Workbook()
    ws = wb.active

    # Intestazioni
    headers = ["Docente"] + [f"{giorno}-{ora}" for giorno in ["Lun","Mar","Mer","Gio","Ven"] for ora in range(1,8)]
    ws.append(headers)

    for nome, valori in docenti_data:
        riga = [nome] + list(valori)
        ws.append(riga)

    temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(temp.name)
    temp.close()
    return temp.name

def crea_excel_assenze(assenze_data):
    """Crea un file Excel di assenze.
    assenze_data: lista di tuple (docente, data, ora_inizio, ora_fine, tipo, data_com)
    """
    wb = Workbook()
    ws = wb.active

    headers = ["Docente", "Data", "Ora_inizio", "Ora_fine", "Tipo_assenza", "Data_comunicazione"]
    ws.append(headers)

    for ass in assenze_data:
        riga = list(ass)
        # Converti date in datetime per openpyxl
        for i in [1,5]:
            if isinstance(riga[i], date):
                riga[i] = datetime.combine(riga[i], datetime.min.time())
        ws.append(riga)

    temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(temp.name)
    temp.close()
    return temp.name

def crea_excel_visite(visite_data):
    """Crea un file Excel di visite (solo per test)."""
    wb = Workbook()
    ws = wb.active
    headers = ["Classe", "Data", "Docenti_accompagnatori"]
    ws.append(headers)
    for vis in visite_data:
        ws.append([vis[0], vis[1], vis[2]])
    temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(temp.name)
    temp.close()
    return temp.name

# ----------------------------------------------------------------------
# Test parse_orario
# ----------------------------------------------------------------------

class TestParseOrario:
    def test_orario_valido(self):
        dati = [
            ("Rossi", ["1A", "1A", None, "D", None, None, None,   # Lun
                       "2B", None, None, None, None, None, None,   # Mar
                       None, None, None, None, None, None, None,   # Mer
                       None, None, None, None, None, None, None,   # Gio
                       "1A", "1A", "D", None, None, None, None]),  # Ven
        ]
        file_path = crea_excel_orario(dati)
        try:
            docenti = parse_orario(file_path)
            assert len(docenti) == 1
            docente = docenti[0]
            assert docente.nome == "Rossi"
            assert docente.orario[(1,1)] == "1A"   # Lun-1
            assert docente.orario[(1,2)] == "1A"   # Lun-2
            assert docente.orario[(1,3)] is None   # Lun-3
            assert docente.orario[(1,4)] == "D"    # Lun-4
            assert docente.orario[(2,1)] == "2B"   # Mar-1
            assert docente.orario[(5,1)] == "1A"   # Ven-1
            assert docente.orario[(5,3)] == "D"    # Ven-3
        finally:
            os.unlink(file_path)

    def test_orario_con_righe_vuote(self):
        dati = [
            ("Rossi", ["1A"] + [None]*34),
            (None, [None]*35),
        ]
        file_path = crea_excel_orario(dati)
        try:
            docenti = parse_orario(file_path)
            assert len(docenti) == 1
            assert docenti[0].nome == "Rossi"
        finally:
            os.unlink(file_path)

    def test_orario_missing_file(self):
        with pytest.raises(FileNotFoundError):
            parse_orario("file_inesistente.xlsx")

    def test_orario_intestazione_errata(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["Nome", "Colonna1", "Colonna2"])
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            with pytest.raises(ValueError, match="La prima colonna deve essere 'Docente'"):
                parse_orario(temp.name)
        finally:
            os.unlink(temp.name)

    def test_orario_giorno_non_riconosciuto(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["Docente", "Xxx-1", "Lun-2"])
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            # La colonna "Xxx-1" viene ignorata, ma almeno una colonna valida deve esistere.
            # In questo caso "Lun-2" è valida, quindi il parsing procede.
            docenti = parse_orario(temp.name)
            assert len(docenti) == 0  # nessun docente? In realtà abbiamo una riga con Rossi? No, non abbiamo inserito righe docenti.
            # Aggiungiamo una riga per avere un docente
            ws.append(["Rossi", "1A", "1A"])
            temp2 = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
            wb.save(temp2.name)
            temp2.close()
            try:
                docenti = parse_orario(temp2.name)
                assert len(docenti) == 1
                # Solo le colonne valide vengono considerate: "Lun-2" è (1,2)
                assert (1,2) in docenti[0].orario
                assert (1,1) not in docenti[0].orario
            finally:
                os.unlink(temp2.name)
        finally:
            os.unlink(temp.name)

    def test_orario_multiple_docenti(self):
        dati = [
            ("Rossi", ["1A"]*7 + [None]*28),
            ("Bianchi", ["D"]*7 + [None]*28),
        ]
        file_path = crea_excel_orario(dati)
        try:
            docenti = parse_orario(file_path)
            assert len(docenti) == 2
            assert docenti[0].nome == "Rossi"
            assert docenti[1].nome == "Bianchi"
            assert docenti[1].orario[(1,1)] == "D"
        finally:
            os.unlink(file_path)

    def test_orario_colonne_extra(self):
        wb = Workbook()
        ws = wb.active
        headers = ["Docente"] + [f"{g}-{o}" for g in ["Lun","Mar","Mer","Gio","Ven"] for o in range(1,8)] + ["Extra1", "Extra2"]
        ws.append(headers)
        ws.append(["Rossi"] + ["1A"]*35 + ["ignorato", "ignorato"])
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            docenti = parse_orario(temp.name)
            assert len(docenti) == 1
            assert len(docenti[0].orario) == 35  # solo le 35 ore valide
        finally:
            os.unlink(temp.name)

    def test_orario_valori_non_stringa(self):
        wb = Workbook()
        ws = wb.active
        headers = ["Docente"] + [f"{g}-{o}" for g in ["Lun","Mar","Mer","Gio","Ven"] for o in range(1,8)]
        ws.append(headers)
        ws.append(["Rossi"] + [123] + [None]*34)
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            docenti = parse_orario(temp.name)
            assert docenti[0].orario[(1,1)] == "123"
        finally:
            os.unlink(temp.name)

    def test_orario_spazi_bianchi(self):
        wb = Workbook()
        ws = wb.active
        headers = ["Docente"] + [f"{g}-{o}" for g in ["Lun","Mar","Mer","Gio","Ven"] for o in range(1,8)]
        ws.append(headers)
        ws.append(["Rossi"] + ["", "   "] + [None]*33)
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            docenti = parse_orario(temp.name)
            assert docenti[0].orario[(1,1)] is None
            assert docenti[0].orario[(1,2)] is None
        finally:
            os.unlink(temp.name)

    def test_orario_intestazione_con_spazi(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["Docente", "Lun-1 ", "Lun-2"])
        ws.append(["Rossi", "1A", "1A"])
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            docenti = parse_orario(temp.name)
            assert len(docenti) == 1
            assert docenti[0].orario[(1,1)] == "1A"
            assert docenti[0].orario[(1,2)] == "1A"
        finally:
            os.unlink(temp.name)

# ----------------------------------------------------------------------
# Test parse_assenze
# ----------------------------------------------------------------------

class TestParseAssenze:
    def test_assenze_valide(self):
        dati = [
            ("Rossi", date(2025,3,14), 1, 2, "PERMESSO", date(2025,3,13)),
            ("Bianchi", date(2025,3,15), 3, 5, "MALATTIA", date(2025,3,14)),
        ]
        file_path = crea_excel_assenze(dati)
        try:
            assenze = parse_assenze(file_path)
            assert len(assenze) == 2
            a1 = assenze[0]
            assert a1.docente_nome == "Rossi"
            assert a1.data == date(2025,3,14)
            assert a1.ora_inizio == 1
            assert a1.ora_fine == 2
            assert a1.tipo_assenza == "PERMESSO"
            assert a1.data_comunicazione == date(2025,3,13)

            a2 = assenze[1]
            assert a2.docente_nome == "Bianchi"
            assert a2.ora_inizio == 3
            assert a2.ora_fine == 5
        finally:
            os.unlink(file_path)

    def test_assenze_ora_inizio_fuori_range(self):
        dati = [("Rossi", date(2025,3,14), 0, 2, "PERMESSO", date(2025,3,13))]
        file_path = crea_excel_assenze(dati)
        try:
            with pytest.raises(ValueError, match="Ora_inizio deve essere compreso tra 1 e 7"):
                parse_assenze(file_path)
        finally:
            os.unlink(file_path)

    def test_assenze_ora_fine_minore_inizio(self):
        dati = [("Rossi", date(2025,3,14), 3, 2, "PERMESSO", date(2025,3,13))]
        file_path = crea_excel_assenze(dati)
        try:
            with pytest.raises(ValueError, match="Ora_fine non può essere minore di Ora_inizio"):
                parse_assenze(file_path)
        finally:
            os.unlink(file_path)

    def test_assenze_intestazione_errata(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["Docente", "Data", "Ora_inizio", "Ora_fine"])
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            with pytest.raises(ValueError, match="Intestazioni non corrispondenti"):
                parse_assenze(temp.name)
        finally:
            os.unlink(temp.name)

    def test_assenze_ora_come_float(self):
        dati = [("Rossi", date(2025,3,14), 2.0, 3.0, "PERMESSO", date(2025,3,13))]
        file_path = crea_excel_assenze(dati)
        try:
            assenze = parse_assenze(file_path)
            assert len(assenze) == 1
            assert assenze[0].ora_inizio == 2
            assert assenze[0].ora_fine == 3
        finally:
            os.unlink(file_path)

    def test_assenze_ora_come_float_non_intero(self):
        dati = [("Rossi", date(2025,3,14), 2.5, 3, "PERMESSO", date(2025,3,13))]
        file_path = crea_excel_assenze(dati)
        try:
            with pytest.raises(ValueError, match="Ora_inizio deve essere un numero intero"):
                parse_assenze(file_path)
        finally:
            os.unlink(file_path)

    def test_assenze_data_come_stringa(self):
        wb = Workbook()
        ws = wb.active
        headers = ["Docente", "Data", "Ora_inizio", "Ora_fine", "Tipo_assenza", "Data_comunicazione"]
        ws.append(headers)
        ws.append(["Rossi", "2025-03-14", 2, 3, "PERMESSO", "2025-03-13"])
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            assenze = parse_assenze(temp.name)
            assert len(assenze) == 1
            a = assenze[0]
            assert a.docente_nome == "Rossi"
            assert a.data == date(2025, 3, 14)
            assert a.ora_inizio == 2
            assert a.ora_fine == 3
            assert a.tipo_assenza == "PERMESSO"
            assert a.data_comunicazione == date(2025, 3, 13)
        finally:
            os.unlink(temp.name)

    def test_assenze_riga_vuota(self):
        dati = [
            ("Rossi", date(2025,3,14), 1, 2, "PERMESSO", date(2025,3,13)),
            (None, None, None, None, None, None),
        ]
        file_path = crea_excel_assenze(dati)
        try:
            assenze = parse_assenze(file_path)
            assert len(assenze) == 1
        finally:
            os.unlink(file_path)

    def test_assenze_docente_non_stringa(self):
        dati = [(123, date(2025,3,14), 1, 2, "PERMESSO", date(2025,3,13))]
        file_path = crea_excel_assenze(dati)
        try:
            with pytest.raises(ValueError, match="Nome docente deve essere una stringa"):
                parse_assenze(file_path)
        finally:
            os.unlink(file_path)

    def test_assenze_tipo_assenza_numerico(self):
        dati = [("Rossi", date(2025,3,14), 1, 2, 123, date(2025,3,13))]
        file_path = crea_excel_assenze(dati)
        try:
            with pytest.raises(ValueError, match="Tipo_assenza deve essere una stringa"):
                parse_assenze(file_path)
        finally:
            os.unlink(file_path)

    def test_assenze_colonne_mancanti(self):
        wb = Workbook()
        ws = wb.active
        headers = ["Docente", "Data", "Ora_inizio", "Ora_fine", "Tipo_assenza"]
        ws.append(headers)
        ws.append(["Rossi", date(2025,3,14), 1, 2, "PERMESSO"])
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            with pytest.raises(ValueError, match="Intestazioni non corrispondenti"):
                parse_assenze(temp.name)
        finally:
            os.unlink(temp.name)

    def test_assenze_data_comunicazione_mancante(self):
        dati = [("Rossi", date(2025,3,14), 1, 2, "PERMESSO", None)]
        file_path = crea_excel_assenze(dati)
        try:
            with pytest.raises(ValueError, match="Data comunicazione non valida"):
                parse_assenze(file_path)
        finally:
            os.unlink(file_path)

# ----------------------------------------------------------------------
# Test parse_visite
# ----------------------------------------------------------------------

class TestParseVisite:
    def test_visite_valide(self):
        dati = [
            ("1A", date(2025,3,14), "Rossi, Verdi"),
            ("2B", date(2025,3,15), "Bianchi"),
        ]
        file_path = crea_excel_visite(dati)
        try:
            visite = parse_visite(file_path, ore_giornaliere=6)
            assert len(visite) == 2
            v1 = visite[0]
            assert v1.classe == "1A"
            assert v1.data == date(2025,3,14)
            assert v1.ora_inizio == 1
            assert v1.ora_fine == 6
            assert v1.docenti_accompagnatori == ["Rossi", "Verdi"]
            v2 = visite[1]
            assert v2.classe == "2B"
            assert v2.docenti_accompagnatori == ["Bianchi"]
        finally:
            os.unlink(file_path)

    def test_visite_intestazione_errata(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["Classe", "Data", "Ora_inizio", "Docenti"])  # sbagliato
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            with pytest.raises(ValueError, match="Intestazioni non corrispondenti"):
                parse_visite(temp.name)
        finally:
            os.unlink(temp.name)

    def test_visite_docenti_mancanti(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["Classe", "Data", "Docenti_accompagnatori"])
        ws.append(["1A", datetime(2025,3,14), None])  # cella vuota (None)
        temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(temp.name)
        temp.close()
        try:
            visite = parse_visite(temp.name)
            assert len(visite) == 1
            assert visite[0].docenti_accompagnatori == []
        finally:
            os.unlink(temp.name)

# ----------------------------------------------------------------------
# Test parse_all
# ----------------------------------------------------------------------

class TestParseAll:
    def test_parse_all_success(self):
        orario_dati = [("Rossi", ["1A"]*7 + [None]*28)]
        orario_path = crea_excel_orario(orario_dati)

        assenze_dati = [("Rossi", date(2025,3,14), 1, 2, "PERMESSO", date(2025,3,13))]
        assenze_path = crea_excel_assenze(assenze_dati)

        try:
            docenti, assenze, visite = parse_all(orario_path, assenze_path, None, 6)
            assert len(docenti) == 1
            assert len(assenze) == 1
            assert len(visite) == 0
        finally:
            os.unlink(orario_path)
            os.unlink(assenze_path)

    def test_parse_all_con_errore_orario(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["Cattiva", "Intestazione"])
        ws.append(["Rossi", "1A"])
        orario_path = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(orario_path.name)
        orario_path.close()

        assenze_dati = [("Rossi", date(2025,3,14), 1, 2, "PERMESSO", date(2025,3,13))]
        assenze_path = crea_excel_assenze(assenze_dati)

        try:
            with pytest.raises(ValueError, match="La prima colonna deve essere 'Docente'"):
                parse_all(orario_path.name, assenze_path, None, 6)
        finally:
            os.unlink(orario_path.name)
            os.unlink(assenze_path)