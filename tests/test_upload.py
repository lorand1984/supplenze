import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import io
import tempfile
from datetime import date, datetime
from openpyxl import Workbook
from app import create_app
from app.models import Assenza, Docente


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def create_excel_file(content=b'dummy content', filename='test.xlsx'):
    return (io.BytesIO(content), filename)


class TestUploadEndpoint:
    def test_upload_success(self, client, monkeypatch):
        def mock_parse_all(a, b, c=None, d=6):
            assenza = Assenza(
                docente_nome="Rossi",
                data=date(2025, 3, 18),
                ora_inizio=1,
                ora_fine=2,
                tipo_assenza="PERMESSO",
                data_comunicazione=date(2025, 3, 18),
            )
            docente = Docente(nome="Rossi", tipo="materia", orario={})
            return [docente], [assenza], []

        monkeypatch.setattr('app.routes.upload.parse_all', mock_parse_all)

        def mock_calcola_assegnazioni(*args, **kwargs):
            return []

        monkeypatch.setattr('app.asp_solver.calcola_assegnazioni', mock_calcola_assegnazioni)
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
        assert response.json['stats'] == {
            'docenti': 1,
            'assenze': 1,
            'visite': 0,
            'assegnazioni': 0,
            'modelli_trovati': 0,
            'max_modelli_richiesti': 10,
            'assenze_ignorate': 2,
            'assenze_senza_supplenza': 0,
        }

    def test_missing_orario(self, client):
        data = {'assenze': create_excel_file(), 'data': '2025-03-18', 'max_modelli': '10'}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'orario mancante' in response.json['error']

    def test_missing_assenze(self, client):
        data = {'orario': create_excel_file(), 'data': '2025-03-18', 'max_modelli': '10'}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'assenze mancante' in response.json['error']

    def test_empty_filename_orario(self, client):
        data = {'orario': (io.BytesIO(b''), ''), 'assenze': create_excel_file(),
                'data': '2025-03-18', 'max_modelli': '10'}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Nessun file selezionato per orario' in response.json['error']

    def test_empty_filename_assenze(self, client):
        data = {'orario': create_excel_file(), 'assenze': (io.BytesIO(b''), ''),
                'data': '2025-03-18', 'max_modelli': '10'}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Nessun file selezionato per assenze' in response.json['error']

    def test_wrong_extension_orario(self, client):
        data = {'orario': create_excel_file(filename='test.txt'), 'assenze': create_excel_file(),
                'data': '2025-03-18', 'max_modelli': '10'}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'formato .xlsx' in response.json['error']

    def test_wrong_extension_assenze(self, client):
        data = {'orario': create_excel_file(), 'assenze': create_excel_file(filename='test.csv'),
                'data': '2025-03-18', 'max_modelli': '10'}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'formato .xlsx' in response.json['error']

    def test_missing_date(self, client):
        data = {'orario': create_excel_file(), 'assenze': create_excel_file(), 'max_modelli': '10'}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Data non specificata' in response.json['error']

    def test_invalid_date_format(self, client):
        data = {'orario': create_excel_file(), 'assenze': create_excel_file(),
                'data': '18-03-2025', 'max_modelli': '10'}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Formato data non valido' in response.json['error']

    def test_no_assenze_for_date(self, client, monkeypatch):
        def mock_parse_all(a, b, c=None, d=6):
            ass1 = Assenza("Rossi", date(2025, 3, 18), 1, 2, "PERMESSO", date(2025, 3, 18))
            ass2 = Assenza("Bianchi", date(2025, 3, 19), 3, 3, "MALATTIA", date(2025, 3, 19))
            return [], [ass1, ass2], []
        monkeypatch.setattr('app.routes.upload.parse_all', mock_parse_all)

        def mock_calcola_assegnazioni(*args, **kwargs):
            return []
        monkeypatch.setattr('app.asp_solver.calcola_assegnazioni', mock_calcola_assegnazioni)
        import app.routes.upload
        monkeypatch.setattr(app.routes.upload, 'calcola_assegnazioni', mock_calcola_assegnazioni)

        data = {'orario': create_excel_file(), 'assenze': create_excel_file(),
                'data': '2025-03-20', 'max_modelli': '10'}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Nessuna assenza trovata per la data' in response.json['error']

    def test_upload_include_statistiche_us20_us26(self, client, monkeypatch):
        def mock_parse_all(a, b, c=None, d=6):
            docente = Docente(nome="Rossi", tipo="materia", orario={(1, 1): "1A"})
            ass_ignorata = Assenza("Rossi", date(2025, 3, 10), 2, 2, "PERMESSO", date(2025, 3, 10))
            ass_senza = Assenza("Rossi", date(2025, 3, 10), 1, 1, "PERMESSO", date(2025, 3, 8))
            return [docente], [ass_ignorata, ass_senza], []

        def mock_calcola_assegnazioni(*args, **kwargs):
            return []

        monkeypatch.setattr('app.routes.upload.parse_all', mock_parse_all)
        monkeypatch.setattr('app.asp_solver.calcola_assegnazioni', mock_calcola_assegnazioni)
        import app.routes.upload
        monkeypatch.setattr(app.routes.upload, 'calcola_assegnazioni', mock_calcola_assegnazioni)

        data = {'orario': create_excel_file(), 'assenze': create_excel_file(),
                'data': '2025-03-10', 'max_modelli': '10'}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        stats = response.json['stats']
        assert stats['assenze_ignorate'] == 1
        assert stats['assenze_senza_supplenza'] == 1

    def test_endpoint_assenze_senza_supplenza(self, client):
        with client.application.app_context():
            client.application.config['ASSENZE_IGNORATE'] = [
                {'docente': 'Rossi', 'data': '2025-03-10', 'ora': 2,
                 'classe': None, 'motivo': "Il docente non aveva lezione in quest'ora"}
            ]
            client.application.config['ASSENZE_SENZA_SUPPLENZA'] = [
                {'docente': 'Rossi', 'data': '2025-03-10', 'ora': 1,
                 'classe': '1A', 'motivo': "Preavviso ≥48h e ora prima della classe"}
            ]
        response = client.get('/assenze_senza_supplenza')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['ignorate']) == 1
        assert len(data['senza_supplenza']) == 1

    def test_endpoint_assenze_senza_supplenza_vuoto(self, client):
        with client.application.app_context():
            client.application.config['ASSENZE_IGNORATE'] = []
            client.application.config['ASSENZE_SENZA_SUPPLENZA'] = []
        response = client.get('/assenze_senza_supplenza')
        assert response.status_code == 200
        assert response.get_json() == {'ignorate': [], 'senza_supplenza': []}