# ADR 0001: ADRs als Entscheidungsdokumentation

- Status: akzeptiert
- Datum: 2026-09-30

## Kontext

Das Projekt entsteht in mehreren Sitzungen. Entscheidungen und Erkenntnisse (z. B. über die Struktur der Intranet-Seite) sollen nachvollziehbar bleiben.

## Entscheidung

Getroffene Entscheidungen und relevante Informationen werden als Architecture Decision Records unter `docs/adr/` abgelegt.

- Dateiname: `NNNN-kurzer-titel.md`, fortlaufend nummeriert
- Aufbau: Status, Datum, Kontext, Entscheidung, Konsequenzen
- Status: `vorgeschlagen`, `akzeptiert`, `ersetzt durch NNNN`
- Bestehende ADRs werden nicht umgeschrieben, sondern durch neue ersetzt. Reine Faktensammlungen (wie ADR 0002) dürfen ergänzt werden.

## Konsequenzen

Jede neue Entscheidung in diesem Projekt bekommt einen ADR oder ergänzt einen bestehenden.
