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

Die `*_FILE`-Varianten lesen den Wert aus einer Datei, z. B. einem Docker Secret.

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
