# ADR 0008: Filter für Termine

- Status: akzeptiert
- Datum: 2026-10-10

## Kontext

Nicht jeder Termin des Kurses ist für jeden relevant, z. B. „Funktionale Programm“ und „Übung_ F. Progamm“ (beide KW 40, Dozent Plümicke). Solche Termine sollen ausgeblendet werden können, für beliebig viele Fächer. Die Titel stammen unverändert aus dem Intranet und sind teils abgekürzt oder falsch geschrieben.

## Entscheidung

- Filterregeln stehen in einer TOML-Datei, Standard `/data/filters.toml` (`FILTERS_FILE`). Sie liegt im bereits eingebundenen Volume, `docker-compose.yml` bleibt unverändert. TOML liest Python ohne zusätzliche Abhängigkeit (`tomllib`), und Listen und Kommentare sind leichter zu pflegen als in einer Env-Variable.
- Nur Ausschlussregeln (`[[exclude]]`). Eine Regel verknüpft ihre Felder mit UND, Werte in einer Liste und mehrere Regeln mit ODER. Felder: `title`, `title_contains`, `title_regex`, `person`, `room`, `kind`.
- Vergleiche ignorieren Groß-/Kleinschreibung und mehrfache Leerzeichen, weil die Titel aus dem Intranet nicht einheitlich sind.
- Gefiltert wird bei der Auslieferung, nicht beim Speichern. Die Datenbank bleibt vollständig, geänderte Regeln wirken sofort auch auf vergangene Wochen, ohne neuen Intranet-Abruf.
- Die Datei wird bei jeder Anfrage auf Änderungen geprüft (mtime und Größe) und bei Bedarf neu geladen. Kein Neustart nötig.
- Ist die Datei beim Start ungültig, bricht der Start ab. Wird sie im Betrieb ungültig, bleiben die letzten gültigen Regeln aktiv und der Fehler wird geloggt, damit Kalender-Clients nicht plötzlich ungefilterte Termine bekommen. Unbekannte Schlüssel und Arten sind Fehler, damit Tippfehler nicht still ignoriert werden.
- `GET /titles?api_key=…` listet alle ausgelieferten Titel mit Art, Anzahl und Zahl der gefilterten Termine, um Regeln gegen die echten Titel schreiben und prüfen zu können.

## Verworfene Alternativen

- Env-Variable mit kommagetrennten Titeln: Titel können Kommas enthalten, und für mehrere Felder pro Regel reicht das Format nicht.
- Filter als URL-Parameter: macht die Abo-URL lang und unübersichtlich. Für einen Nutzer pro Container reicht eine Datei.
- Filtern beim Speichern: gefilterte Termine wären verloren, eine geänderte Regel bräuchte einen neuen Abruf, und vergangene Wochen werden nie neu abgerufen.

## Konsequenzen

- Eine Klausur hat denselben Titel wie die Vorlesung (ADR 0005). Ohne `kind = "lecture"` blendet eine Titelregel auch die Klausur aus. Das ist in README und Beispieldatei beschrieben.
- Ändert das Intranet einen Titel, greift eine `title`-Regel nicht mehr; `title_contains` oder `title_regex` sind robuster.
- Mehrere Personen mit unterschiedlichen Filtern brauchen später Profile (z. B. `[profile.<name>]` plus `?profile=`). Das Format lässt sich dafür erweitern, ohne bestehende Dateien zu brechen.
