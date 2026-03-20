% fatti_base.lp – Dati di base (come nel vecchio fatti_test.lp)

lezione("Rossi", 1, 1, "1A").
lezione("Rossi", 1, 2, "1A").
lezione("Rossi", 1, 3, "1A").
lezione("Bianchi", 1, 4, "2B").
lezione("Bianchi", 1, 5, "2B").
lezione("Verdi", 1, 6, "3C").

assenza("Rossi", 1, 2, 2, true).
assenza("Bianchi", 1, 4, 4, true).
assenza("Verdi", 1, 6, 6, false).

visita("2B", 1, 1, 6).