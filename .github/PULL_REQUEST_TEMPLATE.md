## Bezug

<!-- Genau eine passende eigenständige Beziehungslinie stehen lassen. -->
Refs #<issue>

## Änderung

- Was wurde geändert?
- Welches Abnahmekriterium wird damit erfüllt?

## Koordination

- [ ] Der kanonische Claim im Arbeits-Issue ist aktuell.
- [ ] Der Claim steht für Review auf `Phase: review` und nennt diesen PR.
- [ ] #38, offene Claims und offene PRs wurden nach dem letzten wesentlichen Rebase/Scope-Change erneut geprüft.
- Coordination keys: `none`
- Bewusste Überschneidungen / Merge-Reihenfolge: keine

## Prüfungen

- [ ] Relevante Tests erfolgreich
- [ ] `cd backend && ../.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings` ohne unerwartete Änderungen, falls Modelle betroffen sind
- Ausgeführt: <!-- Befehle und Ergebnis -->

## Sicherheit, Migration und Betrieb

- Berechtigungs-/Datenschutzwirkung: keine / <!-- beschreiben -->
- Migration/Rollback: nicht erforderlich / <!-- beschreiben -->
- Bekannte Grenzen / offene Punkte: keine / <!-- beschreiben -->

## Handoff / Restarbeit

- Restarbeit: keine / <!-- Issues oder klaren Umfang nennen -->
