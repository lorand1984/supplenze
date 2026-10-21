import pytest
import clingo
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
REGOLE_ORE_SCOPERTE_PATH = os.path.join(BASE_DIR, 'app', 'asp', 'regole_ore_scoperte.lp')
REGOLE_ASSEGNAZIONE_PATH = os.path.join(BASE_DIR, 'app', 'asp', 'regole_assegnazione.lp')
FIXTURES_DIR = os.path.join(BASE_DIR, 'tests', 'fixtures')


def esegui_clingo(regole_path, fatti, tutti_modelli=False, predicato="richiede_supplenza"):
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
                args = []
                for arg in sym.arguments:
                    if arg.type == clingo.SymbolType.Number:
                        args.append(arg.number)
                    else:
                        args.append(str(arg).strip('"'))
                modello.add(tuple(args))
        modelli.append(modello)

    ctl.solve(on_model=on_model)
    return len(modelli) > 0, modelli


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
    ])
    def test_regole_ore_scoperte(self, fixture_file, attesi):
        with open(os.path.join(FIXTURES_DIR, fixture_file), 'r', encoding='utf-8') as f:
            fatti = f.read()
        soddisfacibile, modelli = esegui_clingo(
            REGOLE_ORE_SCOPERTE_PATH, fatti, tutti_modelli=False, predicato="richiede_supplenza"
        )
        assert soddisfacibile
        assert len(modelli) == 1
        assert modelli[0] == attesi


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
        soddisfacibile, modelli = esegui_clingo(
            REGOLE_ASSEGNAZIONE_PATH, fatti, tutti_modelli=True, predicato="assegna"
        )
        assert soddisfacibile == atteso_soddisfacibile
        if atteso_soddisfacibile:
            assert len(modelli) == attesi_modelli


class TestSupplenzaAutomatica:
    """Test US18: supplenza automatica da compresenza."""

    def test_supplenza_automatica_generata(self):
        fatti = '''
        lezione("Rossi", 1, 1, "1A").
        compresenza("ITP1", "Rossi", 1, 1, "1A").
        assenza("Rossi", 1, 1, 1, false).
        '''
        soddisfacibile, modelli = esegui_clingo(
            REGOLE_ORE_SCOPERTE_PATH, fatti, tutti_modelli=False, predicato="supplenza_automatica"
        )
        assert soddisfacibile
        assert len(modelli) == 1
        # La tupla contiene (ITP, Giorno, Ora, Classe) perché esegui_clingo legge solo 4 argomenti
        # supplenza_automatica ha 5 argomenti, quindi non viene catturata.
        # Usiamo un test dedicato sotto.
        assert modelli[0] == set()

    def test_supplenza_automatica_con_5_argomenti(self):
        with open(REGOLE_ORE_SCOPERTE_PATH, 'r', encoding='utf-8') as f:
            regole = f.read()
        fatti = '''
        lezione("Rossi", 1, 1, "1A").
        compresenza("ITP1", "Rossi", 1, 1, "1A").
        assenza("Rossi", 1, 1, 1, false).
        '''
        ctl = clingo.Control()
        ctl.add("base", [], regole + "\n" + fatti)
        ctl.ground([("base", [])])
        risultati = []

        def on_model(model):
            for sym in model.symbols(shown=True):
                if sym.name == "supplenza_automatica" and len(sym.arguments) == 5:
                    risultati.append((
                        str(sym.arguments[0]).strip('"'),
                        sym.arguments[1].number,
                        sym.arguments[2].number,
                        str(sym.arguments[3]).strip('"'),
                        str(sym.arguments[4]).strip('"'),
                    ))

        ctl.solve(on_model=on_model)
        assert ("ITP1", 1, 1, "1A", "Rossi") in risultati

    def test_nessuna_supplenza_automatica_senza_compresenza(self):
        with open(REGOLE_ORE_SCOPERTE_PATH, 'r', encoding='utf-8') as f:
            regole = f.read()
        fatti = '''
        lezione("Rossi", 1, 1, "1A").
        assenza("Rossi", 1, 1, 1, false).
        '''
        ctl = clingo.Control()
        ctl.add("base", [], regole + "\n" + fatti)
        ctl.ground([("base", [])])
        risultati = []

        def on_model(model):
            for sym in model.symbols(shown=True):
                if sym.name == "supplenza_automatica":
                    risultati.append(sym)

        ctl.solve(on_model=on_model)
        assert len(risultati) == 0

    def test_richiede_supplenza_esclude_supplenza_automatica(self):
        with open(REGOLE_ORE_SCOPERTE_PATH, 'r', encoding='utf-8') as f:
            regole = f.read()
        fatti = '''
        lezione("Rossi", 1, 1, "1A").
        compresenza("ITP1", "Rossi", 1, 1, "1A").
        assenza("Rossi", 1, 1, 1, false).
        '''
        ctl = clingo.Control()
        ctl.add("base", [], regole + "\n" + fatti)
        ctl.ground([("base", [])])
        richieste = []

        def on_model(model):
            for sym in model.symbols(shown=True):
                if sym.name == "richiede_supplenza" and len(sym.arguments) == 4:
                    richieste.append(sym)

        ctl.solve(on_model=on_model)
        assert len(richieste) == 0