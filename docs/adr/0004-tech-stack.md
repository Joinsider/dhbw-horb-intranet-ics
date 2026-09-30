# ADR 0004: Tech-Stack

- Status: akzeptiert (Option A, Python)
- Datum: 2026-09-30

## Kontext

Der Container braucht laut ADR 0002 und 0003: einen HTTP-Client mit Cookie-Jar und Formular-Login, einen HTML-Parser mit CSS-Selektoren, einen ICS-Generator, einen kleinen HTTP-Server und eine dateibasierte Datenbank auf einem Volume. Ein Headless-Browser ist nicht nötig.

Für alle Optionen gleich:

- Datenbank: SQLite als einzelne Datei auf dem eingebundenen Volume. Ein eigener DB-Container (Postgres o. Ä.) wäre für einen Kurs und wenige hundert Termine pro Jahr unnötig.
- Cache: Abrufzeitpunkt pro Woche in derselben SQLite-Datei statt im Arbeitsspeicher, damit der Cache einen Neustart übersteht und kein Redis nötig ist.

## Optionen

| | A: Python | B: Go | C: TypeScript (Node) | D: Rust |
|---|---|---|---|---|
| HTTP-Server | FastAPI + uvicorn | `net/http` (Standardbibliothek) | Hono oder Fastify | axum |
| HTTP-Client | httpx | `net/http` + `cookiejar` | `fetch` + tough-cookie | reqwest |
| HTML-Parsing | selectolax oder BeautifulSoup | goquery | cheerio | scraper |
| ICS | icalendar | golang-ical | ical-generator | icalendar |
| SQLite | `sqlite3` (Standardbibliothek) | modernc.org/sqlite (ohne CGO) | better-sqlite3 | rusqlite |
| Image-Größe (ca.) | 60–80 MB | 10–20 MB | 80–150 MB | 10–20 MB |
| RAM im Leerlauf (ca.) | 40–60 MB | 5–15 MB | 50–80 MB | 5–10 MB |
| Entwicklungsaufwand | niedrig | mittel | niedrig | hoch |

Die Größenangaben sind Erfahrungswerte, nicht gemessen.

### A: Python

- Plus: Scraping und Parsing gehen am schnellsten von der Hand, ausgereifte Bibliotheken für ICS und Zeitzonen, Parser lässt sich leicht anpassen, wenn sich das HTML ändert.
- Minus: größeres Image, mehr RAM, Abhängigkeiten zur Laufzeit.

### B: Go

- Plus: ein statisches Binary, sehr kleines Image (`scratch`/`distroless`), wenig RAM, fast alles aus der Standardbibliothek, gut für einen Dienst, der jahrelang unbeaufsichtigt läuft.
- Minus: Parsing-Code ist wortreicher, ICS-Bibliothek weniger komfortabel.

### C: TypeScript (Node)

- Plus: cheerio ist sehr bequem für HTML, gute ICS-Bibliothek, Typen.
- Minus: größtes Image, `better-sqlite3` braucht native Builds, viele transitive Abhängigkeiten.

### D: Rust

- Plus: kleinstes und sparsamstes Ergebnis.
- Minus: deutlich höherer Aufwand und lange Build-Zeiten für ein Projekt dieser Größe.

## Empfehlung

A (Python), wenn schnelle Anpassbarkeit des Parsers am wichtigsten ist. B (Go), wenn ein möglichst kleiner, wartungsarmer Container am wichtigsten ist. C und D bieten hier keinen Vorteil gegenüber A bzw. B.

## Entscheidung

Option A, Python (entschieden am 2026-09-30).

- Python 3.12, FastAPI + uvicorn, httpx, icalendar, `sqlite3` aus der Standardbibliothek
- HTML-Parsing mit selectolax (Lexbor). Der Parser baut den DOM nach HTML5-Regeln wie ein Browser auf; gegen einen Browser-DOM wurde die Tageszuordnung in ADR 0002 geprüft.
- Basis-Image `python:3.12-slim`, Prozess läuft als UID 1000, Datenbank unter `/data`
- Tests mit pytest gegen zwei echte Stundenplan-Seiten (KW 40 und KW 51 2026) unter `tests/fixtures/`
