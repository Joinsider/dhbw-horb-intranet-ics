# ADR 0005: Terminarten und Filter

- Status: akzeptiert
- Datum: 2026-09-30

## Kontext

Neben Vorlesungen enthält der Stundenplan Feiertage, Klausuren und mündliche Prüfungen. Geprüft wurden KW 40, KW 42 und KW 51 2026 für `HOR-TINF2024`.

## Beobachtungen

Die Art eines Blocks ist im HTML nur an der Hintergrundfarbe erkennbar:

| Farbe | Art | Beispiel |
|---|---|---|
| `#a3ddff` | Vorlesung | „Recht“, 09:00–12:45 |
| `#f79f81` | Klausur | „Recht“, 08:30–09:30 (KW 51) |
| `#cc00cc` | Mündliche Prüfung | „Mündl. Prüfung T2000“, 09:00–17:00 (KW 42) |
| `#df0101` | Feiertag | „Feiertag“, 07:00–19:00 |

- Eine Klausur trägt denselben Titel wie die Vorlesung. Ohne die Farbe ist sie nicht von einer kurzen Vorlesung zu unterscheiden.
- Mehrere Räume stehen mit `;` getrennt in einem Feld (`HOR-135;HOR-136`), mehrere Dozenten mit `; `.

## Entscheidung

- Feiertage werden nicht gespeichert und nicht ausgeliefert. Erkannt werden sie am Titel „Feiertag“ oder an der Farbe.
- Klausuren und mündliche Prüfungen werden als Termine ausgeliefert.
- Klausuren bekommen im Kalender den Titel `Klausur: <Titel>`, weil sie sonst wie eine Vorlesung aussehen. Mündliche Prüfungen behalten ihren Titel.
- Jeder Termin bekommt eine ICS-Kategorie (`Vorlesung`, `Klausur`, `Mündliche Prüfung`).
- Blöcke mit unbekannter Farbe werden als normaler Termin ohne Kategorie ausgeliefert, nicht verworfen.
- Parallele Blöcke bleiben getrennte Termine.
- Mehrere Räume werden als `HOR-135, HOR-136` in `LOCATION` ausgegeben, der Dozent steht in `DESCRIPTION`.

## Konsequenzen

- Ändert die DHBW die Farben, erscheinen Klausuren ohne Präfix und Feiertage nur noch über den Titel gefiltert. Die Zuordnung steht in `KIND_BY_COLOR` in `src/dhbw_ics/parser.py`.
- Weitere Farben (andere Kurse, andere Terminarten) sind nicht untersucht.
