# Projektentscheidungen und Umfang

Stand: 2026-10-07. Grundlage ist das mehrteilige Anforderungsinterview. Die Dokumentation bleibt organisationsneutral; das Mengengerüst ist ein Planungsfall, keine ausgelieferte Personalisierung.

## Bestätigte Leitentscheidungen

| ID | Entscheidung |
|---|---|
| E-01 | Kommunales Open-Source-RIS, MIT-Lizenz, deutsche Dokumentation und Oberfläche |
| E-02 | RLP zuerst; andere Bundesländer und Körperschaftsarten über Regelprofile anpassbar |
| E-03 | Mehrmandantenfähigkeit kombiniert mit Verwaltungsverbünden und eigenständigen Körperschaften |
| E-04 | Organisationsbaum als Hauptdarstellung, zusätzliche Mehrfachzuordnungen |
| E-05 | Gemeinsame Personen/Stammdaten, organisationsbezogene Funktionen, Kontaktdaten und Sichtbarkeit |
| E-06 | Ein Konto pro Person, ausdrücklich wählbarer und deutlich sichtbarer Arbeitskontext; letzten Kontext merken |
| E-07 | Einfacher und erweiterter Modus überall, wo sinnvoll; keine Abschwächung von Sicherheitsregeln |
| E-08 | Webeditor mit Markdown als Textformat, strukturierte Zusatzdaten, PDF-/DOCX-Export; keine Wordvorlagen |
| E-09 | Vorlagennummer je Körperschaft/Jahr bei verbindlicher interner Bereitstellung nach Freigabe |
| E-10 | Digitale und papierbasierte Sitzungsarbeit, Offline-Mappen als Gesamt-PDF |
| E-11 | Live-Schriftführung, Vorsitzansicht mit Übernahme, Ereignisse und Anwesenheit mit Uhrzeit/TOP |
| E-12 | Befangenheit gesondert feststellen und dokumentieren; kein automatischer Dokumentzugriffsentzug allein deshalb |
| E-13 | Digitale Abstimmungen ab dem ersten produktiven Umfang; Saalbildschirm optional |
| E-14 | Aufnahme, Transkription, KI und Sitzungsgeld ausdrücklich später, mit dokumentierten Modulgrenzen |
| E-15 | Sitzungsaudio niemals öffentlich; externe Verarbeitungsmodule nur ausdrücklich aktivieren |
| E-16 | Niederschrift zuerst Schriftführung, dann Vorsitz; spätere Einwendungen/Berichtigungen abbilden |
| E-17 | Öffentliches Portal nur Einsicht, keine Bürgerkonten oder Themenabonnements |
| E-18 | Ein gemeinsames und zusätzlich abgegrenzte Portale mit eigenen Domains/CI und zentralen Veröffentlichungsdaten |
| E-19 | E-Mail verpflichtend, keine Browser-Push-Benachrichtigungen; Kalender und Datenexport im Kern |
| E-20 | Linux/Docker Compose; ein Server oder zwei Server intern/extern; Caddy verbindlich |
| E-21 | Verwaltung nur intern, VPN außerhalb der Anwendung; Schriftführung und Mandatsträger auch über geschützten externen Dienst |
| E-22 | Interner Server initiiert Übertragung und Abholung; Gegenrichtung nur als ausdrücklich genehmigte Ausnahme |
| E-23 | Nichtöffentliche Daten dürfen im geschützten externen Dienst gespeichert werden |
| E-24 | Eigene Konten; E-Mail-Code als Standard auch für Administration, TOTP und Passkeys konfigurierbar |
| E-25 | Konten durch Administration, Einladung und Import; keine Selbstregistrierung; automatisches Ende von Zugriffszuweisungen |
| E-26 | Caddy-interne CA zur Erstinbetriebnahme; Wechsel zu Let's Encrypt oder hochgeladenen Zertifikaten in Administration |
| E-27 | Domains/Zertifikate administrierbar, automatische DNS-Prüfung; Internet für Images, Updates und Zertifikate erlaubt |
| E-28 | SMTP/IMAP vorhanden, ein gemeinsamer Absender; lokale Dateispeicherung zunächst |
| E-29 | Kontrollierte Updates mit Backup und Rückweg; keine dauerhaft getrennte Testinstallation |
| E-30 | Wenige markierte Testdaten im Defaultsystem; ein Löschvorgang entfernt nur diese |
| E-31 | Keine more-RUBIN-Migration, keine Pflichttelemetrie, keine kostenpflichtigen Pflichtdienste im Kern |
| E-32 | Barrierefreiheit vorsehen, vollständige Umsetzung später; keine Konformitätsbehauptung |

## Mengengerüst

Eine VG, zwölf Ortsgemeinden und weitere Verbände, etwa 19.000 Einwohner, 200–250 Mandatsträger, 120 Verwaltungsnutzer und 150 Sitzungen jährlich. Gleichzeitige Nutzer, maximale Sitzungsgröße, Dokumentvolumen und langfristiger Datenzuwachs müssen vor Dimensionierung gemessen beziehungsweise vereinbart werden. Einwohnerzahl ist keine Gleichzeitigkeitsschätzung.

## Zielqualität

Die Beteiligten sollen gern mit dem System arbeiten: geringe Einarbeitung, schnelle Routinewege, verständliche Rechte, zuverlässiges Speichern, gut lesbare Dokumente und eine Schriftführung, die Nacharbeit reduziert. Dies wird durch praktische Abnahme statt allein durch Funktionslisten geprüft.

## Umfangsänderung aus dem Interview

Die anfängliche Forderung „alles vor dem Livegang“ gilt für den später ausdrücklich abgegrenzten Kernumfang. Aufnahme/Transkription, KI und Sitzungsgeld sind keine Livegangblocker. Digitale Abstimmungen wurden ausdrücklich im Kern belassen. OParl ist vorbereitet, nicht zum Start vollständig implementiert. Die gesamte vereinbarte Kernfunktionalität muss dagegen fertig und geprüft sein.

## Bewusste Abweichungen und Grenzen

- E-Mail-Codes auch für Administration sind eine bestätigte Komfortentscheidung. Die Empfehlung, privilegierte Rollen mit TOTP/Passkeys abzusichern, bleibt dokumentiert; keine NIST-Konformität zusagen.
- Keine permanente Testinstallation beim Betreiber. Automatisierte Entwicklungstests und eine temporäre Wiederherstellungsprüfung bleiben notwendig und sind davon verschieden.
- Keine vollständige Barrierefreiheitsumsetzung in Phase 1. Ob dies einen konkreten öffentlichen Livegang verhindert, ist fachlich/rechtlich zu prüfen, nicht durch diese Dokumentation entschieden.
- Das Ziel „ASAP“ enthält keinen bestätigten Termin und keine Freigabe, Sicherheits- oder Fachprüfungen auszulassen.
- Interoperabilität bedeutet keine automatische Rechtevererbung zwischen verbundenen Körperschaften.

## Technische Vorschläge

Modularer Python-Monolith je Anwendungskontext, Django/REST, PostgreSQL, React/TypeScript, lokaler Dateispeicher und getrennte Hintergrundprozesse. Öffentlicher und geschützter externer Dienst erhalten getrennte Datenbanken, Speicher und Dienstidentitäten. Keine Kubernetes-Pflicht und keine Aufteilung jedes Fachmoduls in einen eigenen Service.

Details zur Synchronisierung und Sitzungsführerschaft sind begründete Architekturvorschläge. Sie müssen vor Implementierung gegen Live-Abstimmung, Offlinekonflikte und Entzug von Rechten validiert werden.
