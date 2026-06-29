import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import io
import tempfile
from datetime import date, datetime
from openpyxl import Workbook
from app import create_app
from app.models import Assenza

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def create_excel_file(content=b'dummy content', filename='test.xlsx'):
    return (io.BytesIO(content), filename)

def crea_excel_assenze_con_date_diverse():
    """Crea un file Excel con due assenze in date diverse."""
    wb = Workbook()
    ws = wb.active
    ws.append(["Docente", "Data", "Ora_inizio", "Ora_fine", "Tipo_assenza", "Data_comunicazione"])
    ws.append(["Rossi", datetime(2025, 3, 18), 1, 2, "PERMESSO", datetime(2025, 3, 18)])
    ws.append(["Bianchi", datetime(2025, 3, 19), 3, 3, "MALATTIA", datetime(2025, 3, 19)])
    temp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(temp.name)
    temp.close()
    return temp.name

class TestUploadEndpoint:
    def test_upload_success(self, client, monkeypatch):
        # Mock parse_all per restituire un'assenza valida per la data richiesta
        def mock_parse_all(a, b, c=None, d=6):
            # Crea un'assenza fittizia per la data 2025-03-18
            assenza = Assenza(
                docente_nome="Rossi",
                data=date(2025, 3, 18),
                ora_inizio=1,
                ora_fine=2,
                tipo_assenza="PERMESSO",
                data_comunicazione=date(2025, 3, 18)
            )
            # Restituisci anche un docente fittizio per evitare altri errori
            from app.models import Docente
            docente = Docente(nome="Rossi", orario={})
            return [docente], [assenza], []
        
        monkeypatch.setattr('app.routes.upload.parse_all', mock_parse_all)
        
        # Mock calcola_assegnazioni per evitare l'esecuzione del solver
        def mock_calcola_assegnazioni(*args, **kwargs):
            return []
        monkeypatch.setattr('app.asp_solver.calcola_assegnazioni', mock_calcola_assegnazioni)
        
        # Mock anche la funzione all'interno di upload.py
        import app.routes.upload
        monkeypatch.setattr(app.routes.upload, 'calcola_assegnazioni', mock_calcola_assegnazioni)

        data = {
            'orario': create_excel_file(),
            'assenze': create_excel_file(),
            'data': '2025-03-18',
            'max_modelli': '10'
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')

        assert response.status_code == 200
        assert response.json['message'] == 'File elaborati con successo'
        assert response.json['stats'] == {
            'docenti': 1,
            'assenze': 1,
            'visite': 0,
            'assegnazioni': 0,
            'modelli_trovati': 0,
            'max_modelli_richiesti': 10
        }

    def test_missing_orario(self, client):
        data = {
            'assenze': create_excel_file(),
            'data': '2025-03-18',
            'max_modelli': '10'
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'orario mancante' in response.json['error']

    def test_missing_assenze(self, client):
        data = {
            'orario': create_excel_file(),
            'data': '2025-03-18',
            'max_modelli': '10'
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'assenze mancante' in response.json['error']

    def test_empty_filename_orario(self, client):
        data = {
            'orario': (io.BytesIO(b''), ''),
            'assenze': create_excel_file(),
            'data': '2025-03-18',
            'max_modelli': '10'
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Nessun file selezionato per orario' in response.json['error']

    def test_empty_filename_assenze(self, client):
        data = {
            'orario': create_excel_file(),
            'assenze': (io.BytesIO(b''), ''),
            'data': '2025-03-18',
            'max_modelli': '10'
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Nessun file selezionato per assenze' in response.json['error']

    def test_wrong_extension_orario(self, client):
        data = {
            'orario': create_excel_file(filename='test.txt'),
            'assenze': create_excel_file(),
            'data': '2025-03-18',
            'max_modelli': '10'
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'formato .xlsx' in response.json['error']

    def test_wrong_extension_assenze(self, client):
        data = {
            'orario': create_excel_file(),
            'assenze': create_excel_file(filename='test.csv'),
            'data': '2025-03-18',
            'max_modelli': '10'
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'formato .xlsx' in response.json['error']

    def test_missing_date(self, client):
        data = {
            'orario': create_excel_file(),
            'assenze': create_excel_file(),
            'max_modelli': '10'
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Data non specificata' in response.json['error']

    def test_invalid_date_format(self, client):
        data = {
            'orario': create_excel_file(),
            'assenze': create_excel_file(),
            'data': '18-03-2025',
            'max_modelli': '10'
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Formato data non valido' in response.json['error']

    def test_no_assenze_for_date(self, client, monkeypatch):
        # Mock parse_all per restituire assenze con date diverse
        def mock_parse_all(a, b, c=None, d=6):
            from app.models import Assenza, Docente
            ass1 = Assenza(
                docente_nome="Rossi",
                data=date(2025, 3, 18),
                ora_inizio=1,
                ora_fine=2,
                tipo_assenza="PERMESSO",
                data_comunicazione=date(2025, 3, 18)
            )
            ass2 = Assenza(
                docente_nome="Bianchi",
                data=date(2025, 3, 19),
                ora_inizio=3,
                ora_fine=3,
                tipo_assenza="MALATTIA",
                data_comunicazione=date(2025, 3, 19)
            )
            return [], [ass1, ass2], []
        monkeypatch.setattr('app.routes.upload.parse_all', mock_parse_all)

        # Mock calcola_assegnazioni per evitare esecuzione reale
        def mock_calcola_assegnazioni(*args, **kwargs):
            return []
        monkeypatch.setattr('app.asp_solver.calcola_assegnazioni', mock_calcola_assegnazioni)
        import app.routes.upload
        monkeypatch.setattr(app.routes.upload, 'calcola_assegnazioni', mock_calcola_assegnazioni)

        data = {
            'orario': create_excel_file(),
            'assenze': create_excel_file(),
            'data': '2025-03-20',  # data senza assenze
            'max_modelli': '10'
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Nessuna assenza trovata per la data' in response.json['error']