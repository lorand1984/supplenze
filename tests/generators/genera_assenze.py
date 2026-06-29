import random
import math
import os
import argparse
from datetime import date, timedelta
from openpyxl import load_workbook
from openpyxl import Workbook
from openpyxl.styles import Alignment

def leggi_orario(file_orario):
    """
    Legge un file Excel di orario e restituisce un dizionario:
    docente -> set di (giorno, ora) in cui ha lezione.
    Supporta intestazioni su più righe (cerca la riga con "Docente").
    """
    wb = load_workbook(file_orario, data_only=True)
    ws = wb.active

    # Trova la riga di intestazione che contiene "Docente" nella prima colonna
    header_row = None
    for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
        if row and row[0] == "Docente":
            header_row = idx
            break

    if header_row is None:
        raise ValueError("Intestazione 'Docente' non trovata nel file orario (prime 10 righe)")

    headers = [cell.value for cell in ws[header_row] if cell.value]

    # Mappa giorno-ora -> indice colonna (1-based)
    giorni_map = {"Lun": 1, "Mar": 2, "Mer": 3, "Gio": 4, "Ven": 5}
    col_index = {}
    for idx, h in enumerate(headers[1:], start=1):
        if isinstance(h, str) and '-' in h:
            parts = h.split('-')
            if len(parts) == 2:
                giorno_abbr, ora_str = parts[0].strip(), parts[1].strip()
                if giorno_abbr in giorni_map:
                    try:
                        ora = int(ora_str)
                        giorno = giorni_map[giorno_abbr]
                        col_index[(giorno, ora)] = idx
                    except ValueError:
                        continue

    if not col_index:
        raise ValueError("Nessuna colonna oraria valida trovata. Formato atteso: 'Lun-1', 'Mar-2', ...")

    # Leggi i docenti e le loro lezioni
    orario = {}
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        nome = row[0]
        if not nome:
            continue
        lezioni = set()
        for (g, o), col in col_index.items():
            if col >= len(row):
                continue
            val = row[col]
            # Gestione robusta: considera lezione solo se è una stringa non vuota e non è "D"
            if val is not None:
                val_str = str(val).strip()
                if val_str != "" and val_str != "D" and not val_str.isdigit():
                    lezioni.add((g, o))
        if lezioni:
            orario[nome] = lezioni

    return orario

def genera_assenze(
    output_file="assenze_docenti.xlsx",
    num_assenze=10,
    ore_giornaliere=6,
    start_date=None,
    end_date=None,
    decay=0.3,
    num_docenti=30,
    docenti_list=None,
    preavviso_mode="misto",
    solo_lezioni=False,
    orario_file=None
):
    """
    Genera un file Excel con assenze.

    Parametri:
        output_file (str): percorso del file Excel da creare.
        num_assenze (int): numero di assenze da generare.
        ore_giornaliere (int): numero di ore per giornata (6 o 7).
        start_date (date): data di inizio del range (default oggi).
        end_date (date): data di fine del range (opzionale).
        decay (float): fattore di decadimento esponenziale (default 0.3).
        num_docenti (int): numero di docenti da generare (se non viene fornita una lista).
        docenti_list (list): lista personalizzata di nomi docenti (opzionale).
        preavviso_mode (str): "insufficiente", "sufficiente", "misto".
        solo_lezioni (bool): se True, genera assenze solo in ore in cui il docente ha lezione.
        orario_file (str): percorso del file Excel dell'orario (richiesto se solo_lezioni=True).
    """
    if start_date is None:
        start_date = date.today()

    output_path = os.path.abspath(output_file)

    # Determina la lista dei docenti
    if docenti_list is not None:
        DOCENTI = docenti_list
    else:
        DOCENTI = [f"Docente_{i+1}" for i in range(num_docenti)]

    # Se modalità "solo lezioni", carica l'orario e costruisci la lista di tutte le lezioni
    if solo_lezioni:
        if not orario_file:
            raise ValueError("Per la modalità 'solo lezioni' è necessario specificare un file orario (--orario-file)")
        orario_docenti = leggi_orario(orario_file)
        if not orario_docenti:
            raise ValueError("Nessun docente trovato nell'orario. Verifica il formato del file.")

        # Costruisci una lista di tutte le lezioni disponibili (docente, giorno, ora)
        lezioni_disponibili = []
        for docente, lezioni in orario_docenti.items():
            for g, o in lezioni:
                lezioni_disponibili.append((docente, g, o))

        if not lezioni_disponibili:
            raise ValueError("Nessuna lezione trovata nell'orario.")

        # Filtra DOCENTI per quelli presenti nell'orario (utile per il caso random, ma qui non serve)
        DOCENTI = [d for d in DOCENTI if d in orario_docenti]
        if not DOCENTI:
            raise ValueError("Nessun docente della lista è presente nell'orario.")

    TIPO_ASSENZA = ["PERMESSO", "MALATTIA", "GITA", "ASSEMBLEA"]

    # Se end_date è specificato, genera le date uniformemente nel range
    if end_date is not None:
        giorni_range = (end_date - start_date).days + 1
        if giorni_range <= 0:
            raise ValueError("end_date deve essere successivo a start_date")
        date_list = [start_date + timedelta(days=i) for i in range(giorni_range)]
        weights = [1] * giorni_range
    else:
        giorni = 15
        date_list = [start_date + timedelta(days=i) for i in range(giorni)]
        weights = [math.exp(-decay * i) for i in range(giorni)]

    wb = Workbook()
    ws = wb.active
    ws.title = "Assenze"

    headers = ["Docente", "Data", "Ora_inizio", "Ora_fine", "Tipo_assenza", "Data_comunicazione"]
    ws.append(headers)

    # Numero di assenze generate finora
    generate_count = 0
    max_tentativi = num_assenze * 10  # per evitare loop infiniti

    while generate_count < num_assenze and max_tentativi > 0:
        max_tentativi -= 1

        # Seleziona docente, data, ora (e eventualmente durata)
        if solo_lezioni:
            # Scegli una lezione casuale dalla lista delle lezioni disponibili
            docente, giorno, ora = random.choice(lezioni_disponibili)
            # Decidi se l'assenza copre anche l'ora successiva (se il docente ha lezione anche lì)
            ora_fine = ora
            if (giorno, ora + 1) in orario_docenti.get(docente, set()) and random.random() < 0.5:
                ora_fine = ora + 1
        else:
            # Modalità random: scegli docente e orario casuale
            docente = random.choice(DOCENTI)
            # Scegli una data dal pool
            data = random.choices(date_list, weights=weights)[0]

            if random.random() < 0.1:
                ora = 1
                ora_fine = ore_giornaliere
            else:
                ora = random.randint(1, ore_giornaliere - 1)
                durata = random.randint(0, 1)
                ora_fine = min(ora + durata, ore_giornaliere)

        # Scegli data (per modalità random è già stata scelta, per solo_lezioni la scegliamo ora)
        if solo_lezioni:
            data = random.choices(date_list, weights=weights)[0]

        tipo = random.choice(TIPO_ASSENZA)

        # Gestione preavviso
        if preavviso_mode == "insufficiente":
            delta_com = random.choice([0, 0, 0, -1])
        elif preavviso_mode == "sufficiente":
            delta_com = random.randint(-4, -2)
        else:  # "misto"
            if random.random() < 0.4:
                delta_com = random.choice([0, 0, 0, -1])
            else:
                delta_com = random.randint(-4, -2)

        data_com = data + timedelta(days=delta_com)

        ws.append([docente, data, ora, ora_fine, tipo, data_com])
        generate_count += 1

    if generate_count < num_assenze:
        print(f"[Generatore] Attenzione: generate solo {generate_count} assenze su {num_assenze} richieste (mancanza di dati).")

    for col in [2, 6]:
        for cell in ws.iter_cols(min_col=col, max_col=col, min_row=2, max_row=num_assenze+1):
            for c in cell:
                c.number_format = 'YYYY-MM-DD'

    try:
        wb.save(output_path)
        print(f"[Generatore] File salvato correttamente in: {output_path}")
        print(f"[Generatore] Modalità preavviso: {preavviso_mode}")
        if solo_lezioni:
            print(f"[Generatore] Modalità: solo lezioni (usando orario da {orario_file})")
            print(f"[Generatore] Lezioni disponibili: {len(lezioni_disponibili)}")
        else:
            print(f"[Generatore] Modalità: random")
    except Exception as e:
        print(f"[Generatore] ERRORE durante il salvataggio: {e}")
        return None

    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera un file Excel di assenze.")
    parser.add_argument("--output", "-o", default="assenze_docenti.xlsx", help="Nome del file di output")
    parser.add_argument("--num-assenze", "-n", type=int, default=10, help="Numero di assenze da generare")
    parser.add_argument("--ore-giornaliere", "-g", type=int, default=6, help="Ore per giornata (6 o 7)")
    parser.add_argument("--start-date", "-s", help="Data di inizio (formato YYYY-MM-DD)")
    parser.add_argument("--end-date", "-e", help="Data di fine (formato YYYY-MM-DD), opzionale")
    parser.add_argument("--decay", "-d", type=float, default=0.3, help="Fattore di decadimento esponenziale")
    parser.add_argument("--num-docenti", "-nd", type=int, default=30, help="Numero di docenti")
    parser.add_argument("--docenti-list", "-dl", help="File con lista di docenti (uno per riga, opzionale)")
    parser.add_argument("--preavviso", "-p", choices=["insufficiente", "sufficiente", "misto"],
                        default="misto", help="Tipo di preavviso")
    parser.add_argument("--solo-lezioni", action="store_true", help="Genera assenze solo in ore in cui il docente ha lezione")
    parser.add_argument("--orario-file", "-of", help="File Excel dell'orario (richiesto con --solo-lezioni)")

    args = parser.parse_args()

    start = None
    if args.start_date:
        start = date.fromisoformat(args.start_date)

    end = None
    if args.end_date:
        end = date.fromisoformat(args.end_date)

    docenti = None
    if args.docenti_list:
        with open(args.docenti_list, 'r') as f:
            docenti = [line.strip() for line in f if line.strip()]

    genera_assenze(
        output_file=args.output,
        num_assenze=args.num_assenze,
        ore_giornaliere=args.ore_giornaliere,
        start_date=start,
        end_date=end,
        decay=args.decay,
        num_docenti=args.num_docenti,
        docenti_list=docenti,
        preavviso_mode=args.preavviso,
        solo_lezioni=args.solo_lezioni,
        orario_file=args.orario_file
    )