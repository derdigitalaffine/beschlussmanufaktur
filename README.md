# Beschlussmanufaktur

![Beschlussmanufaktur – Dokument und Beschluss](backend/static/brand-mark.svg)

> **Entwicklungssoftware, nicht für den produktiven Betrieb freigegeben.** Ein erfolgreicher CI-Lauf ersetzt weder eine fachliche Abnahme noch Penetrationstest, Barrierefreiheitsprüfung, Restoreprobe oder einen realen Zweiserver-Test.

Ein geplantes, vollständig webbasiertes Ratsinformationssystem für kommunale Verwaltung, Mandatsträger und Öffentlichkeit. Schwerpunkt sind eine verständliche Bedienung und die Schriftführung während der Sitzung. Das System soll auf Linux vollständig mit Docker Compose betreibbar sein und getrennte interne und externe Server unterstützen.

**Projektstand: Entwicklungsstand 0.7.** Implementiert sind Organisationen/Rechte, geschützter Datenaustausch, Vorlagen mit Freigaben, Sitzungsvorbereitung und PDF-Mappen, Live-Schriftführung und namentliche digitale Abstimmungen, Niederschriften, Beschlusskontrolle sowie persönlicher Arbeitsbereich mit verschlüsselter Offline-Vorbereitung und geprüftem Abgleich. Noch keine Produktivfreigabe. Umfang, Tests und offene Teilanforderungen stehen im [Implementierungsstand](docs/11-implementierungsstand.md).

## Start und Entwicklung

Für eine **geführte Erstinstallation** des vorhandenen Entwicklungsstands gibt es einen Bash-Assistenten:

```bash
bash setup.sh --stack internal          # interner Fachsystemhost
bash setup.sh --stack external          # getrennter externer Host
bash setup.sh --stack internal --check  # bestehende private .env prüfen, ohne Deployment
bash setup.sh --stack internal --initial-user-only  # erstes Konto nach unterbrochenem Setup nachholen
```

Der Assistent führt durch Domain-, SMTP-, Schlüssel- und optionale Backup-/Transferkonfiguration, initialisiert Datenbank und erstes Verwaltungskonto nur intern, startet die Compose-Dienste und prüft deren Bereitschaft. **Keine automatische Produktivfreigabe, kein unbeaufsichtigtes Upgrade und kein Restore.** Beide Stacks gehören auf getrennte Hosts. Details, Voraussetzungen und Sicherheitsgrenzen: [Geführte Erstinstallation](docs/12-installation.md#geführte-erstinstallation-bash-setup).

Die [Installationsanleitung](docs/12-installation.md) beschreibt zusätzlich die manuellen Einrichtungsschritte mit Docker Compose, SMTP und Caddys lokaler CA. Für Backendtests siehe [Entwicklung](docs/11-implementierungsstand.md#entwicklung). Änderungen erfolgen immer über einen Pull Request mit anschließendem Merge nach relevanten Prüfungen.

Für parallele Entwicklung ist GitHub die gemeinsame Steuerungsebene: **#41** enthält das dynamische Produkt-/Roadmap-Portfolio, **#38** aktive Agentenclaims und Kollisionssignale. Zielqualität, Roadmapvertrag und Gegenprüfung strittiger Entscheidungen stehen in docs/21–23.

## Ziel

Körperschaften verschiedener Ebenen – etwa Landkreis, Verbandsgemeinde, Ortsgemeinde und Zweckverband – arbeiten interoperabel mit gemeinsamen Stammdaten, eigenen Zuständigkeiten und sicher getrennten Zugriffsrechten. Eine Person verwendet ein Konto und wählt ihren Arbeitskontext ausdrücklich aus.

Von der Vorlage über Freigabe, Einladung und Tagesordnung bis zur Live-Sitzung, Niederschrift und Beschlusskontrolle wird der gesamte Ablauf unterstützt. Digitale Arbeit und Papierausgaben sind gleichberechtigte Wege. Einfache und erweiterte Bedienung verwenden dieselben Daten und Sicherheitsregeln.

Das langfristige Zielbild ist ein durchgängig verständliches, zugängliches, performantes, sicher entwickeltes und nachweisbar wiederherstellbares Produkt. „Implementiert“ ist dabei nicht gleich „freigabereif“: reale Fachanwender-, Geräte-, Sicherheits-, Accessibility-, Last- und Restore-Nachweise gehören zur Zielqualität.

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [Projektentscheidungen](docs/01-projektentscheidungen.md) | Bestätigte Vorgaben, Umfang, bewusste Abweichungen und offene Entscheidungen |
| [Anforderungen](docs/02-anforderungen.md) | Funktionaler Katalog mit stabilen Anforderungskennungen |
| [Organisation und Rechte](docs/03-organisation-rechte.md) | Mandanten, Datenmodell, Rollen, Vertraulichkeit und Veröffentlichung |
| [Fachliche Abläufe](docs/04-workflows.md) | Vorlagen, Sitzungen, Abstimmungen, Niederschriften und Beschlusskontrolle |
| [Bedienung und Gestaltung](docs/05-bedienkonzept.md) | Modi, Rollenansichten, CI, Geräte und Barrierefreiheitsplanung |
| [Architektur und Sicherheit](docs/06-architektur-sicherheit.md) | Zwei Server, Datenflüsse, Synchronisierung, Anmeldung und Vertrauensgrenzen |
| [Betrieb und Zertifikate](docs/07-betrieb.md) | Compose-Zielbild, Caddy, SMTP/IMAP, Backups, Updates und Aufbewahrung |
| [Spätere Module](docs/08-spaetere-module.md) | Aufnahme, Transkription, KI, Sitzungsgeld und vorbereitete Schnittstellen |
| [Abnahme und Umsetzung](docs/09-abnahme-umsetzung.md) | Prüfszenarien, Entwicklungsreihenfolge und Voraussetzungen des Livegangs |
| [Quellen und Klärungen](docs/10-quellen-offene-punkte.md) | Recherche, fachliche Grenzen und konkrete offene Fragen |
| [Implementierungsstand](docs/11-implementierungsstand.md) | Verfügbare Funktionen und noch offene Umsetzung |
| [Installation](docs/12-installation.md) | Docker-Start, Einrichtung und TLS-Vertrauen |
| [Konten und Rollen bedienen](docs/13-konten-rollen.md) | Einladungen, Gültigkeitszeiträume und Entzug |
| [Vorlagen und Rechte](docs/14-etappen-1-3.md) | Stammdaten, Vorlagen, Freigaben und Export |
| [Sitzungsvorbereitung](docs/15-sitzungsplanung.md) | Termine, Einladungen, Nachträge und PDF-Mappen |
| [Live-Sitzung](docs/16-live-sitzung.md) | Führerschaft, Anwesenheit und kontrollierte Rückgabe |
| [Abstimmungen](docs/16-live-sitzungsfuehrung.md) | Digitale Stimmen, Papierverfahren und Beschlüsse |
| [Niederschriften](docs/17-niederschrift.md) | Fassungen, Prüfung, Berichtigungen und öffentliche Freigabe |
| [Beschlusskontrolle](docs/18-beschlusskontrolle.md) | Zuständigkeit, Fristen und Sachstände |
| [Persönlicher Bereich und Offline](docs/19-mandatstraeger-offline.md) | Notizen, verschlüsselte Mappen und Offline-Schriftführung |
| [Etappenplan](docs/20-etappenplan.md) | Fachliche Grobfolge; aktuelle Priorisierung verweist auf die dynamische Roadmap |
| [Produktzielbild](docs/21-produkt-zielbild.md) | UX-/Frontend-, Security-, Accessibility-, Performance-, Betriebs- und Freigabeziele |
| [Dynamische Roadmap](docs/22-dynamische-roadmap.md) | Outcome-Portfolio, Horizonte, Prioritäten, Risiken, Qualitätsgates und WIP-Regeln |
| [Agenten-Council](docs/23-agenten-council.md) | Sichtbare Gegenprüfung strittiger Architektur-, UX- und Security-Entscheidungen |

## Schonungslose Bestandsaufnahme (Stand: 13. November 2026)

Diese Übersicht trennt **Code vorhanden**, **automatisiert geprüft** und **im Realbetrieb nachgewiesen**. Sie beruht auf dem Repository, den vorhandenen Tests/Workflows und der Dokumentation; sie ist **kein** unabhängiges Security- oder Fachgutachten.

| Bereich | Nachweisbarer Stand | Wesentliche Einschränkung |
|---|---|---|
| Fachliche Kernstrecke | Django-Modelle, Formulare und Views für Organisationen, Mandate, Vorlagen, Sitzungen, Einladungen, Beschlüsse, Niederschriften und Beschlusskontrolle | Der gesamte Ablauf wurde nicht mit realen kommunalen Fachanwendern verbindlich abgenommen |
| Rechte/Mandanten | Organisationsgebundene Kontexte, Rollen, Einladungen, getrennte interne/geschützte/öffentliche Dienste und entsprechende Tests | Rollenmatrix, Ausnahmesituationen und organisationsübergreifende Datenflüsse benötigen unabhängige Sicherheitsprüfung |
| Live-Sitzung | Implementierte Führerschaft, Journal, Anwesenheit und digitale namentliche Stimmabgabe | Digitale geheime Wahl/Abstimmung nicht produktiv vorhanden; keine rechtliche Gesamtzertifizierung |
| Dokumente | PDF/DOCX, Einladungsmappen, ICS, Vorlagen und Fassungen | Komplexe Typografie, PDF/UA, Signaturen, Druckqualität und rechtssichere Muster nicht vollständig nachgewiesen |
| Offline | Verschlüsselte lokale Vorbereitung und Konfliktbehandlung, automatisierte Chromium-Prüfung | Rechteentzug kann offline nicht sofort greifen; reale Endgeräte-/Browsermatrix und Sicherheitsreview fehlen |
| Integrationen | CSV-Importpipeline und kontrollierter interner/externer Austausch | Kein belegter vollständiger OParl-/DokuFIS- oder bidirektionaler more! rubin-Connector; CSV-Adapter ist in PR #142, noch nicht Teil von `main` |
| Branding/UI | Django-Templates, selbst gehostete Mantine-Assets, neue SVG-Bildmarke und CSS-Design-Tokens | Branding nicht mandantenweise administrierbar; keine fertige Logo-Uploadverwaltung, kein vollständiger UX-/Accessibility-Nachweis |
| Installation/Betrieb | Getrennte Compose-Dateien, Caddy, SMTP, Bootstrap-Assistent, Backup-Skripte und Smoke-Tests | Lokale CA statt automatisch öffentlichem ACME; kein unbeaufsichtigtes Upgrade, kein bestätigter isolierter Restore unter Realbedingungen |
| Qualität | GitHub Actions für Django (inkl. PostgreSQL/Rollen), Migrationen, Compose/Caddy/Imagebuild, JS/Node und Chromium | CI deckt nicht Penetration, Last, Ausfallsicherheit, Datenschutz-Folgenabschätzung, WCAG/BITV oder reale kommunale Freigaben ab |

### Konkrete technische Befunde

- Das Repository enthält eine **monolithische Django-Fachanwendung** mit lokal gebauten Mantine/JavaScript-Teilen, PostgreSQL und separaten externen Diensten. Die Architektur ist funktionsreich, aber entsprechend anspruchsvoll bei Schema-, Rechte- und Synchronisationsänderungen.
- Der geführte Installer ist **ausdrücklich nur für Erstinstallationen**. Er verhindert absichtsvoll gefährliche automatische Updates und Volume-Löschungen. Das ist ein Schutz, keine fertige Betriebsautomatisierung.
- Die GitHub-Workflowdatei `.github/workflows/checks.yml` enthält echte technische Prüfungen einschließlich PostgreSQL, Compose/Caddy und Browserautomation. Eine grüne Pipeline belegt jedoch nur die dort abgedeckten Fälle.
- Der öffentliche Dienst erhält freigegebene Projektionen; der externe Transfer ist ein zusätzlicher Vertrauens- und Betriebsbereich. Reale Netzsegmentierung, Zertifikatsvertrauen und Ende-zu-Ende-Übertragung sind gesondert zu prüfen.
- Es gibt **keine belastbare Aussage**, dass alle kommunalrechtlichen Sonderfälle, Geheimhaltung, Befangenheit, Vertretungen und Fristen vollständig fachlich geprüft sind.
- Die neue SVG-Bildmarke wird im Header und als Favicon verwendet. Die erzeugten alternativen Logoentwürfe sind **nicht** als auswählbare Assets oder Bildgenerator in die Anwendung integriert.
- README und andere Dokumente enthalten teils ältere Zielbildformulierungen. Maßgeblich für den tatsächlichen Stand sind implementierter Code, grüne Checks und dokumentierte Abnahmen, **nicht** die Zahl der beschriebenen Funktionen.

### Offene Pull Requests und Risiken

Zum Zeitpunkt dieser Bestandsaufnahme sind unter anderem [#141](https://github.com/derdigitalaffine/beschlussmanufaktur/pull/141) (Setup-Härtung; Backend-CI fehlgeschlagen) und [#142](https://github.com/derdigitalaffine/beschlussmanufaktur/pull/142) (more! rubin CSV-Adapter; noch nicht gemergt) offen. Die experimentellen Frontend-PRs [#73](https://github.com/derdigitalaffine/beschlussmanufaktur/pull/73) und [#74](https://github.com/derdigitalaffine/beschlussmanufaktur/pull/74) sind keine Produktionsfreigaben. Aktuelle Zustände immer auf GitHub nachprüfen.

### Prioritäten vor jeder Produktivfreigabe

1. **P0 – Betriebssicherheit:** Fehlerhafte CI-Läufe beheben; realen Zwei-Host-Test mit TLS, SMTP, Transfer, Berechtigungsentzug, Backup und isoliertem Restore dokumentieren.
2. **P0 – Fachrecht und Datenschutz:** kommunalrechtliche Fachabnahme der Einladungen, Quoren, Befangenheit, Vertretung, Beschlüsse und Niederschriften; Rollen-/Mandantentrennung extern prüfen; Datenschutzkonzept und Aufbewahrung festlegen.
3. **P0 – Sicherheit:** unabhängiger Pentest, Bedrohungsmodell, Secret-Rotation, Audit- und Vorfallprozesse, Wiederanlauf nach Fehlern und belastbare Lasttests.
4. **P1 – UX/Accessibility:** Tastatur-, Screenreader- und Mobiltests; durchgängige verständliche Fehlermeldungen und echte Anwenderstudien; barrierefreie Dokumente.
5. **P1 – Administration/Integrationen:** Mandantenbranding mit sicherem Upload, Importzuordnung und Dublettenprüfung; OParl-/DokuFIS-Verträge und more! rubin nur anhand realer Hersteller- oder Exportbelege umsetzen.
6. **P2 – Komfort:** Erweiterte Auswertungen, optionale KI und Audio erst nach verlässlichem Kernbetrieb.

**Freigabestatus: NEIN.** Es gibt weder einen dokumentierten vollständigen Abnahmenachweis noch eine Grundlage für die Aussage „100 % fertig“, „rechtskonform zertifiziert“ oder „produktionssicher“.

## Technischer Aufbau

- **Backend:** Python 3.12, Django, PostgreSQL; Templates und selbst gehostete JavaScript-/Mantine-Oberflächen.
- **Infrastruktur:** Linux, Docker Compose, Caddy, separate interne und externe Hosts, asynchrone Hintergrundaufgaben und private Dateivolumes.
- **Qualitätsprüfungen:** `.github/workflows/checks.yml` und die lokalen Django-/Node-/Browser-Smokes.
- **Schnittstellen:** kontrollierte Transferverträge und CSV-Import; OParl/DMS als noch zu belegende Ausbauziele.

Die Abschnitte [Implementierungsstand](docs/11-implementierungsstand.md), [Abnahme](docs/09-abnahme-umsetzung.md), [Betrieb](docs/07-betrieb.md) und [Installation](docs/12-installation.md) enthalten die fachlichen und technischen Details.

## Verbindlichkeit und Lizenz

`KERN` bezeichnet den vereinbarten ersten produktiven Umfang, `SPÄTER` eine ausdrücklich verschobene Umsetzung, `VORBEREITET` eine heute zu dokumentierende Erweiterungsgrenze. `VORSCHLAG` ist noch keine durch den Auftraggeber bestätigte Detailentscheidung. Nicht erprobte Architekturentscheidungen werden nicht als bereits sicher, rechtskonform oder einsatzfähig bezeichnet.

Lizenz: [MIT](LICENSE). Externe Abhängigkeiten, Modelle, Schriften und eingebundene Dienstleistungen sind getrennt auf ihre jeweiligen Bedingungen zu prüfen.
