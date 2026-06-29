def test_analisi_copertura(client):
    # Simula il caricamento di un orario (o popola direttamente la config)
    with client.application.app_context():
        client.application.config['ULTIMI_DOCENTI'] = [Docente(nome="T1", orario={(1,1): "D"})]
    response = client.get('/analisi/copertura')
    assert response.status_code == 200
    data = response.get_json()
    assert 'ore_scoperte' in data
    assert (1,2) in data['ore_scoperte']  # non coperta