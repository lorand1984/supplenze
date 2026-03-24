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
        import app.routes.upload
        def mock_parse_all(a, b, c=None, d=6):
            return [], [], []
        monkeypatch.setattr(app.routes.upload, 'parse_all', mock_parse_all)

        data = {
            'orario': create_excel_file(),
            'assenze': create_excel_file()
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 200
        assert response.json['message'] == 'File elaborati con successo'
        assert response.json['stats'] == {'docenti': 0, 'assenze': 0, 'visite': 0, 'assegnazioni': 0, 'modelli_trovati': 0}

    def test_upload_parsing_error_returns_400(self, client, monkeypatch):
        import app.routes.upload
        def mock_parse_all(a, b, c=None, d=6):
            raise ValueError("Errore simulato")
        monkeypatch.setattr(app.routes.upload, 'parse_all', mock_parse_all)

        data = {
            'orario': create_excel_file(),
            'assenze': create_excel_file()
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')
        assert response.status_code == 400
        assert "Errore simulato" in response.json['error']