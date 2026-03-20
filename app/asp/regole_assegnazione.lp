% ============================================================
% US7 – Regole di Assegnazione delle Supplenze
% ============================================================
% Input: 
%   - richiede_supplenza(_, Giorno, Ora, Classe)   (dalla US6)
%   - disponibile(Docente, Giorno, Ora)
%
% Output:
%   - assegna(Docente, Giorno, Ora, Classe)

% Per ogni ora che richiede supplenza, scegli esattamente un docente disponibile.
{ assegna(D, G, O, C) : disponibile(D, G, O) } = 1 :-
    richiede_supplenza(_, G, O, C).

% Vincolo: un docente non può essere assegnato a due classi diverse nella stessa ora.
:- assegna(D, G, O, C1), assegna(D, G, O, C2), C1 != C2.

% (Opzionale) Mostra solo il predicato assegna/4.
#show assegna/4.