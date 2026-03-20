import pytest
import clingo
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
REGOLE_ORE_SCOPERTE_PATH = os.path.join(BASE_DIR, 'app', 'asp', 'regole_ore_scoperte.lp')
REGOLE_ASSEGNAZIONE_PATH = os.path.join(BASE_DIR, 'app', 'asp', 'regole_assegnazione.lp')
FIXTURES_DIR = os.path.join(BASE_DIR, 'tests', 'fixtures')

def esegui_clingo(regole_path: str, fatti: str, tutti_modelli: bool = False, predicato: str = "richiede_supplenza"):
    """
    Esegue Clingo con le regole dal file e i fatti.
    Restituisce (soddisfacibile, lista_modelli), dove ogni modello è un set di tuple.
    Il predicato di output può essere "richiede_supplenza" (4 argomenti) o "assegna" (4 argomenti).
    """
    with open(regole_path, 'r', encoding='utf-8') as f:
        regole = f.read()
    program = regole + "\n" + fatti
    ctl = clingo.Control()
    ctl.add("base", [], program)
    ctl.ground([("base", [])])

    if tutti_modelli:
        ctl.configuration.solve.models = 0

    modelli = []
    def on_model(model):
        modello = set()
        for sym in model.symbols(shown=True):
            if sym.name == predicato and len(sym.arguments) == 4:
                # Gestione generica: i primi tre argomenti possono essere stringhe o interi
                args = []
                for i, arg in enumerate(sym.arguments):
                    if arg.type == clingo.SymbolType.Number:
                        args.append(arg.number)
                    else:  # String
                        args.append(str(arg).strip('"'))
                # L'ordine è: docente, giorno, ora, classe (per richiede_supplenza e assegna)
                modello.add(tuple(args))
        modelli.append(modello)

    ctl.solve(on_model=on_model)
    return len(modelli) > 0, modelli


# ----------------------------------------------------------------------
# Test US6 – Regole Ore Scoperte
# ----------------------------------------------------------------------

class TestOreScoperte:
    @pytest.mark.parametrize("fixture_file,attesi", [
        ("fatti_base.lp", {("Rossi", 1, 2, "1A"), ("Verdi", 1, 6, "3C")}),
        ("fatti_preavviso_sufficiente_prima.lp", set()),
        ("fatti_preavviso_sufficiente_ultima.lp", set()),
        ("fatti_preavviso_sufficiente_intermedia.lp", {("Rossi", 1, 2, "1A")}),
        ("fatti_preavviso_insufficiente_prima.lp", {("Rossi", 1, 1, "1A")}),
        ("fatti_visita.lp", set()),
        ("fatti_classi_multiple.lp", set()),
        ("fatti_orario_ridotto.lp", {("Rossi", 1, 4, "1A")}),
        ("fatti_7ore.lp", set()),  # aggiunto se presente
    ])
    def test_regole_ore_scoperte(self, fixture_file, attesi):
        with open(os.path.join(FIXTURES_DIR, fixture_file), 'r', encoding='utf-8') as f:
            fatti = f.read()
        soddisfacibile, modelli = esegui_clingo(REGOLE_ORE_SCOPERTE_PATH, fatti, tutti_modelli=False, predicato="richiede_supplenza")
        assert soddisfacibile, f"Il programma dovrebbe essere soddisfacibile per {fixture_file}"
        # Poiché le regole sono deterministiche, ci aspettiamo un solo modello
        assert len(modelli) == 1, f"Previsto 1 modello, trovati {len(modelli)}"
        assert modelli[0] == attesi, f"Per {fixture_file}: attesi {attesi}, ottenuti {modelli[0]}"


# ----------------------------------------------------------------------
# Test US7 – Regole di Assegnazione
# ----------------------------------------------------------------------

class TestAssegnazione:
    @pytest.mark.parametrize("fixture_file,atteso_soddisfacibile,attesi_modelli", [
        ("assegnazione_base.lp", True, 1),
        ("assegnazione_multipla.lp", True, 2),
        ("assegnazione_insoddisfacibile.lp", False, 0),
        ("assegnazione_con_disponibili_multipli.lp", True, 3),
    ])
    def test_regole_assegnazione(self, fixture_file, atteso_soddisfacibile, attesi_modelli):
        with open(os.path.join(FIXTURES_DIR, fixture_file), 'r', encoding='utf-8') as f:
            fatti = f.read()
        soddisfacibile, modelli = esegui_clingo(REGOLE_ASSEGNAZIONE_PATH, fatti, tutti_modelli=True, predicato="assegna")
        assert soddisfacibile == atteso_soddisfacibile
        if atteso_soddisfacibile:
            assert len(modelli) == attesi_modelli
            # Verifica aggiuntiva: nessun docente assegnato a due classi nella stessa ora
            for modello in modelli:
                per_ora = {}
                for (doc, giorno, ora, classe) in modello:
                    chiave = (doc, giorno, ora)
                    assert chiave not in per_ora, f"Docente {doc} assegnato due volte in {giorno},{ora}"
                    per_ora[chiave] = classe