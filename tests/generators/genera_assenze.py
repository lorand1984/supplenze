import random
import math
import os
from datetime import date, timedelta
from openpyxl import Workbook
from openpyxl.styles import Alignment

def genera_assenze(
    output_file="assenze_docenti.xlsx",
    num_assenze=10,
    ore_giornaliere=6,
    start_date=None,
    decay=0.3
):
    """
    Genera un file Excel con assenze distribuite nei 15 giorni successivi a start_date,
    con probabilità decrescente (esponenziale). Di default start_date = oggi.
    """
    if start_date is None:
        start_date = date.today()

    # Converte in percorso assoluto se necessario
    output_path = os.path.abspath(output_file)

    DOCENTI = [f"Docente_{i+1}" for i in range(30)]
    TIPO_ASSENZA = ["PERMESSO", "MALATTIA", "GITA", "ASSEMBLEA"]

    giorni = 15
    pesi = [math.exp(-decay * i) for i in range(giorni)]
    totale = sum(pesi)

    wb = Workbook()
    ws = wb.active
    ws.title = "Assenze"

    headers = ["Docente", "Data", "Ora_inizio", "Ora_fine", "Tipo_assenza", "Data_comunicazione"]
    ws.append(headers)

    for _ in range(num_assenze):
        offset = random.choices(range(giorni), weights=pesi)[0]
        data = start_date + timedelta(days=offset)

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

    # Salva e verifica
    try:
        wb.save(output_path)
        print(f"[Generatore] File salvato correttamente in: {output_path}")
    except Exception as e:
        print(f"[Generatore] ERRORE durante il salvataggio: {e}")
        return None

    return output_path

if __name__ == "__main__":
    file_creato = genera_assenze()
    if file_creato:
        print(f"File creato: {file_creato}")