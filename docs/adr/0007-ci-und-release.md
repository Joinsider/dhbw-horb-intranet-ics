# ADR 0007: CI und Release über GitHub Actions

- Status: akzeptiert
- Datum: 2026-09-30

## Kontext

Tests sollen bei Pull Requests automatisch laufen, und das Docker-Image soll automatisch in der GitHub Container Registry (GHCR) veröffentlicht werden.

## Entscheidung

### Tests (`.github/workflows/test.yml`)

- Läuft bei Pull Requests auf `main` oder `master`.
- `uv run --locked --python 3.12 pytest`: nutzt die `uv.lock`, schlägt fehl, wenn sie nicht zur `pyproject.toml` passt.
- Die Tests brauchen weder Zugangsdaten noch Netzwerkzugriff auf das Intranet, sie laufen gegen die Fixtures.

### Release (`.github/workflows/release.yml`)

- Auslöser ist ein Git-Tag der Form `vX.Y.Z`, nicht jeder Push auf den Hauptzweig. So entsteht ein Image nur, wenn bewusst eine Version vergeben wird.
- Vor dem Veröffentlichen laufen dieselben Tests (der Test-Workflow wird per `workflow_call` wiederverwendet).
- Image: `ghcr.io/<owner>/<repo>` mit den Tags `X.Y.Z`, `X.Y` und `latest`.
- Plattformen: `linux/amd64` und `linux/arm64` (z. B. für Raspberry Pi oder ARM-Server).
- Anmeldung mit dem `GITHUB_TOKEN` des Workflows (`packages: write`), es ist kein eigenes Secret nötig.

## Konsequenzen

- Ein Release wird so ausgelöst: `git tag v0.1.0 && git push origin v0.1.0`.
- Das Paket ist bei GHCR nach dem ersten Push privat. Zum Pullen auf dem Server braucht es entweder `docker login ghcr.io` mit einem Token oder die Sichtbarkeit wird in den Paket-Einstellungen auf öffentlich gestellt.
- Der ARM-Build läuft über QEMU-Emulation und ist langsamer als der amd64-Build.
- Die Version in `pyproject.toml` wird nicht automatisch mit dem Tag abgeglichen.
