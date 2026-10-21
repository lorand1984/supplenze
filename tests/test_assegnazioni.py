import pytest
from datetime import date
from app import create_app
from app.models import Docente, Assenza, Assegnazione, OraScoperta


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_get_assegnazioni_vuote(client):
    response = client.get('/assegnazioni')
    assert response.status_code == 200
    assert response.json == []


def test_get_assegnazioni_con_dati(client):
    ora_scoperta = OraScoperta(
        data=date(2025, 3, 10), ora=2, classe='1A', docente_assente_nome='Rossi'
    )
    assegnazione = Assegnazione(ora_scoperta=ora_scoperta, docente_supplente_nome='Verdi')
    with client.application.app_context():
        client.application.config['ULTIME_ASSEGNAZIONI'] = [assegnazione]

    response = client.get('/assegnazioni')
    assert response.status_code == 200
    assert len(response.json) == 1
    gruppo = response.json[0]
    assert gruppo['docente_supplente'] == 'Verdi'
    assert len(gruppo['supplenze']) == 1
    supplenza = gruppo['supplenze'][0]
    assert supplenza['ora'] == 2
    assert supplenza['docente_assente'] == 'Rossi'
    assert supplenza['classe'] == '1A'


def test_visualizza_page(client):
    response = client.get('/visualizza')
    assert response.status_code == 200
    assert b'Assegnazioni Supplenze' in response.data


def test_data_info(client):
    with client.application.app_context():
        client.application.config['DATA_SUPPLENZE'] = '2025-03-10'
    response = client.get('/data_info')
    assert response.status_code == 200
    assert response.json['data'] == '2025-03-10'


def test_assenze_senza_supplenza_endpoint(client):
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