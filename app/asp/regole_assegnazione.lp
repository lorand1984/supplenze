% ============================================================
% US7 – Regole di Assegnazione delle Supplenze
% ============================================================
% Input:
%   - richiede_supplenza(DocenteAssente, Giorno, Ora, Classe)
%   - supplenza_automatica(ITP, Giorno, Ora, Classe, DocenteMateria)  (US18)
%   - disponibile(Docente, Giorno, Ora)
%
% Output:
%   - assegna(Docente, Giorno, Ora, Classe)

% ----------------------------------------------------------------------
% 1. Scelta del supplente per le ore che richiedono supplenza normale
% ----------------------------------------------------------------------
% Per ogni ora che richiede supplenza (e che non è già coperta da una
% supplenza automatica), scegli esattamente un docente disponibile.
{ assegna(D, G, O, C) : disponibile(D, G, O) } = 1 :-
    richiede_supplenza(_, G, O, C).

% ----------------------------------------------------------------------
% 2. Vincolo di unicità: un docente non può essere in due classi nella stessa ora
% ----------------------------------------------------------------------
:- assegna(D, G, O, C1), assegna(D, G, O, C2), C1 != C2.

% ----------------------------------------------------------------------
% 3. US18 – Assegnazione automatica da compresenza
% ----------------------------------------------------------------------
% L'ITP/sostegno in compresenza assume automaticamente la supplenza
% quando il docente di materia è assente.
% La priorità ITP > sostegno è già garantita a monte (un solo fatto compresenza).
assegna(ITP, G, O, C) :-
    supplenza_automatica(ITP, G, O, C, _).

% ----------------------------------------------------------------------
% 4. Output
% ----------------------------------------------------------------------
#show assegna/4.