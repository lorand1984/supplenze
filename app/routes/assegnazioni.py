# app/routes/assegnazioni.py

from flask import Blueprint, jsonify, current_app, request, render_template
from collections import defaultdict

assegnazioni_bp = Blueprint('assegnazioni', __name__, template_folder='../templates')


def assegna_dict(assegnazione):
    """Converte un oggetto Assegnazione in dict per JSON."""
    return {
        'ora': assegnazione.ora_scoperta.ora,
        'classe': assegnazione.ora_scoperta.classe,
        'docente_supplente': assegnazione.docente_supplente_nome,
        'docente_assente': assegnazione.ora_scoperta.docente_assente_nome
    }


def raggruppa_per_docente(assegnazioni):
    """
    Raggruppa una lista di oggetti Assegnazione per docente supplente.
    Restituisce lista di dict per JSON.
    """
    gruppi = defaultdict(list)
    for a in assegnazioni:
        d = assegna_dict(a)
        docente = d['docente_supplente']
        gruppi[docente].append({
            'ora': d['ora'],
            'docente_assente': d['docente_assente'],
            'classe': d['classe']
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
    Se ?all=true restituisce tutti i modelli (lista di liste di dict).
    Altrimenti restituisce il primo modello raggruppato per docente supplente.
    """
    tutti = request.args.get('all', 'false').lower() == 'true'
    if tutti:
        modelli = current_app.config.get('ULTIMI_MODELLI', [])
        modelli_dict = []
        for modello in modelli:
            modelli_dict.append([assegna_dict(a) for a in modello])
        return jsonify(modelli_dict)
    else:
        assegnazioni = current_app.config.get('ULTIME_ASSEGNAZIONI', [])
        if not assegnazioni:
            return jsonify([])
        return jsonify(raggruppa_per_docente(assegnazioni))


@assegnazioni_bp.route('/visualizza', methods=['GET'])
def visualizza():
    return render_template('risultati.html')


@assegnazioni_bp.route('/data_info', methods=['GET'])
def data_info():
    """Restituisce la data delle ultime sostituzioni calcolate."""
    data = current_app.config.get('DATA_SUPPLENZE', None)
    return jsonify({'data': data})


@assegnazioni_bp.route('/assenze_senza_supplenza', methods=['GET'])
def get_assenze_senza_supplenza():
    """
    Restituisce le assenze che non generano supplenza:
    - ignorate (US20): docente senza lezione o classe in visita
    - senza_supplenza (US26): preavviso ≥48h e ora prima/ultima della classe
    """
    return jsonify({
        'ignorate': current_app.config.get('ASSENZE_IGNORATE', []),
        'senza_supplenza': current_app.config.get('ASSENZE_SENZA_SUPPLENZA', [])
    })