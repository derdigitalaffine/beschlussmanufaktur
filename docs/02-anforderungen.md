# Anforderungskatalog

Alle Zeilen sind KERN, sofern nicht anders markiert. Optionale Funktionen gehören zum Kern, wenn sie hier als konfigurierbar beschrieben sind: „optional aktiviert“ bedeutet nicht „später implementiert“. Detailabläufe und Abnahmen stehen in den Folgedokumenten.

## Organisation und Identität

| ID | Anforderung |
|---|---|
| ORG-01 | Verwaltungsverbünde, Körperschaften mehrerer Ebenen, Gremien und Organisationseinheiten modellieren |
| ORG-02 | Primären Baum und zusätzliche Beziehungen mit Gültigkeitszeiträumen darstellen; Zyklen im Primärbaum verhindern |
| ORG-03 | Personen zentral, Funktionen/Kontaktdaten/Freigaben je Organisation führen; Dublettenprüfung bei Import |
| ORG-04 | Legislaturperioden, Amtszeiten, Besetzungen, Stellvertretungen und Fraktionswechsel historisieren |
| ORG-05 | Gemeinsame Räume, Vorlagenkonfigurationen und organisatorische Stammdaten mit geregelter Verantwortung |
| IAM-01 | Ein Konto pro Person, auswählbarer Kontext aus Organisation und Rolle; letzter Kontext wird nur bei weiter bestehender Berechtigung wiederhergestellt |
| IAM-02 | Rollen und Einzelrechte im einfachen beziehungsweise erweiterten Administrationsmodus |
| IAM-03 | Rechte nach Körperschaft, Gremium, Fachbereich, Vorgang, Sitzung, TOP und Anlage begrenzbar |
| IAM-04 | Einladungen per Mail, Adminanlage und Import; keine freie Selbstregistrierung |
| IAM-05 | E-Mail-Anmeldecode als Default; TOTP/Passkeys konfigurierbar; Wiederherstellung und Faktorenwechsel kontrollieren |
| IAM-06 | Befristete Zuweisungen automatisch beenden; Sitzungen/Tokens und lokale Synchronisierung entsprechend sperren |
| IAM-07 | Technische Administration ohne allgemeinen Inhaltszugriff; begründeten, zeitlich begrenzten Notfallzugriff protokollieren |

## Vorlagen und Zusammenarbeit

| ID | Anforderung |
|---|---|
| VOR-01 | Beschlussvorlagen, Mitteilungen, Anträge, Anfragen, Einwohnerfragen, Dringlichkeits-, Änderungs- und Tischvorlagen sowie frei definierte Arten |
| VOR-02 | Formatierter Webeditor mit Markdown-Quellansicht; Markdown als kanonischer Text, Zusatzdaten strukturiert |
| VOR-03 | Konfigurierbare Felder/Abschnitte/Pflichtfelder je Vorlagenart und Organisation |
| VOR-04 | Betreff, Sachverhalt, Begründung, Beschlussvorschlag, Zuständigkeit, Aktenzeichen, Finanzangaben, Anlagen und Beratungsfolge |
| VOR-05 | Fortlaufende Nummer je Körperschaft/Jahr bei interner Bereitstellung; transaktionssicher, keine Wiederverwendung |
| VOR-06 | Verknüpfung mit früheren Vorlagen, Anträgen und Beschlüssen |
| VOR-07 | Gleichzeitige Bearbeitung, Beteiligtenanzeige, Kommentare, Aufgaben, Benachrichtigungen, Versionen und Vergleiche |
| VOR-08 | SB → FBL → Sitzungsdienst im einfachen Modus; konfigurierbare parallele/bedingte Freigaben und Vertretungen erweitert |
| VOR-09 | Einzelne Nutzer händisch zum Workflow hinzufügen; zusätzliche Beteiligung erteilt nicht automatisch uneingeschränkten Inhaltzugriff |
| VOR-10 | Freigaben versionsgebunden; fachliche Änderungen lösen erneute Prüfung aus |
| VOR-11 | Beratungsfolge über Körperschaftsgrenzen mit eigenen Beschlüssen; lokale Ergänzungen/Änderungen nur bei eingeräumtem Recht |

## Sitzungsvorbereitung und Dokumente

| ID | Anforderung |
|---|---|
| SIT-01 | Kalender, Räume, Gremium, Vorsitz, Schriftführung, öffentliche/nichtöffentliche Abschnitte und Fristen verwalten |
| SIT-02 | TO-Vorschläge, Reihenfolge, Unter-/Sammelpunkte, Zeitplanung und Zusammenarbeit von Sitzungsdienst/Vorsitz |
| SIT-03 | Fristen je Regelprofil/Organisation einstellen; Ausnahmen nur mit Berechtigung, Grund und nötigen Beschlüssen |
| SIT-04 | Personalisierte Einladung, E-Mail, Portalhinweis, Kalenderdatei, PDF-Gesamtmappe und Druckpaket |
| SIT-05 | Versandstatus, optional Empfang/ Kenntnisnahme erfassen; technische Zustellung nicht als rechtlichen Zugang behaupten |
| SIT-06 | Versandten Einladungsstand unveränderlich halten; kontrollierte Nachträge und Änderungsanzeigen |
| SIT-07 | Empfängerbezogene PDF-Pakete mit Inhaltsverzeichnis, Seitennummerierung und verlässlicher Auswahl zulässiger Anlagen |
| SIT-08 | Einladung, Vorlagen, Anwesenheitsliste, Schriftführungsunterlagen, Niederschrift und Beschlussauszug druckbar |
| SIT-09 | DOCX-Export aus systemeigenen Layouts, ohne Voraussetzung nutzereigener Wordvorlagen |

## Live-Sitzung und Abstimmung

| ID | Anforderung |
|---|---|
| LIVE-01 | Eine aktive Schriftführung; Vorsitzansicht mit kontrollierter Übernahme und optionalem Saalbildschirm |
| LIVE-02 | Beginn/Ende, TOP-Wechsel, Pausen, Eintritt/Austritt, Anträge, Beschlüsse und Abstimmungen protokollieren |
| LIVE-03 | Anwesenheit vorab und live durch Schriftführung/Vorsitz, keine Selbstanmeldung; Uhrzeit und TOP-Bezug |
| LIVE-04 | Befangenheit gesondert feststellen; Auswirkungen auf Beratung/Abstimmung dokumentieren |
| LIVE-05 | Beschlussfähigkeit aus Regelprofil und aktuellem Stand berechnen, Änderungen anzeigen; Vorsitz bestätigt Feststellung |
| LIVE-06 | Änderungs-/Geschäftsordnungsanträge, alternative Beschlussfassungen und Abstimmungsreihenfolge erfassen |
| LIVE-07 | Manuelle und optional aktivierbare digitale Abstimmung; Ja/Nein/Enthaltung, namentlich, geheim, Wahlen/mehrere Wahlgänge |
| LIVE-08 | Berechtigte Teilnehmer je Abstimmung fixieren/prüfen, genau eine wirksame Stimme, verbindlichen Wortlaut/Mehrheit speichern |
| LIVE-09 | Digitale Abstimmung online; bei Fehler dokumentierter Abbruch und vollständiger manueller Neudurchlauf |
| LIVE-10 | Offline-Schriftführung vorbereiteter Sitzungen: Text, Ereignisse, Anwesenheit und manuelle Ergebnisse; nachvollziehbare Konfliktlösung |
| LIVE-11 | Ergebnisse und Beschlüsse nicht aus fehlenden Stimmen oder KI-Ausgaben erraten |

## Niederschrift und Folgevorgänge

| ID | Anforderung |
|---|---|
| PRO-01 | Ergebnis-, Verlaufs- und Wortprotokoll je Gremium wählbar; ohne spätere Audiomodule manuell bearbeitbar |
| PRO-02 | Entwurf aus strukturierten Sitzungsdaten und Notizen, einschließlich Anträgen, Anwesenheit, Ergebnissen und Befangenheit |
| PRO-03 | Schriftführung prüft, danach Vorsitz; nachträgliche Einwendungen/Berichtigungen mit Bezug zur nächsten Sitzung |
| PRO-04 | Interne und öffentliche Fassungen getrennt freigeben; Historie und Beschlussauszüge erhalten |
| BES-01 | Umsetzungspflicht je Beschluss entscheiden, keine automatische Aufgabe für jede Kenntnisnahme |
| BES-02 | Zuständige Stelle/Person, Zieltermin, Fortschritt und Erledigungsbestätigung |
| BES-03 | Einfach: offen/in Bearbeitung/erledigt; erweitert: wartet auf Dritte/teilweise umgesetzt, Teilaufgaben und Nachweise |
| BES-04 | Aussetzung/Aufhebung als Beschlussereignis getrennt von Aufgabenstatus; Grund und Folgebeschluss verknüpfen |
| BES-05 | Erinnerungen, Wiedervorlage, Überfälligkeitsübersicht und Sitzungsberichte |
| BES-06 | Freigegebener Sachstand für zuständiges Gremium; öffentlicher Kurzbericht nur ausdrücklich veröffentlicht |
| ANT-01 | Anträge/Anfragen vom Eingang bis Antwort/Beratung/Abschluss mit Zuweisung und Fristen verfolgen |

## Portale, Veröffentlichung und Suche

| ID | Anforderung |
|---|---|
| POR-01 | Mandatsträger: Kalender, Einladungen, Unterlagen, PDF-Mappen, Änderungen, Notizen, Aufgaben, Anträge und Abstimmungen |
| POR-02 | Fraktionen einfach als Mitgliedschaft, erweitert mit geschütztem Arbeitsbereich, Dokumenten, geteilten Notizen und Terminen |
| POR-03 | Bürgerportal ohne Login: Organisationsbaum, Kalender, Gremien, Mitglieder, öffentliche Unterlagen und Volltextsuche |
| POR-04 | Öffentliche Personendaten einzeln konfigurierbar: Name, Funktion, Fraktion, Amtszeit; Foto/Kontakte gesondert freigeben |
| POR-05 | Gemeinsames Portal und Teilportale mit eigenen Domains/CI, Körperschaften in mehreren Portalen |
| POR-06 | Suche nach Organisation/Gremium/Termin/Thema/Art/Status, Volltext in Texten und PDFs; Rechte vor Trefferausgabe durchsetzen |
| PUB-01 | Öffentlich vorgesehen ist nicht veröffentlicht; aktive Freigabe konkreter Version, optional Vieraugenprinzip, Zeitplanung und Vorschau |
| PUB-02 | Anlage, TOP, Vorlage, Beschluss und Niederschrift separat einstufbar; öffentliche Ausgabe über Positivliste |
| PUB-03 | Wirksam geschwärzte Ausgabe ohne versteckten Originaltext/Metadaten; Original bleibt geschützt |
| PUB-04 | Rücknahme mit zentralem Status, Cachebereinigung und Warnung bei noch ausstehender Übertragung |
| INT-01 | Pflicht-E-Mail über SMTP, IMAP-Anbindung berücksichtigen, ein gemeinsamer Absender; Systemhinweise und E-Mail-Digests |
| INT-02 | Kalenderdateien/-abos und portable Datenexporte; Rechte auch für Abonnementlinks prüfen |
| INT-03 | Bürgerportal und einzelne öffentliche Ansichten per iframe für freigegebene Domains |
| INT-04 | OParl-Datenzuordnung und Versionsgrenze VORBEREITET; DMS-Adapter VORBEREITET |

## Querschnitt

| ID | Anforderung |
|---|---|
| OPS-01 | Vollständiger Kernbetrieb via Docker Compose, Einzelserver und intern/extern, keine Kubernetes-Pflicht |
| OPS-02 | Caddy, TLS-Administration, lokale CA, Let's Encrypt, DNS-Prüfung und Zertifikatimport |
| OPS-03 | Lokale persistente Dateien, getrennte Schutzbereiche, austauschbarer Speicheradapter |
| OPS-04 | Systemzustand, Jobs, Mail, Sync, Speicher und Zertifikate im Adminbereich; Fehlermeldungen an Admingruppe |
| OPS-05 | Tägliches und Vorupdate-Backup, verschlüsseltes getrenntes Ziel, Wiederherstellung und dokumentierter Update-Rückweg |
| OPS-06 | Markierte minimale Testdaten mit gezielter vollständiger Entfernung; keine Standardpasswörter |
| SEC-01 | Serverseitige, standardmäßig verweigernde Rechteprüfung an jedem Zugriffsweg; restriktive Dienstidentitäten |
| SEC-02 | Fachliche Änderungen, Rechte, Veröffentlichungen, Notfallzugriffe und Zugriff auf besonders geschützte Inhalte protokollieren |
| UX-01 | Ruhige Gestaltung, Rollenstartseite, Suche, Favoriten und zuletzt verwendete Vorgänge |
| UX-02 | CI für Portale und PDF/DOCX; neutrale Auslieferung; Windows/Linux, Chrome/Firefox, iPad/Tablet/Telefon |
| UX-03 | Barrierefreiheitsanforderungen planen, Umsetzung SPÄTER; keine Zusicherung fertiger Konformität |
