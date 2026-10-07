# Implementierungsstand 0.1

## Verfügbar

- Django 5.2/Python 3.12, PostgreSQL und Gunicorn; Abhängigkeiten exakt versioniert.
- Docker-Compose-Grundbetrieb für intern/Einzelserver und getrennten externen Host.
- Caddy mit lokaler CA; nur Proxyports veröffentlicht, Datenbanknetze intern.
- Persönliche Konten, Passwort plus E-Mail-Code, Ablauf, Einmaligkeit, Versuchslimits und privates Session-Cookie.
- Organisationstypen, primärer Baum mit Kreisprüfung und zusätzliches Beziehungsmodell.
- Zeitlich gültige explizite Rollen, kein automatischer Zugriff auf untergeordnete Organisationen, kein Superuser-Fachzugriff.
- Auswahl und Speicherung des sichtbaren Arbeitskontexts; Entzug wird bei jeder Anfrage erneut geprüft.
- Erste Weboberfläche: Anmeldung, Arbeitsplatz, Kontextwechsel und Anlegen untergeordneter Organisationen mit ausdrücklicher Zuweisung.
- Auditereignisse für Einrichtung, Anmeldung, Kontextwahl und Organisationsanlage.
- Separate öffentliche Serverrolle ohne private Routen sowie geschützte Rolle ohne interne Organisationsverwaltung.
- Tests, Migrationsprüfung und GitHub-Actions-Checks einschließlich PostgreSQL, Compose-/Caddy-Validierung und Imagebuild.

## Noch nicht implementiert

Dies ist eine Entwicklungsgrundlage, noch kein produktionsfertiges RIS. Insbesondere fehlen Benutzerverwaltung/Einladungen/Import in der Oberfläche, weitere Rollen/Rechtekonfiguration, TOTP/Passkeys, Stammdaten-/Gremienverwaltung, Vorlagen und Fachworkflows, Live-/Offline-Sitzung, Abstimmungen, Veröffentlichung, Suche, Synchronisierung, Backupverwaltung, Domain-/Zertifikatsadministration und Löschbarkeit der späteren Testdaten. Es werden aktuell keine Testpersonen oder automatisch erzeugten Fachdatensätze ausgeliefert. Die vorgesehenen minimalen Testdaten folgen mit den Fachmodulen.

Der externe geschützte Dienst kann gestartet werden, hat aber noch keine Kontenprovisionierung vom internen System. Seine Loginseite ist deshalb noch kein vollständiger Mandatsträgerzugang. Der öffentliche Dienst zeigt einen ausdrücklich gekennzeichneten Leerzustand, keine simulierten Veröffentlichungen. Die Zweiserverdatei stellt Netz-/Datenbankgrenzen bereit; Datenabgleich ist noch nicht vorhanden.

TLS verwendet aktuell fest die lokale Caddy-CA. Let's Encrypt, DNS-Prüfung und Zertifikatimport sind dokumentierte nächste Betriebsfunktionen, noch keine Weboption. Keine automatische Migration beim Containerstart: Datenbankschema wird bewusst vor Betriebsstart eingerichtet.

## Oberfläche und technische Entscheidung

Der erste Stand verwendet serverseitige Django-Templates mit lokalem CSS statt eines zusätzlichen React-Builds. Dadurch sind Konten-/Rechtefluss sofort durchgängig testbar und CSP kann ohne Skriptausführung auskommen. React/TypeScript aus dem Architekturvorschlag bleibt für spätere interaktive Fachmodule eine Option, keine bereits ausgelieferte Komponente. Keine externen Schriften, Tracker oder Frontend-CDNs.

## Entwicklung

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r backend/requirements.txt
cd backend
../.venv/bin/python manage.py test --settings=config.test_settings
../.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings
```

`config.test_settings` ist ausschließlich für isolierte Tests: In-Memory-SQLite, Test-Mailbackend und schneller Test-Passworthasher. Niemals als Serverkonfiguration verwenden. Produktionskonfiguration setzt HTTPS und sichere Cookies voraus.

## Änderungen

Ab jetzt jede Änderung über Branch → Pull Request → relevante Prüfungen → Merge. Der Anforderungskatalog bleibt gültig; dieser Stand setzt erst einen Teil davon um.
