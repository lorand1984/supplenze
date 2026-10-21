% ============================================================
% US6 – Regole ASP per Ore Scoperte
% ============================================================
% Input: fatti generati da US5:
%   - lezione(Docente, Giorno, Ora, Classe)
%   - disponibile(Docente, Giorno, Ora)
%   - assenza(Docente, Giorno, Inizio, Fine, Preavviso)
%   - visita(Classe, Giorno, Inizio, Fine)
%   - compresenza(ITP, DocenteMateria, Giorno, Ora, Classe)   (US18)
%
% Output:
%   - richiede_supplenza(DocenteAssente, Giorno, Ora, Classe)
%   - supplenza_automatica(ITP, Giorno, Ora, Classe, DocenteMateria)

% ----------------------------------------------------------------------
% 1. Ore di lezione effettive di una classe (escludendo le visite)
% ----------------------------------------------------------------------
ore_classe(G, Classe, Ora) :- lezione(_, G, Ora, Classe).

% Se c'è una visita per quella classe in quel giorno, tutte le ore sono saltate.
visita_intera_giornata(Classe, G) :- visita(Classe, G, 1, _).

ore_effettive(G, Classe, Ora) :-
    ore_classe(G, Classe, Ora),
    not visita_intera_giornata(Classe, G).

% ----------------------------------------------------------------------
% 2. Prima e ultima ora per classe/giorno (usando aggregati)
% ----------------------------------------------------------------------
prima_ora(G, Classe, Ora) :-
    ore_effettive(G, Classe, Ora),
    Ora = #min{ O : ore_effettive(G, Classe, O) }.

ultima_ora(G, Classe, Ora) :-
    ore_effettive(G, Classe, Ora),
    Ora = #max{ O : ore_effettive(G, Classe, O) }.

% ----------------------------------------------------------------------
% 3. Ore coperte da assenza
% ----------------------------------------------------------------------
ora_assente(Docente, G, Ora, Classe) :-
    assenza(Docente, G, Inizio, Fine, _),
    lezione(Docente, G, Ora, Classe),
    Ora >= Inizio, Ora <= Fine.

% ----------------------------------------------------------------------
% 4. Determinazione ore che richiedono supplenza
% ----------------------------------------------------------------------
% Caso 1: preavviso insufficiente -> tutte le ore effettive coperte richiedono supplenza
% (escluse quelle già coperte da supplenza automatica)
richiede_supplenza(Docente, G, Ora, Classe) :-
    ora_assente(Docente, G, Ora, Classe),
    ore_effettive(G, Classe, Ora),
    assenza(Docente, G, _, _, false),
    not supplenza_automatica(_, G, Ora, Classe, _).

% Caso 2: preavviso sufficiente -> solo le ore effettive che non sono né prima né ultima
% (escluse quelle già coperte da supplenza automatica)
richiede_supplenza(Docente, G, Ora, Classe) :-
    ora_assente(Docente, G, Ora, Classe),
    ore_effettive(G, Classe, Ora),
    assenza(Docente, G, _, _, true),
    not prima_ora(G, Classe, Ora),
    not ultima_ora(G, Classe, Ora),
    not supplenza_automatica(_, G, Ora, Classe, _).

% ----------------------------------------------------------------------
% 5. US18 – Supplenza automatica da compresenza
% ----------------------------------------------------------------------
% Se il docente di materia è assente e c'è una compresenza con ITP/sostegno,
% l'ITP/sostegno subentra automaticamente, anche su prima/ultima ora.
% La priorità ITP > sostegno è già gestita a monte nella generazione dei fatti
% (viene generato un solo fatto compresenza per ogni coppia ora/classe/docente_materia).
supplenza_automatica(ITP, G, Ora, Classe, DocenteMateria) :-
    assenza(DocenteMateria, G, Inizio, Fine, _),
    Ora >= Inizio, Ora <= Fine,
    compresenza(ITP, DocenteMateria, G, Ora, Classe).

% ----------------------------------------------------------------------
% 6. Output
% ----------------------------------------------------------------------
#show richiede_supplenza/4.
#show supplenza_automatica/5.