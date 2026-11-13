# Prototype #69 – Vorlage/Freigabe als Architekturvergleich

Dieser Ordner ist **kein Produktivcode**. Er beantwortet eine begrenzte Frage aus #44/#69:

> Braucht ein normaler informationslastiger Verwaltungsflow mehr Clientarchitektur als servergerenderte Seiten mit kleinen progressiven Interaktionen?

## Varianten

### A – `progressive.html`
Die Seite ist vollständig vorgerendert. JavaScript ergänzt nur Dialog, Pending/Confirmed-Feedback und einen simulierten Stale-Version-Konflikt. Fach-/Workflowdaten bleiben im Markup/Formzustand sichtbar.

### B – `island.html`
Die App-Shell bleibt statisch/servernah. Ein gekapseltes Custom Element besitzt expliziten Clientzustand für Page-Version, Server-Version, Pending, Status und Workflowzustand.

Beide Varianten verwenden **dieselbe Informationsarchitektur und dieselben Zustände**. Damit wird nicht „altes gegen modernes Design“ verglichen, sondern State Ownership und Komplexität.

## Gemeinsame Invarianten

- Arbeitskontext ist sichtbar.
- Version, Workflowstatus, Verantwortlichkeit und nächste Aktion stehen früh auf der Seite.
- Änderungen seit letzter Prüfung sind prominent.
- Es gibt genau eine dominante Hauptaktion `Freigeben`.
- `Zurückgeben` verlangt eine Begründung.
- kritischer Erfolg erscheint erst nach simulierter Serverbestätigung.
- Stale State wird als Fehler gezeigt; Fokus wandert auf die notwendige Recovery-Aktion.
- 360px darf keinen horizontalen Seiten-Overflow erzeugen.
- kein externes Framework, CDN oder Inline-Handler.

## Browsercheck

Der Test startet selbst einen lokalen HTTP-Server. Playwright muss vorhanden sein, wie im bestehenden `offline-browser`-CI-Job.

```bash
node prototypes/template-flow-69/prototype_browser.cjs
```

Geprüft werden für beide Varianten:
- Workflow/Status vorhanden,
- Stale-Version verhindert Freigabe,
- Fokus landet auf der Recovery-Aktion,
- nach Refresh wird Serverbestätigung sichtbar,
- schmaler Viewport erzeugt keinen horizontalen Overflow.

## Vergleichshypothesen

### Progressive Variante gewinnt, wenn …
- dieselbe Aufgabe mit weniger Zustands-/Build-/Testkomplexität zuverlässig lösbar bleibt;
- native HTML-/Serverform-Verträge ausreichen;
- Fokus-/Fehlerzustände ohne Client-State-Machine beherrschbar bleiben.

### Island gewinnt, wenn …
- mehrere voneinander abhängige Pending/Stale/Confirmed-Zustände deutlich konsistenter modellierbar sind;
- gezielte DOM-Updates und Recovery-Fokus mit weniger implizitem Zustand wartbar bleiben;
- zusätzliche Clientkomplexität durch messbare Test-/UX-Vorteile gerechtfertigt ist.

## Vorläufige technische Beobachtung

Schon der kleine Vergleich zeigt einen erwartbaren Trade-off: Die Island macht Zustand expliziter, benötigt dafür aber mehr Clientcode und einen dauerhaften State-/API-Vertrag. Die progressive Variante bleibt kleiner und näher am Servermodell. Ob der Mehrpreis sinnvoll ist, wird erst mit #64-Messung und Review in #44 entschieden.

## Nicht daraus ableiten

- keine React/TypeScript-Entscheidung;
- keine Produktivmigration;
- keine Aussage über reale Netzwerkperformance;
- keine WCAG-Konformitätsbehauptung;
- keine Änderung der bestehenden Workflow-/Securityregeln.
