# ADR 0003: Anforderungen an den ICS-Container

- Status: akzeptiert
- Datum: 2026-09-30

## Kontext

Ein Docker-Container soll den Stundenplan aus dem Intranet (siehe ADR 0002) als abonnierbaren ICS-Kalender bereitstellen. Clients aktualisieren z. B. alle 30 Minuten.

## Entscheidung

### Endpunkt

- Ein HTTP-Endpunkt liefert den Kalender als `text/calendar`.
- Authentifizierung über URL-Parameter `?api_key=…`. Ohne gültigen Key gibt es keinen Zugriff.
- Optionaler Parameter `?cache=false` erzwingt einen frischen Abruf der zukünftigen Wochen.

### Konfiguration

| Einstellung | Quelle |
|---|---|
| API-Key | Env-Variable oder Datei |
| Intranet-Zugangsdaten | Env-Variable oder Datei |
| Kurs | Env-Variable, Standard `HOR-TINF2024` (zunächst nur INF24) |
| Anzahl Wochen in die Zukunft | Env-Variable |

### Termindaten

Pro Vorlesung: Start, Ende, Titel, Dozent, Raum/Ort.

### Abruf und Speicherung

- Es werden genau die aktuelle Woche plus die konfigurierte Anzahl zukünftiger Wochen abgerufen, nicht mehr.
- Eine lokale Datenbank liegt auf einem vom Docker-Host eingebundenen Volume und speichert alle jemals abgerufenen Vorlesungen dauerhaft.
- Vergangene Vorlesungen werden weiter über den Endpunkt ausgeliefert, aber nicht erneut aus dem Intranet abgerufen.
- Zukünftige Wochen werden 1 Stunde gecacht. Anfragen innerhalb dieser Zeit werden aus dem Cache beantwortet.

### Schutz des Intranet-Logins

- Bei Login-Fehlern maximal 2 erneute Versuche, danach kein weiterer Versuch (kein Endlos-Retry).
- Requests an das Intranet laufen nacheinander und mit Pause, um das Rate Limiting nicht auszulösen.

## Konsequenzen

- `cache=false` kann von jedem Client mit API-Key beliebig oft aufgerufen werden und würde das Rate Limit gefährden. Dafür ist eine Mindestpause zwischen zwei Intranet-Abrufen nötig, die auch `cache=false` nicht unterschreitet.
- Wenn der Login dauerhaft fehlschlägt, liefert der Endpunkt den letzten gespeicherten Stand statt eines Fehlers, damit Kalender-Clients nicht leer laufen.
- Der API-Key in der URL landet in Proxy- und Server-Logs. Das ist für Kalender-Abos üblich und hier akzeptiert.

## Offene Punkte

- Tech-Stack: siehe ADR 0004 (vorgeschlagen).
- Mehrere Kurse gleichzeitig (z. B. per URL-Parameter) sind später vorgesehen.
