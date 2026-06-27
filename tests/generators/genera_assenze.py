import random
import math
import os
import argparse
from datetime import date, timedelta
from openpyxl import Workbook
from openpyxl.styles import Alignment

def genera_assenze(
    output_file="assenze_docenti.xlsx",
    num_assenze=10,
    ore_giornaliere=6,
    start_date=None,
    end_date=None,
    decay=0.3,
    num_docenti=30,
    docenti_list=None
):
    """
    Genera un file Excel con assenze.

    Se start_date e end_date sono specificati, le assenze vengono distribuite
    uniformemente in quel range di date. Se solo start_date è specificato,
    vengono distribuite nei 15 giorni successivi con probabilità decrescente.
    Se start_date è None, si usa la data odierna.

    Parametri:
        output_file (str): percorso del file Excel da creare.
        num_assenze (int): numero di assenze da generare.
        ore_giornaliere (int): numero di ore per giornata (6 o 7).
        start_date (date): data di inizio del range (default oggi).
        end_date (date): data di fine del range (opzionale).
        decay (float): fattore di decadimento esponenziale (default 0.3).
        num_docenti (int): numero di docenti da generare (se non viene fornita una lista).
        docenti_list (list): lista personalizzata di nomi docenti (opzionale).
    """
    if start_date is None:
        start_date = date.today()

    output_path = os.path.abspath(output_file)

    # Determina la lista dei docenti
    if docenti_list is not None:
        DOCENTI = docenti_list
    else:
        DOCENTI = [f"Docente_{i+1}" for i in range(num_docenti)]

    TIPO_ASSENZA = ["PERMESSO", "MALATTIA", "GITA", "ASSEMBLEA"]

    # Se end_date è specificato, genera le date uniformemente nel range
    if end_date is not None:
        giorni_range = (end_date - start_date).days + 1
        if giorni_range <= 0:
            raise ValueError("end_date deve essere successivo a start_date")
        date_list = [start_date + timedelta(days=i) for i in range(giorni_range)]
        # Assegna date con probabilità uniforme
        weights = [1] * giorni_range
    else:
        # Distribuzione esponenziale sui prossimi 15 giorni
        giorni = 15
        date_list = [start_date + timedelta(days=i) for i in range(giorni)]
        weights = [math.exp(-decay * i) for i in range(giorni)]

    wb = Workbook()
    ws = wb.active
    ws.title = "Assenze"

    headers = ["Docente", "Data", "Ora_inizio", "Ora_fine", "Tipo_assenza", "Data_comunicazione"]
    ws.append(headers)

    for _ in range(num_assenze):
        # Scegli una data dal pool
        data = random.choices(date_list, weights=weights)[0]

        if random.random() < 0.1:
            ora_inizio = 1
            ora_fine = ore_giornaliere
        else:
            ora_inizio = random.randint(1, ore_giornaliere - 1)
            durata = random.randint(0, 1)
            ora_fine = min(ora_inizio + durata, ore_giornaliere)

        docente = random.choice(DOCENTI)
        tipo = random.choice(TIPO_ASSENZA)
        delta_com = random.randint(-3, 0)
        data_com = data + timedelta(days=delta_com)

        ws.append([docente, data, ora_inizio, ora_fine, tipo, data_com])

    for col in [2, 6]:
        for cell in ws.iter_cols(min_col=col, max_col=col, min_row=2, max_row=num_assenze+1):
            for c in cell:
                c.number_format = 'YYYY-MM-DD'

    try:
        wb.save(output_path)
        print(f"[Generatore] File salvato correttamente in: {output_path}")
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
    parser.add_argument("--num-docenti", "-nd", type=int, default=30, help="Numero di docenti (se non si fornisce una lista)")
    parser.add_argument("--docenti-list", "-dl", help="File con lista di docenti (uno per riga, opzionale)")

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
        docenti_list=docenti
    )