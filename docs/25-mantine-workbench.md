# Durchgängiger Facharbeitsplatz: Mantine und Font Awesome

**Status:** Gestapelter UX-/Architektur-Prototyp #115 auf #113/#114. Bis zum #44-Councilentscheid und der #50-Fachanwendungs-/A11y-Abnahme **keine Produktivfreigabe**. Bestehende Django-Berechtigungen, CSP, POST/CSRF, Freigabe-/Versionsprüfung, Live-/Offline-Status und Public Boundary bleiben autoritativ.

## Visuelles System und Reichweite

Die neue private Oberfläche gilt **über das gemeinsame Django-`base.html` für alle angemeldeten Fachseiten** – nicht nur für die drei bisherigen Mantine-Pilotinseln. Neue Seiten erben diese Hierarchie automatisch. Sie besteht aus zwei bewusst getrennten Schichten:

1. **Echte Mantine-Komponenten auf jeder angemeldeten Seite:** Kontext-Banner (`Paper`, `Group`, `ThemeIcon`, `Breadcrumbs`, `Badge`, `Button`), schmale In-Page-Navigation (`Anchor`) und eine zugängliche Menüschublade (`Drawer`, `NavLink`) für die bereits serverseitig freigegebenen Bereiche. Alle Icons sind selbstgehostete Font-Awesome-7-SVGs. Die Basisschale enthält bewusst **keine** fachlichen Statusentscheidungen oder dynamische API-Daten.
2. **Verbesserte native Django-Arbeitsflächen:** typografisch klare Abschnittstitel, kontrastierende Hero-/Kontextflächen, saubere Aktionshierarchie, Formularfelder und Validierungsfehler, strukturierte Detailkarten, Filter, Status-Badges, Tabellen, Timeline-/Versionsflächen, Hilfetexte, Dateianhänge, explizite Leerzustände. Dieser CSS-Vertrag funktioniert **auch bei deaktiviertem JavaScript**.

Der spezialisierte React/Mantine-Pilot #113 bleibt auf Heute, Einladung und Rollenänderung/-entzug begrenzt. Der durchgängige Workbench erweitert die Orientierung und Qualität der **vorhandenen** Django-Oberflächen ohne pauschale Umwandlung von Formular-POSTs in clientseitigen Zustand.

## Arbeitsbereiche und Ordnungsprinzip

| Bereich | Prioritäre Informationen | Schutzgrenze |
|---|---|---|
| Heute | aktueller Arbeitskontext → nächste Aufgabe → Sitzung/Frist | Nur serverautorisierte Links/Aufgaben |
| Vorlagen | Entwurf, Fassung, Prüfschritt, Anlagen und Freigabe | Server entscheidet Speicherung und Veröffentlichung |
| Sitzungen | Datum/Gremium, Tagesordnung, Einladung, Fristen | Keine Einladung aus UI-Behauptungen |
| Live/Abstimmung | Sitzungshoheit, TO, Anwesenheit, verbindliche Aktionen | JS-Steuerung und Race-/Reconnect-Zustand unverändert |
| Beschlusskontrolle | Beschluss, Zuständigkeit, Termin, Sachstand, Verlauf | Kein automatischer Zustandswechsel |
| Niederschrift | aktuelle Fassung, Prüfung, Berichtigung, Publikation | Keine Veröffentlichung aus Clientstatus |
| Administration | Körperschaft, Gremium, Menschen/Rollen, Audit | Berechtigungen und Widerruf ausschließlich im Backend |
| Persönlicher Bereich | nächste Sitzung, Favoriten, Notizen, Offline-Hinweise | Kein öffentliches oder ungeprüftes Offline-Material |
| Geschütztes Portal | bereitgestellte Vorlagen, berechtigte Inhalte | Nur vom Protected-Server ausgelieferte Daten |
| Bürgerportal | Suche, Filter, veröffentlichte Treffer und Details | **Ohne** private Mantine-Assets oder Kontextnavigation |
| Anmeldung | Passwort/E-Mail-Code, Passkeys, Einladungen, Recovery | Unveränderte Authentifizierung/MFA |

Alle Seiten referenzieren den vorhandenen HTML-Server-Schutzkontext. Die Mantine-Navigation liest ausschließlich im HTML bereits angebotene `.global-nav a[href]` und führt keine eigenen Permission-Regeln ein. Kontextgebundene Unterseiten erhalten ein optionales Abschnittsverzeichnis aus vorhandenen `h2`/`h3`. **Es versteckt oder verschiebt keine Formulare**; dynamische Editor-/Live-Komponenten bleiben unangetastet.

## Darstellung und Bedienung

- Typografie mit klarer Informationshierarchie, beschränkter Zeilenbreite, sichtbaren Labels und Hilfetexten.
- Neutrale Papierflächen, zurückhaltendes dunkles Grün, akzentuierte Risiken, ausreichend große Eingabefelder und Fokusmarkierungen. Farbe allein ist nie Träger des fachlichen Status.
- 1366px Desktop, 720px Tablet, 360px Mobil und 200%-Root-Font-Stresstest; Abschnitte navigierbar, Filter umbruchfähig, Layouts minimieren horizontales Scrollen.
- Kein externer CDN-/Google-Font-Request. Build via versionierter NPM-Lockfile; Vite erzeugt `mantine/workbench.js` und erweitert die gemeinsame CSS-Ausgabe `mantine/workspace.css`. Django bleibt ohne diese Dateien voll bedienbar.
- Öffentlicher/guest Skin ist nur CSS und hat **keinen** `bm-workbench-root`, private JS-Imports oder sensitive Kontextinformation. Ein Portal kann seine eigenen Branding-Regeln über `/portal.css` liefern.

## Sicherheits-/Rollback-Vertrag

Niemals HTML-Navigationslinks aus einer unautorisierten Clientliste erzeugen. Kein Fetch für sensible Funktionen, keine Änderung an Session-Cookies, Tokens oder fachlichen APIs. React visualisiert ausschließlich die auf der Seite vorhandenen, serverautoriserten Inhalte. Mutierende Formularaktionen bleiben echte POSTs mit CSRF-, Versions-, Berechtigungs- und Auditprüfung; Fehler werden durch reguläre Django-Responses gerendert. Der öffentliche Server erhält keinen Clientcode der privaten Workbench. Auch im globalen Fehlerfall sind HTML-Seiten benutzbar, da keine fachliche Inhaltsebene verborgen wird.

Rollback: `#115`-Branch/PR zurücknehmen. Die zusätzliche Workbench-Root-, CSS-, JS-Entry- und Guest-Skin-Schicht entfällt ohne ORM-Migration und ohne Datenänderung. #113/#114 kann separat zurückgerollt werden. Die Caddy-Image-/Static-Pipeline aus #114 ist Voraussetzung; Single-Host-Compose #110 muss diesen Build-Vertrag bei späterer Implementierung integrieren.

## Nachweise vor produktiver Architekturübernahme

- Django-Tests prüfen Auth/Public-Boundary, Kontextnavigation, statische Assets und Django-Template-Vererbung.
- Vite-, Node-, PostgreSQL-, Docker-/Caddy- und Playwright-Prüfungen für echte Mantine-Komponenten und Font-Awesome-SVGs.
- Browser-Fixtures prüfen native POST-Daten (einschließlich CSRF/Version), Drawer-/Abschnittsnavigation, Desktop/360px/200%-Font, Public-Suche und No-JS.
- Vor tatsächlicher Freigabe ausstehend: **echte** 200%-Browserzoom-/Screenreader-/Tastatur-/Tablet- und Fachanwender-Tasks an allen relevanten Rollen, authentisierte CSP-Audits, tatsächliche Bundle-/Lade-/INP-Kosten, Cross-Zone-E2E #70/#72 und UX-/Frontend-Council #43/#44. Ein erfolgreiches Fixture ist keine solche Abnahme.

## Produkt-Qualitätsziel vs. aktueller Stand

Der hier durchgeführte Schritt liefert eine **durchgängige visuelle Grund- und Orientierungsoberfläche**, nicht die abschließende Neuentwicklung sämtlicher individuellen Fachprozesse als React-Komponenten. Für riskante Live-, Abstimmungs-, Offline- und Publikationsworkflows bleiben die fachlich geprüften Bestandskomponenten ausdrücklich bestehen, bis ihre Nachfolge in #44/#50 unabhängig evaluiert wurde.
