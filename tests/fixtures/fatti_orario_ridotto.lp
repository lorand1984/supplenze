% fatti_orario_ridotto.lp
% Classe con orario ridotto (solo ore 3-5). Assenza ora 4 (intermedia) → supplenza

lezione("Rossi", 1, 3, "1A").
lezione("Rossi", 1, 4, "1A").
lezione("Rossi", 1, 5, "1A").
assenza("Rossi", 1, 4, 4, true).