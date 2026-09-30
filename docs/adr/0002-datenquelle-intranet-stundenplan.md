# ADR 0002: Datenquelle – Digitaler Stundenplan im Intranet der DHBW Horb

- Status: akzeptiert
- Datum: 2026-09-30

## Kontext

Die Vorlesungsdaten gibt es nur als HTML-Seite hinter dem Intranet-Login. Dieser ADR hält fest, was bei der manuellen Analyse am 2026-09-30 (eingeloggt, Kurs INF2024, KW 40) beobachtet wurde.

## Beobachtungen

### Login

- Seite: `https://www.hb.dhbw-stuttgart.de/intranet` (TYPO3, Extension `felogin`)
- Formular: `POST /intranet?tx_felogin_login[action]=login&tx_felogin_login[controller]=Login&cHash=<hash>`
- Felder: `user`, `pass`, `logintype=login`, `noredirect=1`, `submit`
- Dynamische Hidden-Felder, die vor jedem Login frisch aus der Login-Seite gelesen werden müssen: `pid`, `referer`, `__referrer[@extension|@controller|@action|arguments|@request]`, `__trustedProperties`, sowie der `cHash` in der Action-URL
- Die Session läuft über ein Cookie, das per JavaScript nicht lesbar ist (HttpOnly). Name und Lebensdauer sind noch nicht ermittelt.
- Kein CAPTCHA und kein JavaScript nötig, ein einfacher HTTP-Client mit Cookie-Jar reicht.

### Stundenplan-Abruf

- Seite: `https://www.hb.dhbw-stuttgart.de/intranet/digitaler-stundenplan`
- Das Formular ist ein einfaches `GET`, die Woche lässt sich direkt per URL abrufen:
  `?kurs=HOR-TINF2024&day=30&month=9&year=2026&goto=Datum+anzeigen`
- Ein beliebiger Tag der Woche liefert die ganze Woche (Mo–Sa).
- Weitere Submit-Parameter: `prev=<<`, `next=>>`, `today=Heute` (werden nicht gebraucht).
- Kurs-IDs haben das Schema `HOR-T<KURS><JAHR>[Suffix]`, z. B. `HOR-TINF2024`, `HOR-TET2025`, `HOR-TMB2024KE1`, `HOR-TWI2024AW-IBM`. Die vollständige Liste steht im `<select name="kurs">`.
- Das Jahr-Dropdown bietet nur Vorjahr, aktuelles Jahr und Folgejahr an.
- Ohne Kurs zeigt die Seite „Bitte einen Kurs auswählen“, mit Kurs steht die Kurs-ID in einer Überschrift (als Erfolgsprüfung nutzbar).

### HTML-Struktur (Rapla-artiger Wochenplan)

- `<table class="week_table">`, eine Seite ist ca. 50 KB groß
- Kopfzeile: `th.week_number` („KW 40“), danach je Tag ein `td.week_header` mit Text „Mo 28.09.26“ und einem `colspan`
- Zeitraster: 4 Tabellenzeilen pro Stunde (15 Minuten), 07:00 bis 20:00
- Eine Vorlesung ist ein `td.week_block` mit `rowspan` und diesen Kindern:

| Element | Inhalt | Beispiel |
|---|---|---|
| `span.time` | Start und Ende, mit `&nbsp;` | `08:30 -12:00` |
| `span.name` | Vorlesungstitel | `GL K. Intelligenz` |
| `span.person` | Dozent (kann leer sein) | `Prof. Dr. …` |
| erstes `span.resource` | Raum / Ort | `HOR-121`, `HOR-ONLINE` |
| weiteres `span.resource` | Kurs-ID | `HOR-TINF2024` |

- Start und Ende stehen minutengenau im Text, das 15-Minuten-Raster muss dafür nicht ausgewertet werden.
- **Der Wochentag steht nicht im Block.** Er ergibt sich nur aus der Spaltenposition. Dazu muss das Tabellenraster inklusive `rowspan`/`colspan` nachgebaut werden: Spalte 0 ist die Zeitspalte, danach belegt jeder Tag so viele Spalten wie sein Header-`colspan` angibt. Das wurde gegen die gerenderte Position geprüft und stimmte für alle 10 Blöcke der Woche.
- Der `colspan` eines Tages ist nicht konstant (normal 3, bei parallelen Terminen 5).

### Besonderheiten in den Daten

- Titel sind von der Quelle gekürzt (ca. 20 Zeichen), z. B. „Funktionale Programm“. Der volle Titel ist auf der Seite nicht vorhanden (keine Tooltips, keine Detail-Links).
- Parallele Blöcke: dieselbe Vorlesung kann zur selben Zeit zweimal vorkommen, mit unterschiedlichem Dozent und Raum (z. B. „Advanced SWE“ in `HOR-121` und `HOR-ONLINE`).
- Feiertage sind eigene Blöcke (07:00–19:00, Titel „Feiertag“, `resource` enthält den Namen des Feiertags statt Raum und Kurs, roter Hintergrund).
- Es gibt keine stabile Termin-ID im HTML.

## Entscheidung

- Abruf per einfachem HTTP-Client (Login-POST, danach GET pro Woche), kein Headless-Browser.
- Parsing über die CSS-Klassen oben, Tageszuordnung über das nachgebaute Tabellenraster.

## Konsequenzen

- Pro Woche ist genau ein Request nötig. Bei N Wochen Vorschau also N Requests, die mit Pause nacheinander laufen (Rate Limiting).
- Der Container braucht Intranet-Zugangsdaten (Env-Variable oder Datei).
- Da es keine Termin-ID gibt, muss die ICS-`UID` aus den Termindaten abgeleitet werden.
- Änderungen am HTML der Seite brechen den Parser. Eine gespeicherte Beispielseite als Test-Fixture ist sinnvoll.

## Offene Punkte

- Lebensdauer der Session und genaues Rate-Limit sind unbekannt.
- Umgang mit Feiertagen (als Termin ausgeben oder weglassen) und parallelen Blöcken (getrennt oder zusammengeführt) ist noch zu entscheiden.
