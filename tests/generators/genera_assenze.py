import random
from datetime import date, timedelta
from openpyxl import Workbook
from openpyxl.styles import Alignment

def genera_assenze(output_file="assenze_giornaliere.xlsx", num_assenze=10, ore_giornaliere=6, giorno=date(2025, 3, 10)):
    """
    Genera un file Excel con 10 assenze (ridotte per aumentare soddisfacibilità).
    Alcune assenze coprono l'intera giornata (probabilità 10%).
    """
    DOCENTI = [f"Docente_{i+1}" for i in range(30)]
    TIPO_ASSENZA = ["PERMESSO", "MALATTIA", "GITA", "ASSEMBLEA"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Assenze"

    headers = ["Docente", "Data", "Ora_inizio", "Ora_fine", "Tipo_assenza", "Data_comunicazione"]
    ws.append(headers)

    for _ in range(num_assenze):
        docente = random.choice(DOCENTI)

        if random.random() < 0.1:
            ora_inizio = 1
            ora_fine = ore_giornaliere
        else:
            ora_inizio = random.randint(1, ore_giornaliere - 1)
            durata = random.randint(0, 1)
            ora_fine = min(ora_inizio + durata, ore_giornaliere)

        tipo = random.choice(TIPO_ASSENZA)
        delta_com = random.randint(-3, 0)
        data_com = giorno + timedelta(days=delta_com)

        ws.append([docente, giorno, ora_inizio, ora_fine, tipo, data_com])

    for col in [2, 6]:
        for cell in ws.iter_cols(min_col=col, max_col=col, min_row=2, max_row=num_assenze+1):
            for c in cell:
                c.number_format = 'YYYY-MM-DD'

    wb.save(output_file)
    print(f"[Generatore] File '{output_file}' creato con {num_assenze} assenze (data unica {giorno.isoformat()}).")
    return output_file

if __name__ == "__main__":
    genera_assenze()