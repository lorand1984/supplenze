from openpyxl import Workbook
import os


def genera_orario_con_compresenze(output_file="./orario_con_compresenze.xlsx"):
    """
    Genera un orario senza colonna Tipo, con:
    - docenti di materia nel primo blocco
    - riga vuota come separatore
    - ITP e sostegno nel secondo blocco (prefissi ITP_ / Sost_)
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Orario Docenti"

    giorni = ["Lun", "Mar", "Mer", "Gio", "Ven"]
    ore = range(1, 7)
    headers = ["Docente"] + [f"{g}-{o}" for g in giorni for o in ore]
    ws.append(headers)

    def riga(nome, celle):
        return [nome] + celle

    # --- Blocco materia ---
    ws.append(riga("Rossi", [
        "1A", "1A", "D", None, None, None,
        "1B", "1B", None, None, None, None,
        "1A", "1A", None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
    ]))
    ws.append(riga("Bianchi", [
        "2B", "2B", "D", None, None, None,
        "2B", None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
    ]))
    ws.append(riga("Neri", [
        "3A", "D", None, None, None, None,
        "1A", None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
    ]))

    # --- Riga vuota separatore ---
    ws.append([])

    # --- Blocco ITP / sostegno ---
    ws.append(riga("ITP_Mario", [
        "1A:Rossi", "1A:Rossi", "D", None, None, None,
        "2B:Bianchi", "D", None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
    ]))
    ws.append(riga("ITP_Luigi", [
        None, None, None, None, None, None,
        "1A:Neri", "D", None, None, None, None,
        "D", None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
    ]))
    ws.append(riga("Sost_Anna", [
        "1A:Rossi", "D", None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
    ]))
    ws.append(riga("Sost_Paolo", [
        "2B:Bianchi", None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
        None, None, None, None, None, None,
    ]))

    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    wb.save(output_file)
    print(f"File creato: {output_file}")
    return output_file


if __name__ == "__main__":
    genera_orario_con_compresenze()