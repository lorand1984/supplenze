import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import io
import pytest
from datetime import date
from openpyxl import Workbook

from app import create_app
from app.parser import parse_orario
from tests.generators.genera_orario_con_compresenze import genera_orario_con_compresenze


# ----------------------------------------------------------------------
# Fixture
# ----------------------------------------------------------------------

@pytest.fixture(scope='module')
def orario_file():
    return genera_orario_con_compresenze("tests/fixtures/orario_con_compresenze.xlsx")


@pytest.fixture
def docenti(orario_file):
    return parse_orario(orario_file)


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def crea_excel_assenze(assenze_data):
    """Crea un file Excel di assenze in memoria (BytesIO)."""
    wb = Workbook()
    ws = wb.active
    ws.append(["Docente", "Data", "Ora_inizio", "Ora_fine", "Tipo_assenza", "Data_comunicazione"])
    for ass in assenze_data:
        ws.append(list(ass))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ----------------------------------------------------------------------
# Test parsing (US18)
# ----------------------------------------------------------------------

class TestParsingUS18:
    def test_tipi_inferiti(self, docenti):
        tipi = {d.nome: d.tipo for d in docenti}
        assert tipi["Rossi"] == "materia"
        assert tipi["Bianchi"] == "materia"
        assert tipi["Neri"] == "materia"
        assert tipi["Mario"] == "itp"
        assert tipi["Luigi"] == "itp"
        assert tipi["Anna"] == "sostegno"
        assert tipi["Paolo"] == "sostegno"

    def test_riga_vuota_saltata(self, docenti):
        nomi = [d.nome for d in docenti]
        assert "" not in nomi
        assert len(docenti) == 7

    def test_compresenza_letta(self, docenti):
        mario = next(d for d in docenti if d.nome == "Mario")
        assert mario.is_compresenza(1, 1) is True
        assert mario.get_classe_compresenza(1, 1) == "1A"
        assert mario.get_docente_materia_compresenza(1, 1) == "Rossi"


# ----------------------------------------------------------------------
# Test upload end-to-end (US18)
# ----------------------------------------------------------------------

class TestUploadUS18:
    def test_upload_con_compresenze(self, client, orario_file):
        with open(orario_file, 'rb') as f_orario:
            assenze_buf = crea_excel_assenze([
                ("Rossi", "2025-03-10", 1, 1, "PERMESSO", "2025-03-10"),
            ])
            data = {
                'orario': (f_orario, "orario_con_compresenze.xlsx"),
                'assenze': (assenze_buf, "assenze.xlsx"),
                'data': '2025-03-10',
                'max_modelli': '10',
            }
            response = client.post(
                '/genera-sostituzioni', data=data, content_type='multipart/form-data'
            )

        assert response.status_code == 200
        stats = response.json['stats']
        assert stats['assegnazioni'] >= 1

        # Recupera le assegnazioni
        response2 = client.get('/assegnazioni')
        assert response2.status_code == 200
        assegnazioni = response2.get_json()

        # Deve esserci Mario (ITP) assegnato alla classe 1A
        trovato = False
        for gruppo in assegnazioni:
            if gruppo['docente_supplente'] == 'Mario':
                for s in gruppo['supplenze']:
                    if s['classe'] == '1A' and s['ora'] == 1:
                        trovato = True
        assert trovato, "L'ITP Mario non è stato assegnato alla classe 1A all'ora 1"