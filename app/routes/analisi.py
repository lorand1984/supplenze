from flask import Blueprint, jsonify, current_app
from app.analisi_orario import analizza_copertura_D

analisi_bp = Blueprint('analisi', __name__)

@analisi_bp.route('/analisi/copertura', methods=['GET'])
def get_copertura():
    """
    Restituisce le ore in cui nessun docente ha una "D" (disponibilità fissa).
    """
    # Recupera i docenti dall'ultimo orario caricato
    docenti = current_app.config.get('ULTIMI_DOCENTI', [])
    if not docenti:
        return jsonify({
            'error': 'Nessun orario caricato. Effettuare prima un upload.'
        }), 400

    ore_scoperte, copertura = analizza_copertura_D(docenti)

    # Costruisci una mappa giorno -> lista di ore
    mappa_giorni = {g: [] for g in range(1, 6)}
    for (g, o) in ore_scoperte:
        mappa_giorni[g].append(o)

    return jsonify({
        'ore_scoperte': ore_scoperte,
        'per_giorno': {f"Giorno_{g}": ore for g, ore in mappa_giorni.items() if ore},
        'dettaglio_copertura': {f"{g}-{o}": list(d) for (g, o), d in copertura.items()}
    })