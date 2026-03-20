% fatti_7ore.lp – Giornata di 7 ore, classe in visita
lezione("Rossi", 1, 1, "1A").
lezione("Rossi", 1, 2, "1A").
lezione("Rossi", 1, 3, "1A").
lezione("Rossi", 1, 4, "1A").
lezione("Rossi", 1, 5, "1A").
lezione("Rossi", 1, 6, "1A").
lezione("Rossi", 1, 7, "1A").

assenza("Rossi", 1, 4, 4, true).  % ora 4 intermedia (in una sequenza di 7 ore)

% Visita che copre l'intera giornata di 7 ore
visita("1A", 1, 1, 7).   % la classe è in visita → nessuna supplenza