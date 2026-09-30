# ADR 0006: Abruf, Cache und Login-Schutz

- Status: akzeptiert
- Datum: 2026-09-30

## Kontext

ADR 0003 legt die Anforderungen fest. Dieser ADR hält fest, wie sie umgesetzt sind.

## Entscheidung

### Abruf

- Es gibt keinen Hintergrund-Job. Abgerufen wird nur, wenn ein Client `/calendar.ics` aufruft.
- Zielwochen sind die aktuelle Woche plus `WEEKS_AHEAD` Wochen. Pro Woche ein GET, nacheinander, mit `REQUEST_DELAY_SECONDS` (Standard 2 s) Pause.
- Eine Woche wird nur gespeichert, wenn die Seite den erwarteten Kurs und die erwartete Woche zeigt. Dann ersetzt sie in einer Transaktion alle bisherigen Termine dieser Woche.
- Wochen vor der aktuellen Woche werden nie wieder abgerufen und bleiben unverändert in der Datenbank.
- Ausgeliefert werden alle gespeicherten Termine bis zum Ende der letzten Zielwoche.

### Cache

- Pro Woche steht der Abrufzeitpunkt in SQLite. Eine Woche gilt 1 Stunde als frisch (`CACHE_TTL_SECONDS`). Der Cache übersteht Neustarts.
- `?cache=false` markiert alle Zielwochen als veraltet.
- Mindestpause: Zwischen zwei Intranet-Abrufen liegen mindestens 5 Minuten (`MIN_FETCH_INTERVAL_SECONDS`), auch bei `cache=false` und auch nach einem fehlgeschlagenen Abruf. Innerhalb der Pause wird der gespeicherte Stand geliefert.
- Gleichzeitige Anfragen lösen nur einen Abruf aus (Lock).

### Login

- Die Session lebt nur im Arbeitsspeicher. Eingeloggt wird erst, wenn eine Stundenplan-Anfrage keine Stundenplan-Tabelle liefert (ohne Session leitet das Intranet um).
- Pro Abruf höchstens 1 Login-Versuch plus 2 Wiederholungen. Danach sperrt der Container weitere Intranet-Abrufe für 6 Stunden. Ein Neustart hebt die Sperre auf.
- Die dynamischen Formularfelder werden vor jedem Versuch frisch gelesen (siehe ADR 0002).

### Fehlerfall

- Schlägt ein Abruf fehl, antwortet der Endpunkt trotzdem mit `200` und dem gespeicherten Stand, mit Header `X-Refresh-Failed: true`. Der Fehler steht im Log.

### ICS

- Zeiten werden aus Europe/Berlin nach UTC umgerechnet ausgegeben, dadurch ist kein `VTIMEZONE`-Block nötig.
- Die `UID` ist ein Hash aus Kurs, Start, Ende, Titel, Dozent, Raum und Art. Ändert sich ein Termin im Intranet, verschwindet der alte und ein neuer erscheint.

### API-Key

- Vergleich in konstanter Zeit, bei falschem oder fehlendem Key `401`.
- Das Zugriffslog von uvicorn ist im Container abgeschaltet, damit der Key aus der URL nicht im Log landet.

## Konsequenzen

- Der erste Aufruf nach einer Stunde Pause dauert mit 4 Wochen Vorschau etwa 10 Sekunden (5 Requests mit je 2 s Pause). Manche Kalender-Clients haben kürzere Timeouts; dann hilft ein kleineres `REQUEST_DELAY_SECONDS` oder später ein Hintergrund-Abruf.
- Ruft niemand den Endpunkt ab, wird auch nichts gespeichert. Wochen, in denen kein Client abruft, fehlen später in der Historie.
- Der Login gegen das echte Intranet ist bisher nur aus der Formularanalyse abgeleitet und nicht mit echten Zugangsdaten getestet.
