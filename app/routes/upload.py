import os
import tempfile
from flask import Blueprint, request, jsonify, current_app, render_template
from werkzeug.utils import secure_filename

from app.parser import parse_all
from app.asp_solver import calcola_assegnazioni

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/', methods=['GET'])
def upload_page():
    """Pagina HTML di upload (frontend)."""
    return render_template('upload.html')

@upload_bp.route('/genera-sostituzioni', methods=['POST'])
def upload_files():
    """
    Endpoint per il caricamento dei file Excel (orario, assenze, visite opzionale).
    Effettua il parsing, calcola le assegnazioni e memorizza il risultato.
    """
    # Verifica presenza dei file obbligatori
    if 'orario' not in request.files:
        return jsonify({'error': 'File orario mancante'}), 400
    if 'assenze' not in request.files:
        return jsonify({'error': 'File assenze mancante'}), 400

    orario_file = request.files['orario']
    assenze_file = request.files['assenze']

    # Controllo che i file non abbiano nome vuoto
    if orario_file.filename == '':
        return jsonify({'error': 'Nessun file selezionato per orario'}), 400
    if assenze_file.filename == '':
        return jsonify({'error': 'Nessun file selezionato per assenze'}), 400

    # Verifica estensioni
    if not allowed_file(orario_file.filename):
        return jsonify({'error': 'Il file orario deve essere in formato .xlsx'}), 400
    if not allowed_file(assenze_file.filename):
        return jsonify({'error': 'Il file assenze deve essere in formato .xlsx'}), 400

    # Crea directory temporanea
    temp_dir = tempfile.mkdtemp()
    orario_path = os.path.join(temp_dir, secure_filename(orario_file.filename))
    assenze_path = os.path.join(temp_dir, secure_filename(assenze_file.filename))
    visite_path = None

    try:
        # Salva i file
        orario_file.save(orario_path)
        assenze_file.save(assenze_path)

        # Gestione file visite opzionale
        visite_file = request.files.get('visite')
        if visite_file and visite_file.filename != '':
            if not allowed_file(visite_file.filename):
                return jsonify({'error': 'Il file visite deve essere in formato .xlsx'}), 400
            visite_path = os.path.join(temp_dir, secure_filename(visite_file.filename))
            visite_file.save(visite_path)

        # Parsing dei file
        ore_giornaliere = current_app.config.get('ORE_GIORNALIERE', 6)
        docenti, assenze, visite = parse_all(
            orario_path, assenze_path, visite_path, ore_giornaliere
        )

        # Calcola il primo modello (per l'endpoint standard)
        assegnazioni = calcola_assegnazioni(docenti, assenze, visite, ore_giornaliere, tutti_modelli=False)

        # Calcola tutti i modelli (per debug o visualizzazione alternativa)
        modelli = calcola_assegnazioni(docenti, assenze, visite, ore_giornaliere, tutti_modelli=True)

        # Memorizza entrambi nella configurazione dell'app
        current_app.config['ULTIME_ASSEGNAZIONI'] = assegnazioni
        current_app.config['ULTIMI_MODELLI'] = modelli

        return jsonify({
            'message': 'File elaborati con successo',
            'stats': {
                'docenti': len(docenti),
                'assenze': len(assenze),
                'visite': len(visite),
                'assegnazioni': len(assegnazioni) if assegnazioni else 0,
                'modelli_trovati': len(modelli)
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Errore durante l\'elaborazione: {str(e)}'}), 400

    finally:
        # Pulizia file temporanei
        for path in [orario_path, assenze_path, visite_path]:
            if path and os.path.exists(path):
                os.remove(path)
        os.rmdir(temp_dir)