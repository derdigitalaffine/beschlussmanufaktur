# Prototype #68 – Live-Sitzung als Architektur-Stresstest

Dieser Bereich ist **kein Produktivcode**. Er vergleicht für #44/#68 zwei UI-Architekturen gegen denselben Use Case #57, ohne `live_service.py`, `voting.py` oder andere Fachregeln zu verändern.

## Varianten

### A – `progressive.html`
Servernah vorgedachte Oberfläche mit kleinen DOM-Updates. Der Browser hält nur die für die Demonstration nötigen Variablen; serverseitige Bestätigung wird simuliert.

### B – `island.html`
Gekapseltes Custom Element mit explizitem Zustandsmodell für:
- Page-/Server-Version,
- Verbindung `online | offline | stale`,
- Sitzungshoheit,
- aktiven TOP,
- Quorum,
- Vote `idle | pending-open | open | pending-close | closed`,
- eingegangene Stimmen,
- Fehler-/Recovery-Meldung.

## Gemeinsame Invarianten

- dauerhaft sichtbar: Verbindung, Sitzungshoheit, aktiver TOP, Quorum, Abstimmungsstatus;
- kritische Aktionen sind während Pending gesperrt;
- Erfolg erscheint erst nach simulierter Serverbestätigung;
- Stale-Version blockiert weitere kritische Aktionen und fokussiert Recovery;
- Offline blockiert kritische Aktionen;
- verlorene Sitzungshoheit blockiert Schreiben/Voting;
- namentliche Abstimmung ist nach Abschluss nicht erneut schließbar;
- keine geheime Abstimmung;
- dieser UI-Prototyp beweist **keine** Datenbank-/Race-Sicherheit – dafür #71.

## Szenario

1. TOP 7 ist aktiv, 18 von 28 Stimmberechtigten sind anwesend und Beschlussfähigkeit ist festgestellt.
2. Schriftführung startet eine namentliche Abstimmung.
3. Server bestätigt die Öffnung.
4. Testzustand meldet 18 eingegangene Stimmen.
5. Vor dem Schließen wird optional Stale/Offline/Authority-Loss provoziert.
6. Nach Recovery wird die Abstimmung geschlossen und Ergebnis serverseitig bestätigt.

## Browsercheck

`live_browser.cjs` ist für Playwright vorbereitet und prüft beide Varianten auf:
- sichtbare Live-Statusleiste,
- Pending-Lock,
- Stale-Block + Recovery-Fokus,
- Offline-Block + Reconnect,
- bestätigtes Vote-Ergebnis,
- keine erneute Schließaktion,
- 768px-Tablet-Reflow ohne horizontalen Seitenoverflow.

Der Test wird nur als bestanden bezeichnet, wenn er tatsächlich ausgeführt wurde.

## Bewertungsfrage

Die Island ist nur dann gerechtfertigt, wenn ihr explizites Zustandsmodell bei diesem komplexen Live-Flow messbar bessere Konsistenz, Fokus-/A11y-Führung oder Testbarkeit liefert als kleine progressive DOM-Logik – ohne Fachautorität vom Server in den Client zu verschieben.

## Nicht-Ziele

- keine produktive Live-Migration;
- kein Ersatz für #71 PostgreSQL-Concurrency;
- keine geheime digitale Abstimmung (#49);
- kein React/TypeScript-Entscheid;
- keine realen Netzwerk-/Latenz-SLAs aus einer Simulation ableiten.
