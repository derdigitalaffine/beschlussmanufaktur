# Produktzielbild: Beschlussmanufaktur

Status: **Zielbild / Qualitätsvertrag**, keine Behauptung bereits erreichter Produktivqualität.

Dieses Dokument beschreibt, woran die Beschlussmanufaktur langfristig gemessen wird. Fachliche KERN-Anforderungen aus README und docs/01–20 bleiben verbindlich. Wo dieses Zielbild höhere Qualitätsansprüche formuliert, sind sie zusätzliche Ziel- und Freigabekriterien; sie dürfen nicht als bereits erfüllt dargestellt werden, solange Nachweise fehlen.

## 1. Nordstern

Die Beschlussmanufaktur soll kommunale Gremienarbeit vom ersten Entwurf bis zur veröffentlichten Entscheidung so unterstützen, dass Menschen **schneller, sicherer und mit weniger kognitiver Last** arbeiten als mit einer Sammlung aus Office-Dateien, E-Mail, Papierlisten und getrennten Portalen.

Das Produktziel ist nicht „viele Funktionen“, sondern ein durchgängiger Arbeitsfluss mit fünf Eigenschaften:

1. **verständlich:** Nutzer erkennen jederzeit Kontext, Zustand, nächste sinnvolle Aktion und Folgen einer Entscheidung;
2. **sicher:** Rechte, Vertraulichkeit und Vertrauensgrenzen werden serverseitig durchgesetzt und systematisch geprüft;
3. **robust:** Unterbrechungen, Wiederholungen, Offlinephasen und Wiederherstellung führen nicht zu stiller Datenkorruption;
4. **zugänglich:** Kernaufgaben sind mit Tastatur, Screenreader, vergrößerter Darstellung und auf unterschiedlichen Gerätegrößen nutzbar;
5. **vertrauenswürdig:** kritische Fachentscheidungen, Änderungen und Übernahmen bleiben nachvollziehbar, ohne Nutzer mit technischen Details zu überfordern.

## 2. Produktflächen

### 2.1 Interne Verwaltung

Ziel ist ein ruhiger Arbeitsraum für hohe Vorgangsdichte. Startseiten priorisieren Aufgaben statt Module: offene Freigaben, nächste Sitzungen, Fristen, Änderungen, Rückläufer und zuletzt bearbeitete Vorgänge. Der aktive Organisations- und Rollenkontext ist dauerhaft sichtbar.

Routinearbeit soll überwiegend mit wenigen stabilen Mustern auskommen: suchen/filtern, Datensatz öffnen, bearbeiten, prüfen, freigeben, versenden/veröffentlichen. Erweiterte Regeln bleiben erreichbar, dominieren aber nicht die Standardansicht.

### 2.2 Geschützter externer Bereich

Mandatsträger, Schriftführung und Vorsitz sehen zuerst das, was für ihre nächste Handlung relevant ist: Sitzungen, geänderte Unterlagen, Aufgaben, Notizen, Abstimmungen und Synczustand. Sicherheitszustände wie abgelaufene Berechtigung, veralteter Offlinebestand oder verlorene Sitzungshoheit werden unmissverständlich angezeigt.

### 2.3 Öffentliches Bürgerportal

Das Bürgerportal ist kein Nebenprodukt der Verwaltungsoberfläche. Es erhält eine eigenständige, reduzierte Informationsarchitektur: aktuelle und vergangene Sitzungen, verständliche Tagesordnungen/Beschlüsse, Suche, Kalender, Gremien/Personen und freigegebene Dokumente. Es zeigt ausschließlich veröffentlichte Projektionen; interne Fachzustände und vertrauliche Metadaten dürfen nicht durchsickern.

## 3. UX-Prinzipien

### 3.1 Aufgaben vor Datenmodell

Navigation und Seitenaufbau folgen Nutzerabsichten („Sitzung vorbereiten“, „Vorlage prüfen“, „Beschluss nachverfolgen“) statt internen Tabellen oder Klassen. Fachbegriffe bleiben dort erhalten, wo sie rechtlich/organisatorisch nötig sind.

### 3.2 Ein primärer nächster Schritt

Eine Ansicht soll nach Möglichkeit genau eine visuell dominante Hauptaktion besitzen. Destruktive, rechtlich relevante oder veröffentlichende Aktionen werden nicht mit gewöhnlicher Navigation verwechselt.

### 3.3 Progressive Offenlegung

Der einfache Modus zeigt die häufigste sichere Entscheidung. Erweiterte Konfiguration wird kontextbezogen geöffnet. Komplexität wird erklärt, nicht nur versteckt: wirksame erweiterte Regeln müssen im einfachen Modus als verständliche Zusammenfassung sichtbar bleiben.

### 3.4 Zustand statt Überraschung

Laden, Speichern, Übertragen, Freigeben, Synchronisieren, Konflikte und Fehler haben sichtbare Zustände. Keine stille Erfolgsmeldung, wenn nur lokal gespeichert wurde; keine stille Rechteausweitung bei ungültigem Kontext; keine automatische Übernahme fachkritischer Konflikte.

### 3.5 Reversibilität

Wo fachlich zulässig, erhalten Nutzer Vorschau, Rückweg oder bestätigbaren Entwurf. Unumkehrbare Aktionen erklären Wirkung und Reichweite. Bestätigungsdialoge werden nur für echte Risiken verwendet, nicht als generelle Klickbremse.

### 3.6 Kein Sicherheits-Theater

Sicherheitsfunktionen müssen echte Risiken reduzieren. Wiederholte Warnungen, die Nutzer routinemäßig wegklicken, gelten als UX- und Sicherheitsfehler. Kritische Hinweise nennen konkrete Wirkung und sichere Alternative.

## 4. Informationsarchitektur

Die primäre Struktur soll domänenübergreifend konsistent sein:

- **Heute / Meine Arbeit:** Aufgaben, Fristen, nächste Sitzungen, Änderungen;
- **Vorlagen & Vorgänge:** Erstellung, Zusammenarbeit, Prüfung, Freigabe;
- **Sitzungen:** Planung, Einladung, Unterlagen, Livebetrieb, Niederschrift;
- **Beschlüsse:** Beschlüsse, Aufgaben, Sachstände, Wiedervorlagen;
- **Organisation:** Gremien, Personen, Mandate, Rollen und Zeiträume;
- **Veröffentlichung:** öffentliche Fassungen, Portalzustand, Rücknahmen;
- **Administration:** Konfiguration, Integrationen, Betrieb und Diagnose entsprechend Berechtigung.

Globale Suche ist rechte- und kontextsensitiv. Filterzustände sind verständlich und nach Möglichkeit teilbar/wiederherstellbar, ohne geheime Informationen in URLs zu schreiben.

## 5. Frontend-Zielqualität

### 5.1 Designsystem

Alle Produktflächen verwenden ein gemeinsames Designsystem mit Tokens für Typografie, Abstände, Radien, Schatten, Zustände und CI-Farben. Komponenten werden nach Verhalten und Semantik definiert, nicht als seitenlokale CSS-Kopien.

Pflichtbausteine sind mindestens: App-Shell, Kontextwechsler, Breadcrumb/Seitentitel, Tabs, Tabellen/Listen, Filter, Suche, Formfelder, Rich-/Markdown-Editorrahmen, Status/Badges, Callouts, Dialog/Drawer, Toast nur für flüchtige Bestätigung, leere Zustände, Skeleton/Loading, Pagination, Dateiliste, Timeline/Auditdarstellung und responsive Aktionsleisten.

### 5.2 Responsive Strategie

Desktop/Laptop optimiert Informationsdichte und parallele Sicht. Tablet priorisiert große Touchziele und umschaltbare Arbeitsbereiche. Telefon unterstützt Lesen, Suchen, einfache Freigaben und Kernaktionen; hochkomplexe Schriftführungsarbeit darf auf kleinen Displays bewusst reduziert werden, ohne Daten zu verstecken oder falsche Gleichwertigkeit zu behaupten.

### 5.3 Schriftführungsarbeitsplatz

Der Live-Arbeitsplatz ist ein eigenes Hochleistungs-Interface:

- Laptop: Tagesordnung links, aktiver TOP/Dokumentation zentral, Anwesenheit/Ereignisse rechts;
- Tablet: dieselben mentalen Bereiche als schnell wechselbare Panels;
- Sitzungshoheit, Onlinezustand, Sync, aktueller TOP, Beschlussfähigkeit und aktives Abstimmungsverfahren bleiben sichtbar;
- Kernaktionen sind mit Tastatur und Touch erreichbar;
- konkurrierende Aktionen werden gegen Doppel- oder Mehrfachauslösung geschützt;
- Ereignisse besitzen nachvollziehbare Zeit-/Statusdarstellung, ohne die Hauptaufgabe zu überfrachten.

### 5.4 Formulare

Formulare verwenden konsistente Labels, Hilfetexte, Pflichtkennzeichnung und Fehlerpositionierung. Serverseitige Fehler erscheinen am betroffenen Feld und in einer fokussierbaren Fehlerzusammenfassung. Ungespeicherte Änderungen werden bei riskanter Navigation geschützt. Lange Formulare werden nach Fachabschnitten strukturiert, nicht nach Datenbankmodellen.

### 5.5 Tabellen und dichte Arbeitslisten

Tabellen werden nur verwendet, wenn Spaltenvergleich wichtig ist. Auf schmalen Screens wechseln sie in Karten/Listen oder horizontale, klar gekennzeichnete Ansichten. Sortierung, Filter, Auswahl und Bulk-Aktionen bleiben tastaturbedienbar. Status wird nie ausschließlich über Farbe vermittelt.

## 6. Barrierefreiheit als Produktqualität

Zielqualität für vom Produkt kontrollierte Weboberflächen ist **WCAG 2.2 Level AA**, soweit keine dokumentierte fachlich-rechtliche Entscheidung strengere Anforderungen verlangt. Das ist ein Entwicklungsziel, keine automatische Konformitätszusage.

Mindestens erforderlich:

- semantische Landmarken und Überschriftenstruktur;
- vollständige Tastaturbedienbarkeit ohne Fokusfallen;
- sichtbarer Fokus und logische Fokusführung nach Navigation/Fehler/Dialogen;
- Screenreader-taugliche Namen, Zustände und Live-Updates;
- Zoom/Reflow ohne Verlust wesentlicher Funktion;
- ausreichende Kontraste und nicht-farbliche Statuscodierung;
- respektierte `prefers-reduced-motion`-Einstellung;
- verständliche Fehlermeldungen und Eingabehilfen;
- barrierearme Dokumentausgaben als gesondertes Qualitätsziel.

Automatisierte Accessibility-Checks sind Mindestnetz; reale Tastatur-, Screenreader- und Zoomtests bleiben erforderlich.

## 7. Performance und wahrgenommene Geschwindigkeit

Performance wird pro Oberfläche gemessen, nicht nur durch Backend-Testlaufzeit.

Für öffentliches Portal und gewöhnliche Navigation gilt als initiales Webziel unter einem vereinbarten Referenzprofil: gute Core-Web-Vitals-Grenzen (LCP höchstens 2,5 s, INP höchstens 200 ms, CLS höchstens 0,1 am 75. Perzentil). Für interne Hochleistungsansichten werden zusätzlich fachliche Budgets vereinbart, z. B. Such-/Filterreaktion, Öffnen eines Vorgangs und Live-Aktionsbestätigung.

Weitere Prinzipien:

- keine externen Tracker/CDNs im Standardprodukt;
- JavaScript nur, wo es Interaktion verbessert; progressive serverseitige Grundfunktion bevorzugen, wenn fachlich sinnvoll;
- Lazy Loading für schwere Sekundärinhalte, nicht für unmittelbar benötigte Kerninformationen;
- keine unkontrolliert wachsenden DOM-Listen oder mehrfachen API-Abfragen pro Zeile;
- Performance-Regressions werden wie Funktionsregressions behandelt.

## 8. Frontend-Architekturentscheidung

Das Zielbild schreibt **nicht** vor, dass React automatisch besser ist. Die heutige Django-Template-/JavaScript-Architektur bleibt gültig, bis eine dokumentierte Entscheidung anhand realer Prototypen anderes zeigt.

Eine mögliche Umstellung oder Hybridarchitektur darf nur erfolgen, wenn sie messbar verbessert:

- Konsistenz komplexer UI-Zustände;
- Testbarkeit;
- Accessibility;
- Live-/Offline-Interaktion;
- Entwicklungs- und Wartungsgeschwindigkeit;

und dabei nicht unverhältnismäßig verschlechtert:

- CSP/Supply-Chain-Angriffsfläche;
- Ladevolumen;
- Server-/Client-Vertragskomplexität;
- Fähigkeit zu schrittweisen Releases;
- Betriebs- und Debuggingaufwand.

Vor einer großen Migration ist ein repräsentativer vertikaler Prototyp Pflicht.

## 9. Sicherheitszielbild

„Perfekt sicher“ ist kein belastbares Freigabeversprechen. Ziel ist stattdessen ein **nachweisbar sicher entwickeltes System mit Defense-in-depth und dokumentiertem Restrisiko**.

### 9.1 Sicherheitsgrundsätze

- deny-by-default für Fachrechte;
- Kontext, Organisation, Objekt und zeitliche Zuweisung serverseitig auf jeder geschützten Aktion prüfen;
- getrennte Vertrauensbereiche für intern, geschützt extern und öffentlich;
- keine außen initiierte allgemeine Verbindung in das interne Netz;
- minimale Dienstrechte und getrennte Secrets;
- sichere Standardwerte vor Konfigurationskomfort;
- vertrauliche Daten nicht in Logs, URLs, E-Mail-Betreff/Body oder öffentliche Suchindizes leaken;
- jede Datei, jeder Export und jeder Hintergrundjob unterliegt denselben Fachrechten wie die direkte Ansicht.

### 9.2 Verifikation

Sicherheitsanforderungen werden gegen einen aktuellen, dokumentierten Prüfkatalog wie OWASP ASVS gespiegelt. Für produktionskritische Flächen entsteht eine Traceability von Risiko → Kontrolle → automatisierter/manueller Test → Evidenz.

Pflichtprüfungen vor Produktivfreigabe:

- Threat Model je Vertrauensgrenze und Hochrisiko-Workflow;
- Missbrauchs-/Negativtests für IDOR/BOLA, Rechte, CSRF, XSS, Injection, Session/Logout, Uploads, SSRF und Ressourcenmissbrauch;
- Dependency-/Supply-Chain-Prüfung und reproduzierbare Abhängigkeitsaktualisierung;
- Secret Scanning und keine geheimen Werte im Frontendbuild;
- Backup-/Restore- und Schlüsselwechseltest;
- gezielte unabhängige Prüfung geheimer digitaler Abstimmungen, bevor diese Funktion überhaupt als sicher verfügbar gilt.

Offene P0-Sicherheitsrisiken blockieren die Produktivfreigabe. P1-Risiken benötigen eine dokumentierte Entscheidung mit zeitgebundener Abhilfe; reine Akzeptanz aus Zeitdruck ist kein Standardweg.

## 10. Datenschutz und Datenminimierung

Jede neue Funktion beantwortet vor Umsetzung:

1. Welche personenbezogenen/vertraulichen Daten benötigt sie wirklich?
2. In welchem Vertrauensbereich liegen diese Daten?
3. Wer darf sie sehen/verändern/exportieren?
4. Wie lange werden sie benötigt?
5. Wie werden Löschung, Widerruf, Korrektur und Audit voneinander getrennt?
6. Welche Metadaten könnten über Suche, Zähler, Dateinamen oder Fehler indirekt Informationen verraten?

Telemetry ist standardmäßig lokal/minimal und darf keine heimliche Nutzerprofilierung einführen.

## 11. Zuverlässigkeit und Betrieb

Produktionsreife bedeutet nachweisbare Wiederherstellbarkeit, nicht nur erfolgreiche Starts.

Zielzustand:

- idempotente/wiederholbare Übertragungen;
- sichtbare Queue-/Synczustände und begrenzte Wiederholungen;
- Healthchecks unterscheiden Prozess lebt vs. fachliche Abhängigkeiten funktionieren;
- Backups werden automatisiert erstellt und regelmäßig real wiederhergestellt;
- Restore umfasst Datenbank, Dateien, relevante Schlüssel/Metadaten und ausstehende Ereignisse;
- Updates besitzen Migrations- und Rückwegplan;
- Ressourcenlimits und kontrollierte Fehler bei Speicher-/Datei-/Exportlast;
- Adminhinweise sind handlungsorientiert und verraten keine Secrets.

RPO/RTO und Lastziele werden mit realen Betriebsanforderungen vereinbart; ungeprüfte SLA-Zahlen werden nicht erfunden.

## 12. Qualitätsgates

Ein Roadmap-Outcome gilt nicht als „fertig“, nur weil Code gemergt ist. Je nach Risiko sind folgende Gates relevant:

### G0 – Problem verstanden
- Nutzerproblem/Outcome beschrieben;
- bestehende Fähigkeit und Wiederverwendung geprüft;
- Risiken und Nicht-Ziele dokumentiert.

### G1 – Lösung entschieden
- UX-/Architekturentwurf vorhanden;
- Security/Privacy-Auswirkung bewertet;
- Accessibility/Performance berücksichtigt;
- strittige Entscheidung im Agenten-Council challenged.

### G2 – Implementiert
- kleiner nachvollziehbarer PR;
- relevante automatisierte Tests grün;
- keine stillen Vertrags-/Rechteänderungen;
- Migration/Rollback dokumentiert.

### G3 – Integriert geprüft
- End-to-End-/Geräte-/Fehlerpfade geprüft;
- fachliche Rechte-/Negativtests bestanden;
- Accessibility-/Performance-Regressions geprüft;
- Betriebs-/Syncwirkung getestet, soweit betroffen.

### G4 – Freigabereif
- relevante Abnahmeszenarien dokumentiert bestanden;
- keine offenen P0-Risiken;
- bekannte Restrisiken und Betriebsgrenzen dokumentiert;
- Nutzerdokumentation und Admin-/Recovery-Verfahren vorhanden;
- bei Hochrisiko-Security unabhängige Prüfung abgeschlossen.

## 13. Erfolgsmessung

Vor Produktivfreigabe werden repräsentative Fachaufgaben mit echten Fachanwendern gemessen. Metriken dienen der Verbesserung, nicht der Leistungsüberwachung einzelner Personen.

Beispiele:

- Erfolgsquote ohne Hilfe;
- Zeit bis Aufgabenabschluss;
- Fehlhandlungen und Rücksprünge;
- benötigte Hilfetexte/Supportfragen;
- wahrgenommene Verständlichkeit und Sicherheit;
- Anzahl kritischer Kontext-/Rechtefehler;
- technische Fehler-/Abbruchrate;
- Accessibility-Blocker;
- Performancebudgets;
- Restore-Erfolg und tatsächliche Wiederanlaufzeit.

## 14. Definition des Endprodukts

Das Zielprodukt ist erreicht, wenn der bestätigte KERN nicht nur implementiert, sondern in realistischen End-to-End-Szenarien als verständlich, sicher, zugänglich und wiederherstellbar nachgewiesen ist. Verschobene Module wie Aufnahme/KI/Sitzungsgeld dürfen erst danach auf denselben Qualitätsvertrag aufsetzen.
