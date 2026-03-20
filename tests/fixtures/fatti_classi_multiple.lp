% fatti_classi_multiple.lp
% Docente con due classi: 1A ore 1-2, 2B ore 3-4.
% Assenza ore 2-3 → ora 2 (1A) è ultima, ora 3 (2B) è prima → nessuna supplenza

lezione("Rossi", 1, 1, "1A").
lezione("Rossi", 1, 2, "1A").
lezione("Rossi", 1, 3, "2B").
lezione("Rossi", 1, 4, "2B").
assenza("Rossi", 1, 2, 3, true).