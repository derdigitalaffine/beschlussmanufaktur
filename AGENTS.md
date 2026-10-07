# Entwicklungsvorgaben

- Grundlage sind README und docs/01 bis docs/10. Bestehende Anforderungen nicht still reduzieren.
- Jede Änderung über einen eigenen Branch und Pull Request; nach erfolgreichen relevanten Prüfungen mergen. Keine direkten Implementierungscommits auf main.
- Kein Merge bei fehlgeschlagenen relevanten Checks. Offene technische Grenzen im PR und Implementierungsstand dokumentieren.
- Serverseitige Rechte standardmäßig verweigern, aktiven Arbeitskontext und gültige Zuweisung prüfen. Technische Superuser erhalten keine impliziten Fachrechte.
- Öffentlicher Dienst erhält keine geschützten Daten und keine internen Zugangswege. Von außen initiierte Verbindung nach innen bleibt standardmäßig gesperrt.
- Aufnahme/Transkription/KI und Sitzungsgeld erst nach Kernabschluss entwickeln.
- Tests: `cd backend && ../.venv/bin/python manage.py test --settings=config.test_settings`.
- Migrationen einchecken; `makemigrations --check --dry-run` muss ohne Änderungen enden.
- Geheimnisse, Datenbanken und lokale Laufzeitdateien niemals committen.

