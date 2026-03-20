from flask import Blueprint, jsonify, current_app, request, render_template
from collections import defaultdict

assegnazioni_bp = Blueprint('assegnazioni', __name__, template_folder='../templates')

def raggruppa_per_docente(assegnazioni):
    """
    Raggruppa una lista piatta di assegnazioni per docente_supplente.
    Input: lista di dict con chiavi: 'ora', 'classe', 'docente_supplente', 'docente_assente'
    Output: lista di dict con struttura:
        [{'docente_supplente': '...', 'supplenze': [{'ora':..., 'docente_assente':..., 'classe':...}, ...]}, ...]
    """
    gruppi = defaultdict(list)
    for a in assegnazioni:
        docente = a['docente_supplente']
        gruppi[docente].append({
            'ora': a['ora'],
            'docente_assente': a['docente_assente'],
            'classe': a['classe']
        })
    risultato = []
    for docente, lista in gruppi.items():
        risultato.append({
            'docente_supplente': docente,
            'supplenze': lista
        })
    return risultato

@assegnazioni_bp.route('/assegnazioni', methods=['GET'])
def get_assegnazioni():
    """
    Restituisce le assegnazioni.
    - Se ?all=true restituisce tutti i modelli (lista di liste piatte).
    - Altrimenti restituisce il primo modello raggruppato per docente supplente.
    """
    tutti = request.args.get('all', 'false').lower() == 'true'
    if tutti:
        modelli = current_app.config.get('ULTIMI_MODELLI', [])
        return jsonify(modelli)
    else:
        assegnazioni = current_app.config.get('ULTIME_ASSEGNAZIONI', [])
        # Se non ci sono assegnazioni, restituisci lista vuota
        if not assegnazioni:
            return jsonify([])
        # Raggruppa e restituisci
        return jsonify(raggruppa_per_docente(assegnazioni))

@assegnazioni_bp.route('/visualizza', methods=['GET'])
def visualizza():
    """Pagina HTML per visualizzare i risultati (frontend)."""
    return render_template('risultati.html')