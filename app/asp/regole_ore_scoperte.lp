% ============================================================
% US6 – Regole ASP per Ore Scoperte
% ============================================================
% Input: fatti generati da US5:
%   - lezione(Docente, Giorno, Ora, Classe)
%   - disponibile(Docente, Giorno, Ora)
%   - assenza(Docente, Giorno, Inizio, Fine, Preavviso)  (Preavviso: true/false)
%   - visita(Classe, Giorno, Inizio, Fine)
%
% Output: richiede_supplenza(DocenteAssente, Giorno, Ora, Classe)

% ----------------------------------------------------------------------
% 1. Ore di lezione effettive di una classe (escludendo le visite)
% ----------------------------------------------------------------------
ore_classe(G, Classe, Ora) :- lezione(_, G, Ora, Classe).

% Se c'è una visita per quella classe in quel giorno, tutte le ore sono saltate.
visita_intera_giornata(Classe, G) :- visita(Classe, G, 1, _).

ore_effettive(G, Classe, Ora) :- ore_classe(G, Classe, Ora), not visita_intera_giornata(Classe, G).

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
%    (richiedono che l'ora sia effettiva, cioè non cancellata da visita)
% ----------------------------------------------------------------------
% Caso 1: preavviso insufficiente -> tutte le ore effettive coperte richiedono supplenza
richiede_supplenza(Docente, G, Ora, Classe) :-
    ora_assente(Docente, G, Ora, Classe),
    ore_effettive(G, Classe, Ora),
    assenza(Docente, G, _, _, false).

% Caso 2: preavviso sufficiente -> solo le ore effettive che non sono né prima né ultima
richiede_supplenza(Docente, G, Ora, Classe) :-
    ora_assente(Docente, G, Ora, Classe),
    ore_effettive(G, Classe, Ora),
    assenza(Docente, G, _, _, true),
    not prima_ora(G, Classe, Ora),
    not ultima_ora(G, Classe, Ora).

% ----------------------------------------------------------------------
% 5. Mostra solo i fatti di output
% ----------------------------------------------------------------------
#show richiede_supplenza/4.