# Implementierungsstand 0.7

## Implementierte Entwicklungsfunktionen

| Bereich | Verfügbar | Bedienung |
|---|---|---|
| Konten | Passwort plus E-Mail-Code, persönliche Konten, befristete Rollen, Einladungen ohne Selbstregistrierung | docs/13 |
| Organisation/Rechte | Hauptbaum und zusätzliche Beziehungen, Stammdaten/Legislaturperioden/Gremien/Funktionen/Mandate, einfacher/erweiterter Modus, expliziter Arbeitskontext, Einzelrechte | docs/14 |
| Austausch | Separate Datenbanken/Dienste, geschützte Kontenprovisionierung, Rechteentzug, signierte Snapshots und Dateien, externe Vorschläge mit interner Genehmigung | docs/14–16 |
| Vorlagen | Markdown-Webeditor und Vorschau, Arten/Pflichtfelder, Anlagen, Fassungen, parallele Bearbeitung mit Konfliktprüfung, Aufgaben/Hinweise, Prüfketten, Jahresnummern, PDF/DOCX, getrennte Veröffentlichung | docs/14 |
| Vorbereitung | Kalender, Zuständigkeiten, Tagesordnung/Unterpunkte, Einladung mit festem Versandstand, genehmigte Nachträge, technische Zustellung und Kenntnisnahme, persönliche PDF-Gesamtmappe/ICS | docs/15 |
| Live | Exklusive Sitzungshoheit mit Epoche/Heartbeat, begründete Vorsitzübernahme, vorbereitete Besetzung, Ein-/Austritte mit Zeit/TOP, Befangenheit, dokumentierte Beschlussfähigkeit, Notizen/Anträge, Journal | docs/16 |
| Abstimmen | Fester Versuch/Wortlaut/Optionen/Stimmrechtskreis, digitale namentliche Stimmen ausschließlich online, gesonderte Hand-/Papierauszählung, fehlende Stimmen, Abbruch bei Kontextänderung, Ergebnisfeststellung und Beschluss | docs/16-live-sitzungsfuehrung |
| Rückgabe | Extern abgeschlossene Sitzung wird eingefroren, intern abgeholt, geprüft und ausdrücklich genehmigt; kein automatisches Übernehmen externer Fachänderungen | docs/16 |
| Niederschrift | Journaldraft, manuelle Ergebnis-/Verlaufs-/Wortfassung, unveränderliche Fassungen, Schriftführung→Vorsitz, Rückgabe/Berichtigung mit Folgesitzungsbezug, separate öffentliche Fassung, PDF/DOCX | docs/17 |
| Beschlusskontrolle | Optionale Zuständigkeit/Frist, Kenntnisnahme ohne Aufgabe, Teilfortschritt, Erledigungsmeldung und geprüfter Abschluss, Historie, neutraler Hinweis | docs/18 |
| Persönlicher Bereich | Aktuell berechtigte Suche/Favoriten/zuletzt geöffnet, konto- und kontextgebundene eigene Notizen, keine fremden Notizen im Fachjournal | docs/19 |
| Offline | HTTPS-Browseroberfläche, verschlüsselte IndexedDB-Mappen und optionales PDF, persönliche Notizen und lokale Schriftführungsereignisse, signierte Vorbereitung, ausdrücklicher atomarer Abgleich und sichtbare Konflikte | docs/19 |
| Betrieb | Linux/Docker Compose, Django 5.2/Python 3.12/PostgreSQL/Gunicorn, Caddy lokale CA, SMTP-Worker, Dateivolumes, getrennte Datenbanknetze, Prozess-/Datenbankbereitschaft | docs/12 |

Öffentliche Dienste erhalten ausschließlich ausdrücklich freigegebene Projektionen und Anlagen. Das vorhandene öffentliche Portal ist eine Grundlage mit freigegebenen Datensätzen, noch nicht der in Etappe 8 geplante umfassende Portal-/Integrationsausbau. Geschützte Dienste können bereitgestellte Konten, Unterlagen und Sitzungen verwenden; interne Organisations-/Vorlagenadministration bleibt intern. Technische Superuser bekommen keine impliziten Fachrechte.

## Noch offen und Grenzen

- Digitale **geheime** Wahlen/Abstimmungen: nicht implementiert; geheime Papierauszählung ist verfügbar. Keine Anonymitätsbehauptung durch Verbergen von Namen. Ein gesondert geprüfter Entwurf und unabhängige qualifizierte Prüfung bleiben erforderlich.
- Vollständiger Bürgerportal-/Domain-/CI-/iframe-/Such-/IMAP-Ausbau, OParl-/DMS-Vorbereitung und weitergehende Administration: folgende Etappen. SMTP-Versand und ICS-Dateien sind bereits verfügbar.
- Benutzerimport, Passwortwiederherstellung, TOTP/Passkeys, dokumentierter Notfallzugriff, frei konfigurierbare TLS-/DNS-/Zertifikatsverwaltung, automatisiertes Backup/Restore und löschbare minimale Auslieferungstestdaten: noch offen. Aktuell werden keine Testpersonen automatisch ausgeliefert.
- Einfache/erweiterte Ansichten sind vorhanden; manche erweiterte Rechte-/Workflowkonfiguration verwendet noch technische Felder/JSON. Die Bedienbarkeit muss mit Fachanwendern erprobt und weiter vereinheitlicht werden.
- Zentrale Personenstammdaten sind vorhanden, die organisationsübergreifende Dubletten-/Identitätsverwaltung sowie komfortable Bearbeitung aller Mehrfachbeziehungen sind weiter auszubauen. Keine stillschweigende Abnahme des gesamten ORG-Katalogs.
- Exporte verwenden lokale Text-/Listen-/Tabellenkonvertierung; komplexe Dokumenttypografie und CI benötigen weitere Abnahme. Kein automatisch erzeugtes Audio-/Wortprotokoll, keine qualifizierte elektronische Signatur.
- Transferverträge sind bewusst begrenzt (8 MiB pro Antwort/Anfrage, Dateien 4 MiB, Offline-Abgleich 2 MiB, lokale PDF 20 MiB). Große Gesamtdatenbestände benötigen vor Betrieb Chunking/inkrementelle Übertragung und Lastprüfung; die Zielgröße von 150 Sitzungen/Jahr wurde nicht als Lastabnahme bestätigt.
- Keine lokale Docker-Laufzeit verfügbar; Compose/Caddy und Imagebuild werden in GitHub CI geprüft. Chromium-Offlinemechanik ist automatisiert geprüft; iPad/Firefox, vollständige reale Zweiserverstrecke und Fachanwenderabläufe sind noch praktisch abzunehmen.
- Offlinekopien können zentrale Rechteänderungen ohne Netz nicht sofort erkennen. Lokale Verschlüsselung ersetzt keine Gerätesicherheit; Details und Löschwege in docs/19.

Der gesamte bestätigte KERN-Katalog bleibt verbindlich. Der Stand ist zur Entwicklung und Erprobung bestimmt; **keine Produktivfreigabe**. Aufnahme/Transkription/KI und Sitzungsgeld sind weiterhin bewusst verschoben. Weitere Anforderungen werden nicht durch diese Auflistung aufgehoben.

## Prüfungen und Entwicklung

199 Backendtests laufen lokal mit In-Memory-SQLite. GitHub prüft zusätzlich PostgreSQL, getrennte öffentliche/geschützte Rollen, Migrationen, JavaScript-Syntax, Compose, Caddy und Imagebuild. Drei Node-Prüfungen decken Verschlüsselung, Manipulation, falsches Passwort und große Daten ab. Chromium prüft verschlüsselte Vorbereitung, echtes Offline-Neuladen, persönliche Notizen, sichere Textausgabe, Kontext-/Zentralstandkonflikte und ausschließlich statische Shell-Caches. Die Zahl wird bei weiteren Regressionstests angepasst.

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r backend/requirements.txt
cd backend
../.venv/bin/python manage.py test --settings=config.test_settings
../.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings
```

Im Repositoryroot: `node --test tests/offline_crypto.cjs`. Für den Browsercheck separat `npm install --no-save --package-lock=false playwright@1.62.1`, `npx playwright install --with-deps chromium`, `node tests/offline_browser.cjs`. Browsertransportfixtures sind isolierte Testdaten und werden nicht ausgeliefert. `config.test_settings` ist ausschließlich für Tests, niemals Serverkonfiguration.

Die Oberfläche verwendet Django-Templates mit lokalem CSS/JavaScript, keine externen Schriften/CDNs/Tracker. CSP gestattet keine Inline-Skripte. Änderungen: Branch → kleiner PR → relevante grüne Prüfungen → Merge. Der Etappenplan steht in docs/20; die Abnahmeszenarien aus docs/09 sind weiterhin offen, soweit keine konkrete fachliche Abnahme dokumentiert wurde.
