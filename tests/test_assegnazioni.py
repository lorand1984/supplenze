# tests/test_assegnazioni.py

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
    """Endpoint deve restituire le assegnazioni precedentemente memorizzate (raggruppate)."""
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
    gruppo = response.json[0]
    assert gruppo['docente_supplente'] == 'Verdi'
    assert len(gruppo['supplenze']) == 1
    supplenza = gruppo['supplenze'][0]
    assert supplenza['ora'] == 2
    assert supplenza['docente_assente'] == 'Rossi'
    assert supplenza['classe'] == '1A'