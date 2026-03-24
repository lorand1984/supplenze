import pytest
import io
from app import create_app

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
        # Mock parse_all per evitare il parsing reale
        def mock_parse_all(a, b, c=None, d=6):
            return [], [], []
        monkeypatch.setattr('app.routes.upload.parse_all', mock_parse_all)

        # Mock calcola_assegnazioni per evitare l'esecuzione del solver
        def mock_calcola_assegnazioni(*args, **kwargs):
            return []  # primo modello vuoto
        monkeypatch.setattr('app.routes.upload.calcola_assegnazioni', mock_calcola_assegnazioni)

        data = {
            'orario': create_excel_file(),
            'assenze': create_excel_file()
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        assert response.json['message'] == 'File elaborati con successo'
        assert response.json['stats'] == {'docenti': 0, 'assenze': 0, 'visite': 0, 'assegnazioni': 0, 'modelli_trovati': 0}

    def test_missing_orario(self, client):
        data = {'assenze': create_excel_file()}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'orario mancante' in response.json['error']

    def test_missing_assenze(self, client):
        data = {'orario': create_excel_file()}
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'assenze mancante' in response.json['error']

    def test_empty_filename_orario(self, client):
        data = {
            'orario': (io.BytesIO(b''), ''),
            'assenze': create_excel_file()
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Nessun file selezionato per orario' in response.json['error']

    def test_empty_filename_assenze(self, client):
        data = {
            'orario': create_excel_file(),
            'assenze': (io.BytesIO(b''), '')
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'Nessun file selezionato per assenze' in response.json['error']

    def test_wrong_extension_orario(self, client):
        data = {
            'orario': create_excel_file(filename='test.txt'),
            'assenze': create_excel_file()
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'formato .xlsx' in response.json['error']

    def test_wrong_extension_assenze(self, client):
        data = {
            'orario': create_excel_file(),
            'assenze': create_excel_file(filename='test.csv')
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert 'formato .xlsx' in response.json['error']

    def test_upload_parsing_error_returns_400(self, client, monkeypatch):
        def mock_parse_all(a, b, c=None, d=6):
            raise ValueError("Errore simulato")
        monkeypatch.setattr('app.routes.upload.parse_all', mock_parse_all)

        data = {
            'orario': create_excel_file(),
            'assenze': create_excel_file()
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert "Errore simulato" in response.json['error']