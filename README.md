# Beschlussmanufaktur

Ein geplantes, vollständig webbasiertes Ratsinformationssystem für kommunale Verwaltung, Mandatsträger und Öffentlichkeit. Schwerpunkt sind eine verständliche Bedienung und die Schriftführung während der Sitzung. Das System soll auf Linux vollständig mit Docker Compose betreibbar sein und getrennte interne und externe Server unterstützen.

**Projektstand: Anforderungs- und Architekturplanung, 7. Oktober 2026.** Dieses Repository enthält ausschließlich Textdokumentation und die MIT-Lizenz. Es gibt noch keine Anwendung, Container, Compose-Dateien oder startfähige Installation. Die folgenden Aussagen beschreiben das zu entwickelnde Produkt.

## Ziel

Körperschaften verschiedener Ebenen – etwa Landkreis, Verbandsgemeinde, Ortsgemeinde und Zweckverband – arbeiten interoperabel mit gemeinsamen Stammdaten, eigenen Zuständigkeiten und sicher getrennten Zugriffsrechten. Eine Person verwendet ein Konto und wählt ihren Arbeitskontext ausdrücklich aus.

Von der Vorlage über Freigabe, Einladung und Tagesordnung bis zur Live-Sitzung, Niederschrift und Beschlusskontrolle wird der gesamte Ablauf unterstützt. Digitale Arbeit und Papierausgaben sind gleichberechtigte Wege. Einfache und erweiterte Bedienung verwenden dieselben Daten und Sicherheitsregeln.

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

## Erster produktiver Umfang

- Organisationen, Gremien, Personen, Legislaturperioden und flexible Rechte.
- Markdown-basierte Vorlagen im Webeditor, Zusammenarbeit und Freigaben.
- Sitzungsvorbereitung, kontrollierte Nachträge, Einladungen, PDF-Mappen und Druckpakete.
- Live-Schriftführung, Anwesenheit, Befangenheit, Beschlussfähigkeitsprüfung und digitale Abstimmungen einschließlich eines gesondert geprüften Entwurfs für geheime Abstimmungen/Wahlen.
- Offline-Schriftführung für ausdrücklich vorbereitete Sitzungen; digitale Stimmabgabe ausschließlich online.
- Niederschriften, Prüfung, Berichtigungen, Anträge und Beschlusskontrolle.
- Geschütztes Mandatsträgerportal und öffentliches Bürgerportal mit Suche.
- Administration, CI, Domains und TLS, E-Mail, lokale Dateispeicherung, Backup und Wiederherstellung.
- Einzelserverbetrieb und Trennung in internen und externen Server.

## Bewusst später

Aufnahme, Audioablage, Whisper/WhisperX, SpeechMind, KI-Protokollvorschläge und Sitzungsgeld werden erst nach dem übrigen Kern entwickelt. OParl und DMS werden vorbereitet. Vollständige Barrierefreiheitsumsetzung ist nicht Bestandteil des ersten Umfangs; ihre mögliche Bedeutung für einen realen öffentlichen Einsatz bleibt eine ausdrücklich zu klärende Freigabevoraussetzung.

Keine Migration aus Bestands-RIS, Bürgerkonten, Themenabonnements, Browser-Push oder verpflichtenden externen Analyse- und KI-Dienste. Keine kundenspezifischen Logos, Namen oder realen Personen im Auslieferungszustand. Wenige eindeutig gekennzeichnete, vollständig löschbare Testdaten werden vorgesehen.

## Technische Richtung

Bestätigt sind Python im Backend, Linux, Docker Compose, Caddy und administrierbare TLS-Zertifikate. Vorgeschlagen sind Django mit REST-API, PostgreSQL, ein React/TypeScript-Frontend und getrennte Hintergrundprozesse. Diese Komponenten sind Architekturvorschläge, noch keine festgelegten Versions- oder Paketlisten.

## Verbindlichkeit und Lizenz

`KERN` bezeichnet den vereinbarten ersten produktiven Umfang, `SPÄTER` eine ausdrücklich verschobene Umsetzung, `VORBEREITET` eine heute zu dokumentierende Erweiterungsgrenze. `VORSCHLAG` ist noch keine durch den Auftraggeber bestätigte Detailentscheidung. Nicht erprobte Architekturentscheidungen werden nicht als bereits sicher, rechtskonform oder einsatzfähig bezeichnet.

Lizenz: [MIT](LICENSE). Externe Abhängigkeiten, Modelle, Schriften und eingebundene Dienstleistungen sind getrennt auf ihre jeweiligen Bedingungen zu prüfen.
