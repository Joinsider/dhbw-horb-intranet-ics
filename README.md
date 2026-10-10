# dhbw-intranet-ics

Stellt den Stundenplan aus dem Intranet der DHBW Horb als abonnierbaren ICS-Kalender bereit.

## Start

Vorlage kopieren und `API_KEY`, `INTRANET_USER` und `INTRANET_PASSWORD` in der `.env` eintragen:

```bash
cp .env-example .env
```

Dann starten:

```bash
mkdir -p data && docker compose up -d --build
```

Kalender-URL für den Client:

```
http://<host>:8000/calendar.ics?api_key=<API_KEY>
```

`&cache=false` erzwingt einen frischen Abruf, frühestens aber 5 Minuten nach dem letzten Intranet-Abruf.

## Konfiguration

| Variable | Standard | Bedeutung |
|---|---|---|
| `API_KEY` / `API_KEY_FILE` | – | Schlüssel für `?api_key=` |
| `INTRANET_USER` / `INTRANET_USER_FILE` | – | Intranet-Benutzer |
| `INTRANET_PASSWORD` / `INTRANET_PASSWORD_FILE` | – | Intranet-Passwort |
| `KURS` | `HOR-TINF2024` | Kurs, z. B. `INF2024` oder `HOR-TINF2024` |
| `WEEKS_AHEAD` | `4` | Wochen zusätzlich zur aktuellen Woche |
| `CACHE_TTL_SECONDS` | `3600` | Cache-Dauer für aktuelle und zukünftige Wochen |
| `MIN_FETCH_INTERVAL_SECONDS` | `300` | Mindestpause zwischen zwei Intranet-Abrufen |
| `REQUEST_DELAY_SECONDS` | `2` | Pause zwischen einzelnen Requests |
| `DB_PATH` | `/data/schedule.db` | SQLite-Datei (Volume `/data`) |
| `FILTERS_FILE` | `/data/filters.toml` | Filterregeln, optional |

Die `*_FILE`-Varianten lesen den Wert aus einer Datei, z. B. einem Docker Secret.

## Filter

Termine lassen sich über eine TOML-Datei ausblenden, z. B. Fächer, die man nicht belegt:

```bash
cp filters.example.toml data/filters.toml
```

```toml
[[exclude]]
title = ["Funktionale Programm", "Übung_ F. Progamm"]
kind = "lecture"   # Klausuren bleiben sichtbar

[[exclude]]
title_contains = "Funknetze"
```

- Jeder `[[exclude]]`-Block ist eine Regel; ein Termin fällt raus, sobald eine Regel passt. Innerhalb einer Regel müssen alle Felder passen, bei Listen reicht ein Wert.
- Felder: `title` (exakt), `title_contains`, `title_regex`, `person`, `room`, `kind` (`lecture`, `exam`, `oral_exam`, `other`). Groß-/Kleinschreibung spielt keine Rolle.
- Klausuren haben denselben Titel wie die Vorlesung. Ohne `kind = "lecture"` verschwinden sie mit.
- Änderungen an der Datei gelten ab dem nächsten Abruf, ohne Neustart. Ist die Datei beim Start fehlerhaft, startet der Container nicht; wird sie im Betrieb fehlerhaft, bleiben die letzten gültigen Regeln aktiv (Fehler im Log).
- `http://<host>:8000/titles?api_key=<API_KEY>` listet alle gespeicherten Titel mit Art, Anzahl und wie viele davon gefiltert werden.
- Gefiltert wird nur bei der Auslieferung, die Datenbank bleibt vollständig. Der Header `X-Filtered-Events` nennt die Zahl der ausgeblendeten Termine.

## Verhalten

- Abgerufen werden nur die aktuelle Woche und `WEEKS_AHEAD` weitere Wochen.
- Vergangene Wochen bleiben in der Datenbank und im Kalender, werden aber nicht erneut abgerufen.
- Feiertage werden ausgelassen. Klausuren erscheinen als `Klausur: <Titel>`, mündliche Prüfungen mit ihrem Titel aus dem Intranet.
- Schlägt der Login dreimal hintereinander fehl (1 Versuch + 2 Wiederholungen), versucht der Container es 6 Stunden lang nicht mehr. Ein Neustart hebt die Sperre auf.
- Schlägt ein Abruf fehl, liefert der Endpunkt den gespeicherten Stand (Header `X-Refresh-Failed: true`).

## Entwicklung

```bash
uv run pytest
```

Bei Pull Requests auf `main`/`master` laufen die Tests automatisch. Ein Tag `vX.Y.Z` veröffentlicht das Image als `ghcr.io/<owner>/<repo>` mit den Tags `X.Y.Z`, `X.Y` und `latest`:

```bash
git tag v0.1.0 && git push origin v0.1.0
```

Entscheidungen stehen in [docs/adr](docs/adr).
