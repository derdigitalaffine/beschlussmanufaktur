# Mantine-/Font-Awesome-Frontendpilot (#113)

**Status:** Experiment unter den offenen Frontend-Architektur- und UX-Gates #44/#43/#50. Kein globaler Frameworkwechsel und keine Produktivfreigabe.

## Gestaltungsziel

Statt einer bloßen Formular-Liste verbindet der Pilot eine editoriale, gut unterscheidbare Arbeitsoberfläche mit klar sichtbaren nächsten Schritten, freundlichen Oberflächen, verlässlicher Fehlerwiedergabe und der bereits vorhandenen fachlichen Backend-Autorität. Alle angemeldeten Arbeitsbereiche erhalten eine neue App-Shell-/Form-/Listensprache, gezielt die Seiten *Heute*, *Menschen & Rollen – Person einladen* und *Rolle ändern/entziehen* erhalten echte Mantine-Komponenten.

Aktuelle festgehaltene Bibliotheken (06.11.2026): **Mantine 9.7.5**, **Font Awesome Free Icons/Core 7.3.1**, **@fortawesome/react-fontawesome 3.5.0**, **React 19.3.1**, **Vite 8.3.6**. Die genauen Versionen inklusive transitiver Abhängigkeiten stehen im versionierten \`frontend/package-lock.json\`. Lizenzhinweise gelten wie in den Upstream-Paketen (Mantine MIT, Font Awesome Free-Icons: CC BY 4.0/MIT je nach Bestandteil).

## Lokaler Build und Auslieferung

\`\`\`sh
cd frontend
npm ci --ignore-scripts --no-audit --no-fund
npm run build
\`\`\`

Die auslieferbaren Dateien landen unter \`backend/static/mantine/\` (Git-ignored). Das neue \`deploy/Dockerfile.caddy\` erzeugt diese **im Docker-Build** mit Node 24 und packt sie gemeinsam mit den übrigen lokalen Django-Static-Dateien in das Caddy-Image. Die Compose-Dateien bauen dieses Image ohne Host-Node-Abhängigkeit; es wird kein npm-CDN im Browser benötigt. Backend und Caddy teilen **keine** Build-Artefakte über Laufzeitvolumes. Ein Staging-Rollout benötigt eine neue Caddy-Image-Version, nicht nur ein Backend-Image. Backup-/TLS-Volumes bleiben unberührt. Für die Entwicklungsansicht ohne Docker können die gebauten Dateien direkt über \`/static/mantine/\` bereitgestellt werden.

Die Django-Templates referenzieren lokale Assets. \`shell.js\` rendert ausschließlich fest zugelassene Font-Awesome-SVGs im bestehenden privaten Navigations-HTML. \`workspace.js\` mountet React/Mantine **nur auf den drei markierten Fachflächen**. Fällt JavaScript aus, bleiben die ursprünglichen Django-Links und Formulare sichtbar und funktionsfähig.

## Grenzen und Rückweg

- **Keine neue API oder Clientautorisierung:** Rolle, Organisation, Felder, Formular-POSTs, CSRF-Token und Optimistic-Concurrency-\`version\` stammen aus dem Django-HTML. React liest sie, rendert ein verbessertes UI und schickt reguläre Formular-POSTs. Serverseitige Permission-Checks, Validierung und Audit bleiben unangetastet.
- **Progressiv, kein „Frontend behauptet Erfolg“:** Mutierende Aktionen sind erst nach der Django-Antwort abgeschlossen. Ein zusätzliches Widerrufs-Kontrollkästchen ist nur eine zusätzliche clientseitige Denkhilfe, keine Ersatzberechtigung.
- **CSP:** \`script-src 'self'; style-src 'self'\` wird **nicht** für Mantine gelockert. \`MantineProvider withCSSVariables={false}\` vermeidet dynamische Theme-\`<style>\`-Blöcke; Component-Inline-Styles/CSP-Verhalten sind mit realem Browser, insbesondere authentisiert und mit produktivem Response-Header, vor einem produktiven Merge noch zu testen.
- **Bundle/Performance:** Nur lokal auslieferbar, keine externen Fonts/JS. Zwei Einträge (leichte Icons und Mantine-Fachflächen) werden getrennt gebaut. HTTP-Transfergrößen/CPU und Zoom/Tastatur/SR-Verhalten gehören noch zur #44/#50-Freigabe.
- **Datenschutz:** Public erhält weder private CSS-/JS-Ausgaben im Public-Template noch einen App-Shell-Arbeitskontext. React-Ausstattung wird nur bei den bereits erlaubten serverseitigen Seiten eingeblendet.
- **Rollback:** Branch/PR zurücknehmen, bisherigen Caddy-Static-Bind und rein servergerenderten Templatebestand wiederherstellen. Keine ORM-Datenmigration, kein Widerruf fachlicher Serveraktionen.

## Testevidenz vor Entscheidung

Foundation-CI: Python-/PostgreSQL-Tests, Django-Fallback-/CSRF-/Version-Templatefälle, Node-Client-Build, beide Caddy-Builds, Playwright-360px/Post-/No-JS-Szenarien. **Diese Checks ersetzen keine 200%-Zoom-, Keyboard-, Screenreader-, Tablet- und reale Verwaltungs-/Mandatsträger-Fachabnahme.** #73/#74 bilden weiterhin eine unabhängige Prototyp-Vergleichsgrundlage.

Zentrale nächste Entscheidung in #44: Welchen belegten Mehrwert liefert dieser Mantine-Pilot für Standardformulare relativ zu Django plus sorgfältigem Designsystem – rechtfertigt er den zusätzlichen Build, Clientcode, CSP-/Dependency-Aufwand und Migrationsbedarf? Eine Einzelentscheidung aus reiner Optik ist kein vollständiger Architekturentscheid.
