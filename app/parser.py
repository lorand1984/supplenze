import os
from datetime import datetime
from typing import List, Tuple, Optional
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from app.models import Docente, Assenza, VisitaIstruzione

# Mapping dei giorni della settimana
GIORNI_MAP = {
    'Lun': 1,
    'Mar': 2,
    'Mer': 3,
    'Gio': 4,
    'Ven': 5
}

def parse_orario(file_path: str) -> List[Docente]:
    """
    Legge il file Excel dell'orario docenti e restituisce una lista di oggetti Docente.
    Il file deve avere:
        - prima riga di intestazione con colonne: "Docente", "Lun-1", "Lun-2", ..., "Ven-7"
        - i valori possono essere: codice classe (es. "1A"), "D" (disponibile), oppure cella vuota (libero)
    Le colonne extra o con formato non valido vengono ignorate.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File non trovato: {file_path}")

    try:
        wb = load_workbook(file_path, data_only=True)
        ws = wb.active
    except InvalidFileException:
        raise ValueError("Il file non è un valido file Excel .xlsx")

    # Estrai intestazioni dalla prima riga
    headers = [cell.value for cell in ws[1] if cell.value]
    if not headers or headers[0] != "Docente":
        raise ValueError("La prima colonna deve essere 'Docente'")

    # Costruisci lista delle colonne orarie valide
    ore_colonne = []
    for h in headers[1:]:
        if not isinstance(h, str):
            continue
        h_strip = h.strip()
        if '-' not in h_strip:
            continue
        giorno_abbr, ora_str = h_strip.split('-', 1)
        giorno_abbr = giorno_abbr.strip()
        ora_str = ora_str.strip()
        if giorno_abbr not in GIORNI_MAP:
            continue
        try:
            ora = int(ora_str)
            if ora < 1 or ora > 7:
                continue
        except ValueError:
            continue
        ore_colonne.append((GIORNI_MAP[giorno_abbr], ora))

    if not ore_colonne:
        raise ValueError("Nessuna colonna oraria valida trovata nel file")

    docenti = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        nome_docente = row[0]
        if nome_docente is None:  # riga vuota
            continue
        if not isinstance(nome_docente, str):
            raise ValueError(f"Nome docente non valido alla riga {row[0]}: {nome_docente}")

        # Costruisci dizionario orario
        orario = {}
        for idx, valore in enumerate(row[1:]):
            if idx >= len(ore_colonne):
                break  # colonne extra ignorate
            giorno, ora = ore_colonne[idx]
            if valore is None:
                orario[(giorno, ora)] = None
            elif isinstance(valore, str) and valore.strip() == "":
                orario[(giorno, ora)] = None
            else:
                # Può essere "D" o un codice classe (es. "1A") – convertiamo in stringa
                orario[(giorno, ora)] = str(valore).strip()

        docente = Docente(nome=nome_docente, orario=orario)
        docenti.append(docente)

    return docenti


def parse_assenze(file_path: str) -> List[Assenza]:
    """
    Legge il file Excel delle assenze e restituisce una lista di oggetti Assenza.
    Il file deve avere le colonne:
        Docente, Data, Ora_inizio, Ora_fine, Tipo_assenza, Data_comunicazione
    La prima riga è intestazione.
    Supporta date in formato Excel (datetime) o stringhe ISO (YYYY-MM-DD).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File non trovato: {file_path}")

    try:
        wb = load_workbook(file_path, data_only=True)
        ws = wb.active
    except InvalidFileException:
        raise ValueError("Il file non è un valido file Excel .xlsx")

    # Verifica intestazioni
    headers = [cell.value for cell in ws[1] if cell.value]
    expected = ["Docente", "Data", "Ora_inizio", "Ora_fine", "Tipo_assenza", "Data_comunicazione"]
    if headers != expected:
        raise ValueError(f"Intestazioni non corrispondenti. Attese: {expected}, trovate: {headers}")

    assenze = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(cell is None for cell in row):
            continue

        # Verifica che la riga abbia almeno 6 elementi
        if len(row) < 6:
            raise ValueError(f"Riga {row_idx}: numero di colonne insufficiente (attese 6, trovate {len(row)})")

        docente_nome = row[0]
        data = row[1]
        ora_inizio = row[2]
        ora_fine = row[3]
        tipo = row[4]
        data_com = row[5]

        # Validazioni
        if not isinstance(docente_nome, str):
            raise ValueError(f"Riga {row_idx}: Nome docente deve essere una stringa, trovato {type(docente_nome)}")

        # Conversione date se sono stringhe (formato YYYY-MM-DD)
        if isinstance(data, str):
            try:
                data = datetime.strptime(data, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Riga {row_idx}: Data non valida (formato atteso YYYY-MM-DD), trovato '{data}'")
        elif not isinstance(data, datetime):
            raise ValueError(f"Riga {row_idx}: Data non valida (deve essere una data Excel o stringa YYYY-MM-DD), trovato {type(data)}")

        if isinstance(data_com, str):
            try:
                data_com = datetime.strptime(data_com, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Riga {row_idx}: Data comunicazione non valida (formato atteso YYYY-MM-DD), trovato '{data_com}'")
        elif not isinstance(data_com, datetime):
            raise ValueError(f"Riga {row_idx}: Data comunicazione non valida (deve essere una data Excel o stringa YYYY-MM-DD), trovato {type(data_com)}")

        # Gestione ore: accettiamo float interi
        def converti_ora(val, nome_campo, riga):
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            elif not isinstance(val, int):
                raise ValueError(f"Riga {riga}: {nome_campo} deve essere un numero intero, trovato {type(val)}")
            if val < 1 or val > 7:
                raise ValueError(f"Riga {riga}: {nome_campo} deve essere compreso tra 1 e 7")
            return val

        ora_inizio = converti_ora(ora_inizio, "Ora_inizio", row_idx)
        ora_fine = converti_ora(ora_fine, "Ora_fine", row_idx)

        if ora_fine < ora_inizio:
            raise ValueError(f"Riga {row_idx}: Ora_fine non può essere minore di Ora_inizio")

        if not isinstance(tipo, str):
            raise ValueError(f"Riga {row_idx}: Tipo_assenza deve essere una stringa, trovato {type(tipo)}")

        assenza = Assenza(
            docente_nome=docente_nome,
            data=data.date(),
            ora_inizio=ora_inizio,
            ora_fine=ora_fine,
            tipo_assenza=tipo,
            data_comunicazione=data_com.date()
        )
        assenze.append(assenza)

    return assenze


def parse_visite(file_path: str, ore_giornaliere: int = 6) -> List[VisitaIstruzione]:
    """
    Legge il file Excel delle visite di istruzione.
    Colonne attese: Classe, Data, Docenti_accompagnatori
    La visita copre l'intera giornata (dalla 1ª all'ultima ora).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File non trovato: {file_path}")

    try:
        wb = load_workbook(file_path, data_only=True)
        ws = wb.active
    except InvalidFileException:
        raise ValueError("Il file non è un valido file Excel .xlsx")

    headers = [cell.value for cell in ws[1] if cell.value]
    expected = ["Classe", "Data", "Docenti_accompagnatori"]
    if headers != expected:
        raise ValueError(f"Intestazioni non corrispondenti. Attese: {expected}, trovate: {headers}")

    visite = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(cell is None for cell in row):
            continue

        if len(row) < 3:
            raise ValueError(f"Riga {row_idx}: numero di colonne insufficiente (attese 3)")

        classe = row[0]
        data = row[1]
        docenti_raw = row[2]

        if not isinstance(classe, str):
            raise ValueError(f"Riga {row_idx}: Classe deve essere una stringa")
        if not isinstance(data, datetime):
            raise ValueError(f"Riga {row_idx}: Data non valida")
        if not isinstance(docenti_raw, str):
            raise ValueError(f"Riga {row_idx}: Docenti_accompagnatori deve essere una stringa separata da virgole")

        docenti_list = [d.strip() for d in docenti_raw.split(',') if d.strip()]

        visita = VisitaIstruzione(
            classe=classe,
            data=data.date(),
            ora_inizio=1,
            ora_fine=ore_giornaliere,
            docenti_accompagnatori=docenti_list
        )
        visite.append(visita)

    return visite


def parse_all(
    orario_path: str,
    assenze_path: str,
    visite_path: Optional[str] = None,
    ore_giornaliere: int = 6
) -> Tuple[List[Docente], List[Assenza], List[VisitaIstruzione]]:
    """
    Esegue il parsing di tutti i file.
    Restituisce una tupla (docenti, assenze, visite).
    """
    docenti = parse_orario(orario_path)
    assenze = parse_assenze(assenze_path)
    visite = []
    if visite_path:
        visite = parse_visite(visite_path, ore_giornaliere)
    return docenti, assenze, visite