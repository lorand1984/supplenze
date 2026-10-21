import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import date
from app import create_app
from tests.generators import genera_orario, genera_assenze


@pytest.fixture(scope='module')
def generated_files():
    orario_file = genera_orario.genera_orario("orario_test.xlsx")
    assenze_file = genera_assenze.genera_assenze(
        "assenze_test.xlsx", num_assenze=10, start_date=date(2025, 3, 10)
    )
    yield orario_file, assenze_file
    os.remove(orario_file)
    os.remove(assenze_file)


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_end2end(generated_files, client):
    orario_file, assenze_file = generated_files

    with open(orario_file, 'rb') as f_orario, open(assenze_file, 'rb') as f_assenze:
        data = {
            'orario': (f_orario, os.path.basename(orario_file)),
            'assenze': (f_assenze, os.path.basename(assenze_file)),
            'data': '2025-03-10',
            'max_modelli': '10',
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')

    json_data = response.get_json()
    print(json.dumps(json_data, separators=(',', ':'), ensure_ascii=False))

    if response.status_code == 400 and "Nessuna soluzione" in json_data.get('error', ''):
        return

    assert response.status_code == 200
    num_assegnazioni = json_data['stats']['assegnazioni']
    num_modelli = json_data['stats']['modelli_trovati']

    response2 = client.get('/assegnazioni')
    assert response2.status_code == 200
    assegnazioni = response2.get_json()
    totale_supplenze = sum(len(g['supplenze']) for g in assegnazioni)
    assert totale_supplenze == num_assegnazioni

    response_all = client.get('/assegnazioni?all=true')
    assert response_all.status_code == 200
    modelli = response_all.get_json()
    assert len(modelli) == num_modelli


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-s'])