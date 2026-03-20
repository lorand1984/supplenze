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
    """Endpoint senza assegnazioni deve restituire lista vuota."""
    response = client.get('/assegnazioni')
    assert response.status_code == 200
    assert response.json == []

def test_get_assegnazioni_con_dati(client):
    """Endpoint deve restituire le assegnazioni precedentemente memorizzate."""
    # Simula la memorizzazione di alcune assegnazioni
    ora_scoperta = OraScoperta(
        data=date(2025, 3, 10),
        ora=2,
        classe='1A',
        docente_assente_nome='Rossi'
    )
    assegnazione = Assegnazione(
        ora_scoperta=ora_scoperta,
        docente_supplente_nome='Verdi'
    )
    with client.application.app_context():
        client.application.config['ULTIME_ASSEGNAZIONI'] = [assegnazione]

    response = client.get('/assegnazioni')
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]['data'] == '2025-03-10'
    assert response.json[0]['ora'] == 2
    assert response.json[0]['classe'] == '1A'
    assert response.json[0]['docente_supplente'] == 'Verdi'
    assert response.json[0]['docente_assente'] == 'Rossi'