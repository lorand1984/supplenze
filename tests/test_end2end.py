import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app
from tests.generators import genera_orario, genera_assenze

@pytest.fixture(scope='module')
def generated_files():
    """Genera i file Excel di test e restituisce i percorsi."""
    orario_file = genera_orario.genera_orario("orario_test.xlsx")
    assenze_file = genera_assenze.genera_assenze("assenze_test.xlsx")
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
    """Test completo: upload, recupero assegnazioni, verifica coerenza."""
    orario_file, assenze_file = generated_files

    # 1. Upload dei file
    with open(orario_file, 'rb') as f_orario, open(assenze_file, 'rb') as f_assenze:
        data = {
            'orario': (f_orario, os.path.basename(orario_file)),
            'assenze': (f_assenze, os.path.basename(assenze_file))
        }
        response = client.post('/genera-sostituzioni', data=data, content_type='multipart/form-data')

    print("\n--- Risposta POST /genera-sostituzioni ---")
    print(f"Status: {response.status_code}")
    json_data = response.get_json()
    print("JSON (compattato):")
    print(json.dumps(json_data, separators=(',', ':'), ensure_ascii=False))

    if response.status_code == 400 and "Nessuna soluzione di assegnazione trovata" in json_data.get('error', ''):
        print("OK Problema insoddisfacibile (comportamento atteso)")
        return

    assert response.status_code == 200
    assert json_data['message'] == 'File elaborati con successo'
    assert 'stats' in json_data
    num_assegnazioni = json_data['stats']['assegnazioni']
    num_modelli = json_data['stats']['modelli_trovati']

    # 2. Recupero del primo modello (formato raggruppato)
    response2 = client.get('/assegnazioni')
    print("\n--- Risposta GET /assegnazioni (default) ---")
    print(f"Status: {response2.status_code}")
    assegnazioni = response2.get_json()
    print("JSON (compattato):")
    print(json.dumps(assegnazioni, separators=(',', ':'), ensure_ascii=False))
    print(f"Numero docenti supplenti: {len(assegnazioni)}")

    assert response2.status_code == 200
    totale_supplenze = sum(len(gruppo['supplenze']) for gruppo in assegnazioni)
    assert totale_supplenze == num_assegnazioni

    # 3. Recupero di tutti i modelli (formato liste piatte)
    response_all = client.get('/assegnazioni?all=true')
    print("\n--- Risposta GET /assegnazioni?all=true ---")
    print(f"Status: {response_all.status_code}")
    modelli = response_all.get_json()
    print("JSON (compattato):")
    print(json.dumps(modelli, separators=(',', ':'), ensure_ascii=False))
    print(f"Numero modelli: {len(modelli)}")

    assert response_all.status_code == 200
    assert len(modelli) == num_modelli

    # 4. Verifica di non avere conflitti nel primo modello
    if assegnazioni:
        # Raccogli tutte le supplenze in lista piatta
        tutte = []
        for gruppo in assegnazioni:
            docente = gruppo['docente_supplente']
            for s in gruppo['supplenze']:
                tutte.append({
                    'docente_supplente': docente,
                    'ora': s['ora'],
                    'classe': s['classe']
                })
        conflitti = False
        for i, a in enumerate(tutte):
            for j, b in enumerate(tutte):
                if i < j and a['ora'] == b['ora'] and a['docente_supplente'] == b['docente_supplente']:
                    conflitti = True
                    print(f"Conflitto: {a['docente_supplente']} all'ora {a['ora']} per classi {a['classe']} e {b['classe']}")
        assert not conflitti, "Trovati conflitti di assegnazione"

if __name__ == "__main__":
    pytest.main([__file__, '-v', '-s'])