import random
from openpyxl import Workbook
from openpyxl.styles import Alignment

def genera_orario(output_file="orario_30_docenti.xlsx"):
    """
    Genera un file Excel con l'orario di 30 docenti.
    Ogni docente ha un totale ore (lezioni + D) compreso tra 18 e 24.
    """
    NUM_DOCENTI = 30
    CLASSI = [f"{lettera}{numero}" for lettera in ["1", "2", "3", "4", "5"] for numero in ["A", "B", "C"]]
    GIORNI = ["Lun", "Mar", "Mer", "Gio", "Ven"]
    ORE_MAX = 7
    ORE_NORM = 6
    GIORNI_LUNGHI = 2

    # 1. Orario delle classi
    orario_classi = {}
    for classe in CLASSI:
        giorni_lunghi = random.sample(range(5), GIORNI_LUNGHI)
        ore_per_giorno = [ORE_MAX if g in giorni_lunghi else ORE_NORM for g in range(5)]
        orario_classi[classe] = ore_per_giorno

    totale_ore_lezioni = sum(sum(ore) for ore in orario_classi.values())
    print(f"[Generatore] Totale ore lezione da coprire: {totale_ore_lezioni}")

    # 2. Target di ore totali per docente (18-24)
    target_totali = [random.randint(18, 24) for _ in range(NUM_DOCENTI)]

    # 3. Distribuzione delle ore di lezione
    ore_lezioni_docenti = [0] * NUM_DOCENTI
    somma = 0
    for i in range(NUM_DOCENTI):
        ore_lezioni_docenti[i] = random.randint(8, 15)
        somma += ore_lezioni_docenti[i]

    fattore = totale_ore_lezioni / somma
    for i in range(NUM_DOCENTI):
        ore_lezioni_docenti[i] = int(round(ore_lezioni_docenti[i] * fattore))
        if ore_lezioni_docenti[i] < 6:
            ore_lezioni_docenti[i] = 6
        elif ore_lezioni_docenti[i] > 20:
            ore_lezioni_docenti[i] = 20

    differenza = totale_ore_lezioni - sum(ore_lezioni_docenti)
    while differenza != 0:
        for i in range(NUM_DOCENTI):
            if differenza > 0:
                if ore_lezioni_docenti[i] < 20:
                    ore_lezioni_docenti[i] += 1
                    differenza -= 1
                    if differenza == 0: break
            else:
                if ore_lezioni_docenti[i] > 6:
                    ore_lezioni_docenti[i] -= 1
                    differenza += 1
                    if differenza == 0: break

    print(f"[Generatore] Ore di lezione per docente: {ore_lezioni_docenti}")
    print(f"[Generatore] Somma ore lezione: {sum(ore_lezioni_docenti)} (target {totale_ore_lezioni})")

    # 4. Assegnazione delle lezioni
    richieste = []
    for classe in CLASSI:
        for giorno, ore_giorno in enumerate(orario_classi[classe]):
            for ora in range(1, ore_giorno + 1):
                richieste.append((classe, giorno, ora))
    random.shuffle(richieste)

    ore_assegnate_docenti = [0] * NUM_DOCENTI
    occupazione_docenti = {d: set() for d in range(NUM_DOCENTI)}
    assegnazioni = {}

    for (classe, giorno, ora) in richieste:
        candidati = [
            d for d in range(NUM_DOCENTI)
            if ore_assegnate_docenti[d] < ore_lezioni_docenti[d]
            and (giorno, ora) not in occupazione_docenti[d]
        ]
        if not candidati:
            candidati = [
                d for d in range(NUM_DOCENTI)
                if (giorno, ora) not in occupazione_docenti[d]
            ]
            if not candidati:
                raise RuntimeError(f"Impossibile assegnare {classe} giorno {giorno} ora {ora}")
        docente = random.choice(candidati)
        assegnazioni[(classe, giorno, ora)] = docente
        ore_assegnate_docenti[docente] += 1
        occupazione_docenti[docente].add((giorno, ora))

    print(f"[Generatore] Assegnate {len(assegnazioni)} richieste su {len(richieste)}")

    # 5. Costruzione orario docenti
    orario_docenti = {d: {} for d in range(NUM_DOCENTI)}
    for (classe, giorno, ora), docente in assegnazioni.items():
        orario_docenti[docente][(giorno, ora)] = classe

    # 6. Aggiunta di "D" per raggiungere il target
    for d in range(NUM_DOCENTI):
        gia_assegnate = ore_assegnate_docenti[d]
        target = target_totali[d]
        if target < gia_assegnate:
            target = gia_assegnate
        da_aggiungere = target - gia_assegnate
        if da_aggiungere <= 0:
            continue
        ore_libere = []
        for giorno in range(5):
            for ora in range(1, ORE_MAX + 1):
                if (giorno, ora) not in orario_docenti[d]:
                    ore_libere.append((giorno, ora))
        random.shuffle(ore_libere)
        for (giorno, ora) in ore_libere[:da_aggiungere]:
            orario_docenti[d][(giorno, ora)] = "D"

    # 7. Creazione file Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Orario Docenti"

    headers = ["Docente"] + [f"{GIORNI[g]}-{o}" for g in range(5) for o in range(1, ORE_MAX + 1)]
    ws.append(headers)

    for d in range(NUM_DOCENTI):
        nome = f"Docente_{d+1}"
        riga = [nome]
        for g in range(5):
            for o in range(1, ORE_MAX + 1):
                valore = orario_docenti[d].get((g, o), None)
                riga.append(valore)
        ws.append(riga)

    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(horizontal='center')

    wb.save(output_file)
    print(f"[Generatore] File '{output_file}' creato con successo.")
    return output_file

if __name__ == "__main__":
    genera_orario()